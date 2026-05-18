"""Personal + cohort progress aggregation."""

from __future__ import annotations

from pathlib import Path

import pytest

from bio334_checker.core import exercises as ex_mod
from bio334_checker.core import grader as grader_mod
from bio334_checker.core import progress as progress_mod
from bio334_checker.core import submissions as sub_repo
from bio334_checker.db.connection import connect, init_db


SAMPLE_YAML = """\
slug: ex_a
title: A
day: 1
part: 1
order_index: 1
description_md: x
rubric_md: x
expected_stdout: "a\\n"
"""


@pytest.fixture()
def db(tmp_path: Path):
    p = tmp_path / "p.db"
    init_db(p)
    conn = connect(p)
    yaml_path = tmp_path / "a.yaml"
    yaml_path.write_text(SAMPLE_YAML, encoding="utf-8")
    ex_mod.upsert_exercise(conn, ex_mod.load_yaml(yaml_path))
    yield conn
    conn.close()


def _seed_user(conn, handle: str) -> None:
    conn.execute(
        "INSERT INTO users (handle, display_name, created_at, last_seen_at) "
        "VALUES (?, ?, datetime('now'), datetime('now'))",
        (handle, handle.upper()),
    )


def _seed_submission(conn, *, handle: str, score: int, passed: bool, status: str = "graded") -> int:
    detail = ex_mod.get_exercise_detail(conn, "ex_a")
    assert detail is not None
    result = grader_mod.GradeResult(
        sandbox_stdout="a\n",
        sandbox_stderr="",
        sandbox_rc=0,
        sandbox_truncated=False,
        exact_match=True,
        llm_score=score,
        llm_feedback_md="ok",
        llm_hints=[],
        llm_raw_response_json="{}",
        llm_pass=score >= 70,
        floor_ok=score >= 40,
        passed=passed,
        status=status,
        grader_version="v1",
        model_id="stub",
    )
    return sub_repo.insert_submission(
        conn, handle=handle, exercise=detail, source_code="print('a')", result=result
    )


def test_personal_progress_no_attempts(db) -> None:
    _seed_user(db, "aaaa")
    rows = progress_mod.personal_progress(db, "aaaa")
    assert len(rows) == 1
    assert rows[0].attempted is False
    assert rows[0].passed is False
    assert rows[0].best_score is None


def test_personal_progress_best_score_and_pass(db) -> None:
    _seed_user(db, "aaaa")
    _seed_submission(db, handle="aaaa", score=55, passed=False)
    _seed_submission(db, handle="aaaa", score=85, passed=True)
    _seed_submission(db, handle="aaaa", score=70, passed=False)
    rows = progress_mod.personal_progress(db, "aaaa")
    assert rows[0].best_score == 85
    assert rows[0].passed is True
    assert rows[0].attempts == 3


def test_cohort_suppresses_below_min_submitters(db) -> None:
    for i, h in enumerate(["aaaa", "bbbb", "cccc"]):
        _seed_user(db, h)
        _seed_submission(db, handle=h, score=80 + i, passed=True)
    rows = progress_mod.cohort_progress(db)
    assert rows[0].submitters == 3
    assert rows[0].suppressed is True
    assert rows[0].median_best_score is None


def test_leaderboard_assigns_medals_dense_rank(db) -> None:
    """Top-3 distinct non-zero scores get 🥇 🥈 🥉; ties share the medal;
    zero score is never awarded.
    """
    # Seed 5 users with various best-scores: 100, 100, 80, 50, 0.
    for h, score, passed in [
        ("aaaa", 100, True),
        ("bbbb", 100, True),
        ("cccc", 80, True),
        ("dddd", 50, False),  # below pass_threshold but still scores
        ("eeee", None, None),  # never submitted
    ]:
        _seed_user(db, h)
        if score is not None:
            _seed_submission(db, handle=h, score=score, passed=bool(passed))

    entries, exercises = progress_mod.leaderboard(db)
    assert len(entries) == 5
    assert len(exercises) == 1

    by_handle = {e.handle: e for e in entries}
    # 100s share gold.
    assert by_handle["aaaa"].medal == "🥇"
    assert by_handle["bbbb"].medal == "🥇"
    assert by_handle["aaaa"].rank == 1 == by_handle["bbbb"].rank
    # 80 takes silver (next distinct score).
    assert by_handle["cccc"].medal == "🥈"
    assert by_handle["cccc"].rank == 2
    # 50 takes bronze.
    assert by_handle["dddd"].medal == "🥉"
    assert by_handle["dddd"].rank == 3
    # No-attempt student gets no medal AND rank 0.
    assert by_handle["eeee"].medal == ""
    assert by_handle["eeee"].rank == 0


def test_leaderboard_zero_score_no_medal_even_when_top(db) -> None:
    """If everyone is at 0, nobody gets a medal."""
    for h in ("aaaa", "bbbb"):
        _seed_user(db, h)
    entries, _ = progress_mod.leaderboard(db)
    for e in entries:
        assert e.medal == ""
        assert e.rank == 0


def test_leaderboard_anon_id_in_display_order(db) -> None:
    """anon_id is 1..N, in the displayed order (sorted by total_score desc)."""
    for h, score in [("aaaa", 50), ("bbbb", 100), ("cccc", 80)]:
        _seed_user(db, h)
        _seed_submission(db, handle=h, score=score, passed=score >= 70)
    entries, _ = progress_mod.leaderboard(db)
    by_anon = {e.anon_id: e.handle for e in entries}
    assert by_anon[1] == "bbbb"  # highest score first
    assert by_anon[2] == "cccc"
    assert by_anon[3] == "aaaa"


def test_leaderboard_cells_reflect_passed(db) -> None:
    """A cell is True iff the student has at least one passing submission."""
    _seed_user(db, "aaaa")
    _seed_submission(db, handle="aaaa", score=85, passed=True)
    entries, _ = progress_mod.leaderboard(db)
    e = next(x for x in entries if x.handle == "aaaa")
    assert e.cells["ex_a"] is True
    assert e.cleared_count == 1


def test_cohort_shows_median_when_enough_submitters(db) -> None:
    scores = [50, 60, 70, 80, 90]
    for i, score in enumerate(scores):
        h = f"u{i:03d}"[:4]
        _seed_user(db, h)
        _seed_submission(db, handle=h, score=score, passed=score >= 70)
    rows = progress_mod.cohort_progress(db)
    assert rows[0].submitters == 5
    assert rows[0].suppressed is False
    assert rows[0].median_best_score == 70.0
    assert rows[0].pass_count == 3
