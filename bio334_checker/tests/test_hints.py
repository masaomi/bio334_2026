"""Hint gating + LLM hint generation."""

from __future__ import annotations

from pathlib import Path

import pytest

from bio334_checker.core import exercises as ex_mod
from bio334_checker.core import grader as grader_mod
from bio334_checker.core import hints as hint_mod
from bio334_checker.core import llm_call as llm_mod
from bio334_checker.core import submissions as sub_repo
from bio334_checker.db.connection import connect, init_db


SAMPLE_YAML = """\
slug: ex_h
title: H
day: 1
part: 1
order_index: 1
description_md: x
rubric_md: x
expected_stdout: "h\\n"
"""


@pytest.fixture()
def db(tmp_path: Path):
    p = tmp_path / "h.db"
    init_db(p)
    conn = connect(p)
    yaml_path = tmp_path / "h.yaml"
    yaml_path.write_text(SAMPLE_YAML, encoding="utf-8")
    ex_mod.upsert_exercise(conn, ex_mod.load_yaml(yaml_path))
    conn.execute(
        "INSERT INTO users (handle, display_name, created_at, last_seen_at) "
        "VALUES ('aaaa', 'A', datetime('now'), datetime('now'))"
    )
    yield conn
    conn.close()


def _add_failed_attempt(conn, handle: str = "aaaa") -> None:
    detail = ex_mod.get_exercise_detail(conn, "ex_h")
    assert detail is not None
    result = grader_mod.GradeResult(
        sandbox_stdout="",
        sandbox_stderr="",
        sandbox_rc=0,
        sandbox_truncated=False,
        exact_match=False,
        llm_score=10,
        llm_feedback_md="not yet",
        llm_hints=[],
        llm_raw_response_json="{}",
        llm_pass=False,
        floor_ok=False,
        passed=False,
        status="graded",
        grader_version="v1",
        model_id="stub",
    )
    sub_repo.insert_submission(
        conn, handle=handle, exercise=detail, source_code="print('x')", result=result
    )


def test_gate_blocked_when_no_attempts_and_not_opened(db) -> None:
    g = hint_mod.gate_state(db, handle="aaaa", exercise_slug="ex_h")
    assert g.allowed is False
    assert "Open the exercise" in g.reason or "remaining" in g.reason


def test_gate_unlocks_after_two_failed_attempts(db) -> None:
    _add_failed_attempt(db)
    g1 = hint_mod.gate_state(db, handle="aaaa", exercise_slug="ex_h")
    assert g1.allowed is False  # only 1 fail so far

    _add_failed_attempt(db)
    g2 = hint_mod.gate_state(db, handle="aaaa", exercise_slug="ex_h")
    assert g2.allowed is True
    assert g2.next_level == 1


def test_gate_unlocks_after_5_minutes(db) -> None:
    # Insert an exercise_open event 6 minutes ago.
    db.execute(
        "INSERT INTO events (ip, handle, event_type, detail_json, created_at) "
        "VALUES ('?', 'aaaa', 'exercise_open', '{\"slug\": \"ex_h\"}', "
        "datetime('now', '-6 minutes'))"
    )
    g = hint_mod.gate_state(db, handle="aaaa", exercise_slug="ex_h")
    assert g.allowed is True
    assert g.seconds_since_open is not None
    assert g.seconds_since_open >= 300


def test_progressive_levels_advance_each_request(db) -> None:
    _add_failed_attempt(db)
    _add_failed_attempt(db)
    for expected_level in (1, 2, 3):
        g = hint_mod.gate_state(db, handle="aaaa", exercise_slug="ex_h")
        assert g.allowed is True
        assert g.next_level == expected_level
        hint_mod.record_hint_request(
            db, handle="aaaa", exercise_slug="ex_h", level=expected_level, ip="?"
        )
    g_after = hint_mod.gate_state(db, handle="aaaa", exercise_slug="ex_h")
    assert g_after.allowed is False
    assert "All three" in g_after.reason


def test_note_exercise_opened_idempotent(db) -> None:
    hint_mod.note_exercise_opened(db, handle="aaaa", exercise_slug="ex_h", ip="?")
    hint_mod.note_exercise_opened(db, handle="aaaa", exercise_slug="ex_h", ip="?")
    count = db.execute(
        "SELECT COUNT(*) AS c FROM events WHERE event_type='exercise_open' AND handle='aaaa'"
    ).fetchone()["c"]
    assert count == 1


def test_generate_hint_calls_llm(monkeypatch, db) -> None:
    detail = ex_mod.get_exercise_detail(db, "ex_h")
    assert detail is not None

    captured: dict = {}

    def fake_call(user, *, system, max_tokens=400, cache_system=True):
        captured["user"] = user
        captured["system"] = system
        return llm_mod.LLMResponse(
            text="Think about what changes between iterations.",
            raw_json="{}",
            model_id="stub",
            backend="api",
        )

    monkeypatch.setattr(llm_mod, "llm_call", fake_call)

    hint = hint_mod.generate_hint(exercise=detail, level=2, failed_attempts=3)
    assert hint.level == 2
    assert hint.level_name == "approach"
    assert "iterations" in hint.text
    assert "Level: 2" in captured["user"]
    assert "Concept" in captured["system"]


def test_generate_hint_clamps_level(monkeypatch, db) -> None:
    detail = ex_mod.get_exercise_detail(db, "ex_h")
    assert detail is not None
    monkeypatch.setattr(
        llm_mod,
        "llm_call",
        lambda *a, **k: llm_mod.LLMResponse(text="x", raw_json="{}", model_id="x", backend="api"),
    )
    h0 = hint_mod.generate_hint(exercise=detail, level=0, failed_attempts=0)
    assert h0.level == 1
    h99 = hint_mod.generate_hint(exercise=detail, level=99, failed_attempts=0)
    assert h99.level == 3
