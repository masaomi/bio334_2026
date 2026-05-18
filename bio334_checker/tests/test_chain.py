"""KairosChain client + bridge: idempotency, two-phase queue, retry."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from bio334_checker.chain.bridge import chain_drain_once
from bio334_checker.chain.client import (
    FailingKCClient,
    KCError,
    LogKCClient,
    NullKCClient,
)
from bio334_checker.core import exercises as ex_mod
from bio334_checker.core import grader as grader_mod
from bio334_checker.core import submissions as sub_repo
from bio334_checker.db.connection import connect, init_db


SAMPLE_YAML = """\
slug: ex_c
title: C
day: 1
part: 1
order_index: 1
description_md: c
rubric_md: c
expected_stdout: "c\\n"
"""


@pytest.fixture()
def db(tmp_path: Path):
    p = tmp_path / "chain.db"
    init_db(p)
    conn = connect(p)
    yaml_path = tmp_path / "c.yaml"
    yaml_path.write_text(SAMPLE_YAML, encoding="utf-8")
    ex_mod.upsert_exercise(conn, ex_mod.load_yaml(yaml_path))
    conn.execute(
        "INSERT INTO users (handle, display_name, created_at, last_seen_at) "
        "VALUES ('aaaa', 'A', datetime('now'), datetime('now'))"
    )
    yield conn
    conn.close()


def _seed_submission(conn, *, score: int, passed: bool, status: str = "graded") -> int:
    detail = ex_mod.get_exercise_detail(conn, "ex_c")
    assert detail is not None
    result = grader_mod.GradeResult(
        sandbox_stdout="c\n",
        sandbox_stderr="",
        sandbox_rc=0,
        sandbox_truncated=False,
        exact_match=True,
        llm_score=score,
        llm_feedback_md="",
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
        conn, handle="aaaa", exercise=detail, source_code="print('c')", result=result
    )


# ---------------------------------------------------------------------------
# LogKCClient (idempotency)
# ---------------------------------------------------------------------------

def test_log_client_dedup_on_idempotency_key(tmp_path: Path) -> None:
    log = tmp_path / "chain.jsonl"
    c = LogKCClient(log)
    a = c.record("k1", {"x": 1})
    b = c.record("k1", {"x": 1})
    assert a == b
    # Only one line on disk despite two record() calls with the same key.
    lines = log.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 1


def test_log_client_record_and_attestation_keys_separate(tmp_path: Path) -> None:
    c = LogKCClient(tmp_path / "x.jsonl")
    a = c.record("k", {})
    b = c.issue("k", {})
    assert a != b
    assert a.startswith("record-")
    assert b.startswith("attestation-")


def test_log_client_loads_existing_log_on_init(tmp_path: Path) -> None:
    p = tmp_path / "x.jsonl"
    c1 = LogKCClient(p)
    rid = c1.record("k", {"a": 1})
    c2 = LogKCClient(p)  # fresh instance: loads dedup map from disk
    rid2 = c2.record("k", {"a": 1})
    assert rid == rid2
    assert len(p.read_text(encoding="utf-8").strip().splitlines()) == 1


# ---------------------------------------------------------------------------
# Bridge: 2-phase queue
# ---------------------------------------------------------------------------

def test_bridge_records_graded_writes_chain_block_ref(db, tmp_path: Path) -> None:
    sid = _seed_submission(db, score=85, passed=True)
    client = LogKCClient(tmp_path / "log.jsonl")
    counters = chain_drain_once(db, client)
    assert counters.records_written == 1
    assert counters.attestations_written == 1
    row = db.execute("SELECT chain_block_ref, attestation_id FROM submissions WHERE id=?", (sid,)).fetchone()
    assert row["chain_block_ref"] is not None
    assert row["attestation_id"] is not None


def test_bridge_does_not_attest_failing_submissions(db, tmp_path: Path) -> None:
    sid = _seed_submission(db, score=30, passed=False)
    client = LogKCClient(tmp_path / "log.jsonl")
    counters = chain_drain_once(db, client)
    assert counters.records_written == 1
    assert counters.attestations_written == 0
    row = db.execute("SELECT chain_block_ref, attestation_id FROM submissions WHERE id=?", (sid,)).fetchone()
    assert row["chain_block_ref"] is not None
    assert row["attestation_id"] is None


def test_bridge_skips_pending_status(db, tmp_path: Path) -> None:
    _seed_submission(db, score=85, passed=False, status="pending")
    counters = chain_drain_once(db, LogKCClient(tmp_path / "log.jsonl"))
    assert counters.records_written == 0
    assert counters.attestations_written == 0


def test_bridge_idempotent_on_re_run(db, tmp_path: Path) -> None:
    """Running the drain twice does not write twice (v0.3 R-4)."""
    _seed_submission(db, score=85, passed=True)
    client = LogKCClient(tmp_path / "log.jsonl")
    chain_drain_once(db, client)
    counters = chain_drain_once(db, client)
    assert counters.records_written == 0
    assert counters.attestations_written == 0


def test_bridge_resumes_after_crash_with_same_key(db, tmp_path: Path) -> None:
    """Simulate "wrote to KC but crashed before SQLite UPDATE": next pass is safe."""
    _seed_submission(db, score=85, passed=True)
    log_path = tmp_path / "log.jsonl"
    client = LogKCClient(log_path)

    # Pretend we wrote the record but the DB UPDATE never happened.
    sub = db.execute("SELECT * FROM submissions").fetchone()
    expected_key = f"bio334:rec:{sub['id']}:{sub['grader_version']}"
    pre_id = client.record(expected_key, {"prewritten": True})

    counters = chain_drain_once(db, client)
    # The bridge would have attempted record() with the same key; LogKCClient
    # returns the same id, so the submission's chain_block_ref ends up
    # matching the prewritten id (no duplicate JSONL line).
    row = db.execute("SELECT chain_block_ref FROM submissions").fetchone()
    assert row["chain_block_ref"] == pre_id
    assert counters.records_written == 1


def test_bridge_transient_error_leaves_row_unchanged(db) -> None:
    _seed_submission(db, score=85, passed=True)
    counters = chain_drain_once(db, FailingKCClient())
    assert counters.transient_errors >= 1
    row = db.execute("SELECT chain_block_ref FROM submissions").fetchone()
    assert row["chain_block_ref"] is None


# ---------------------------------------------------------------------------
# Privacy invariant: display_name never on chain
# ---------------------------------------------------------------------------

def test_chain_payload_does_not_include_display_name(db, tmp_path: Path) -> None:
    """I-PRIV-2: the chain payload uses handle only."""
    _seed_submission(db, score=85, passed=True)
    log_path = tmp_path / "log.jsonl"
    chain_drain_once(db, LogKCClient(log_path))
    text = log_path.read_text(encoding="utf-8")
    assert "aaaa" in text  # handle is on chain
    assert "display_name" not in text
    # The user's display_name in this fixture is 'A' — must not appear in payload.
    # (We accept the literal 'A' may appear in metadata; assert a clearer marker:
    # the payload key list contains no display_name field.)
    for line in text.strip().splitlines():
        obj = json.loads(line)
        payload = obj.get("payload", {})
        assert "display_name" not in payload
