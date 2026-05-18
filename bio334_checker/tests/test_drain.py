"""Drain task: pending → graded / failed transitions."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from bio334_checker.core import drain as drain_mod
from bio334_checker.core import exercises as ex_mod
from bio334_checker.core import grader as grader_mod
from bio334_checker.core import llm_call as llm_mod
from bio334_checker.core import submissions as sub_repo
from bio334_checker.db.connection import connect, init_db


SAMPLE_YAML = """\
slug: drain_ex
title: Drain
day: 1
part: 1
order_index: 1
description_md: x
rubric_md: x
expected_stdout: "x\\n"
"""


@pytest.fixture()
def db(tmp_path: Path):
    p = tmp_path / "drain.db"
    init_db(p)
    conn = connect(p)
    yaml_path = tmp_path / "ex.yaml"
    yaml_path.write_text(SAMPLE_YAML, encoding="utf-8")
    ex_mod.upsert_exercise(conn, ex_mod.load_yaml(yaml_path))
    conn.execute(
        "INSERT INTO users (handle, display_name, created_at, last_seen_at) "
        "VALUES ('aaaa', 'A', datetime('now'), datetime('now'))"
    )
    yield conn
    conn.close()


def _seed_pending(db, n: int) -> list[int]:
    detail = ex_mod.get_exercise_detail(db, "drain_ex")
    assert detail is not None
    ids: list[int] = []
    for _ in range(n):
        result = grader_mod.GradeResult(
            sandbox_stdout="x\n",
            sandbox_stderr="",
            sandbox_rc=0,
            sandbox_truncated=False,
            exact_match=True,
            llm_score=None,
            llm_feedback_md=None,
            llm_hints=[],
            llm_raw_response_json=None,
            llm_pass=None,
            floor_ok=None,
            passed=False,
            status="pending",
            grader_version="v1",
            model_id=None,
        )
        ids.append(
            sub_repo.insert_submission(
                db,
                handle="aaaa",
                exercise=detail,
                source_code="print('x')",
                result=result,
            )
        )
    return ids


def test_drain_grades_when_llm_recovers(db, monkeypatch) -> None:
    _seed_pending(db, 1)

    payload = json.dumps({"score": 95, "feedback_md": "great"})
    monkeypatch.setattr(
        grader_mod,
        "llm_call",
        lambda *a, **k: llm_mod.LLMResponse(text=payload, raw_json="{}", model_id="x", backend="api"),
    )

    counters = drain_mod.drain_once(db)
    assert counters["graded"] == 1

    row = db.execute("SELECT * FROM submissions").fetchone()
    assert row["status"] == "graded"
    assert row["llm_score"] == 95
    assert row["passed"] == 1


def test_drain_keeps_pending_when_still_transient(db, monkeypatch) -> None:
    _seed_pending(db, 1)

    monkeypatch.setattr(
        grader_mod,
        "llm_call",
        lambda *a, **k: (_ for _ in ()).throw(llm_mod.LLMError("nope", transient=True)),
    )
    counters = drain_mod.drain_once(db)
    assert counters["still_pending"] == 1
    row = db.execute("SELECT status FROM submissions").fetchone()
    assert row["status"] == "pending"


def test_drain_marks_failed_after_max_retries(db, monkeypatch) -> None:
    sid = _seed_pending(db, 1)[0]
    monkeypatch.setattr(
        grader_mod,
        "llm_call",
        lambda *a, **k: (_ for _ in ()).throw(llm_mod.LLMError("nope", transient=True)),
    )
    # MAX_RETRIES drain attempts each leave the row pending.
    for _ in range(drain_mod.MAX_RETRIES):
        drain_mod.drain_once(db)
    # The next pass sees attempts >= MAX_RETRIES and flips to failed.
    counters = drain_mod.drain_once(db)
    assert counters["failed"] == 1
    row = db.execute("SELECT status FROM submissions WHERE id=?", (sid,)).fetchone()
    assert row["status"] == "failed"
