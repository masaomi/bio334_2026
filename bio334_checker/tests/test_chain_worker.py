"""Singleton worker: lifecycle + tick-driven drain integration.

The asyncio worker runs ``_tick_sync`` in a thread on each cadence tick.
Here we exercise it by starting the worker, seeding a passing submission,
waiting briefly, and asserting that ``chain_block_ref`` lands.
"""

from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

from bio334_checker.chain.client import LogKCClient
from bio334_checker.chain.worker import BackgroundWorker
from bio334_checker.core import exercises as ex_mod
from bio334_checker.core import grader as grader_mod
from bio334_checker.core import submissions as sub_repo
from bio334_checker.db.connection import connect, init_db


SAMPLE_YAML = """\
slug: ex_w
title: W
day: 1
part: 1
order_index: 1
description_md: w
rubric_md: w
expected_stdout: "w\\n"
"""


def _seed_one_passing(db_path: Path) -> int:
    init_db(db_path)
    yaml_path = db_path.parent / "w.yaml"
    yaml_path.write_text(SAMPLE_YAML, encoding="utf-8")
    conn = connect(db_path)
    try:
        ex_mod.upsert_exercise(conn, ex_mod.load_yaml(yaml_path))
        conn.execute(
            "INSERT INTO users (handle, display_name, created_at, last_seen_at) "
            "VALUES ('aaaa', 'A', datetime('now'), datetime('now'))"
        )
        detail = ex_mod.get_exercise_detail(conn, "ex_w")
        assert detail is not None
        result = grader_mod.GradeResult(
            sandbox_stdout="w\n", sandbox_stderr="", sandbox_rc=0,
            sandbox_truncated=False, exact_match=True,
            llm_score=85, llm_feedback_md="ok", llm_hints=[],
            llm_raw_response_json="{}", llm_pass=True, floor_ok=True,
            passed=True, status="graded", grader_version="v1", model_id="stub",
        )
        sid = sub_repo.insert_submission(
            conn, handle="aaaa", exercise=detail, source_code="print('w')", result=result
        )
    finally:
        conn.close()
    return sid


@pytest.mark.asyncio
async def test_worker_writes_chain_record(tmp_path: Path) -> None:
    db_path = tmp_path / "wkr.db"
    sid = _seed_one_passing(db_path)
    client = LogKCClient(tmp_path / "chain.jsonl")
    worker = BackgroundWorker(db_path=db_path, kc_client=client)
    await worker.start()
    try:
        # The worker ticks every 2s when busy; one immediate tick suffices.
        for _ in range(15):
            conn = connect(db_path)
            try:
                row = conn.execute(
                    "SELECT chain_block_ref, attestation_id FROM submissions WHERE id=?",
                    (sid,),
                ).fetchone()
            finally:
                conn.close()
            if row["chain_block_ref"] and row["attestation_id"]:
                break
            await asyncio.sleep(0.5)
        assert row["chain_block_ref"] is not None
        assert row["attestation_id"] is not None
    finally:
        await worker.stop()


@pytest.mark.asyncio
async def test_worker_stop_is_clean(tmp_path: Path) -> None:
    db_path = tmp_path / "stop.db"
    init_db(db_path)
    worker = BackgroundWorker(db_path=db_path)
    await worker.start()
    await worker.stop()
    # A second stop is a no-op.
    await worker.stop()
