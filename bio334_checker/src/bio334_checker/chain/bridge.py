"""SQLite-as-queue chain bridge (singleton worker).

Per ARCHITECTURE.md §7.2 (v0.3 R-1 / R-4):

Phase A: every graded submission gets a ``chain_record``.
   SELECT ... WHERE chain_block_ref IS NULL AND status='graded'

Phase B: every passing submission additionally gets an
``attestation_issue``.
   SELECT ... WHERE attestation_id IS NULL AND chain_block_ref IS NOT NULL
                  AND status='graded' AND passed=1

Idempotency keys are stable per submission row because re-grading in
place is forbidden (I-VERSION-2). Re-evaluation creates a new
submission row with a fresh id and a possibly bumped grader_version.

Failure handling: ``KCError(transient=True)`` leaves the row unmodified
so the next iteration retries. Permanent ``KCError`` (or any non-retryable
exception) is logged and the row is left alone too — the singleton
runtime guarantees only one worker is competing for it.
"""

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

from bio334_checker.chain.client import KCClient, KCError


@dataclass
class DrainCounters:
    records_written: int = 0
    attestations_written: int = 0
    transient_errors: int = 0
    permanent_errors: int = 0


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _record_key(submission_id: int, grader_version: str) -> str:
    return f"bio334:rec:{submission_id}:{grader_version}"


def _attestation_key(submission_id: int, grader_version: str) -> str:
    return f"bio334:att:{submission_id}:{grader_version}"


def _record_payload(row: sqlite3.Row, *, handle: str) -> dict:
    """Chain payload — handle ONLY, never display_name (I-PRIV-2)."""
    return {
        "type": "submission",
        "handle": handle,
        "exercise_slug": row["exercise_slug"],
        "exercise_version": int(row["exercise_version"]),
        "passed": int(row["passed"]),
        "llm_score": row["llm_score"],
        "grader_version": row["grader_version"],
        "model_id": row["model_id"],
        "ts": row["created_at"],
    }


def _attestation_payload(row: sqlite3.Row, *, handle: str) -> dict:
    return {
        "subject": handle,
        "claim": "completed",
        "exercise_slug": row["exercise_slug"],
        "exercise_version": int(row["exercise_version"]),
        "score": row["llm_score"],
        "ts": row["created_at"],
    }


def chain_drain_once(
    conn: sqlite3.Connection, client: KCClient, *, batch: int = 32
) -> DrainCounters:
    """One pass of phases A + B. Returns counters for observability."""
    counters = DrainCounters()

    # Phase A: chain_record for any graded submission missing chain_block_ref.
    rows_a = conn.execute(
        "SELECT id, user_handle, exercise_slug, exercise_version, llm_score, "
        "       passed, status, grader_version, model_id, created_at "
        "  FROM submissions "
        " WHERE chain_block_ref IS NULL "
        "   AND status = 'graded' "
        " ORDER BY id LIMIT ?",
        (batch,),
    ).fetchall()
    for row in rows_a:
        sub_id = int(row["id"])
        key = _record_key(sub_id, row["grader_version"])
        payload = _record_payload(row, handle=row["user_handle"])
        try:
            ref = client.record(key, payload)
        except KCError as e:
            if e.transient:
                counters.transient_errors += 1
            else:
                counters.permanent_errors += 1
                _log_event(
                    conn,
                    handle=row["user_handle"],
                    event_type="chain_record_failed",
                    detail={"submission_id": sub_id, "msg": str(e)},
                )
            continue
        conn.execute(
            "UPDATE submissions SET chain_block_ref = ? WHERE id = ?",
            (ref, sub_id),
        )
        counters.records_written += 1

    # Phase B: attestation_issue only for passing submissions whose record
    # already landed.
    rows_b = conn.execute(
        "SELECT id, user_handle, exercise_slug, exercise_version, llm_score, "
        "       passed, status, grader_version, model_id, created_at "
        "  FROM submissions "
        " WHERE attestation_id IS NULL "
        "   AND chain_block_ref IS NOT NULL "
        "   AND status = 'graded' "
        "   AND passed = 1 "
        " ORDER BY id LIMIT ?",
        (batch,),
    ).fetchall()
    for row in rows_b:
        sub_id = int(row["id"])
        key = _attestation_key(sub_id, row["grader_version"])
        payload = _attestation_payload(row, handle=row["user_handle"])
        try:
            att = client.issue(key, payload)
        except KCError as e:
            if e.transient:
                counters.transient_errors += 1
            else:
                counters.permanent_errors += 1
                _log_event(
                    conn,
                    handle=row["user_handle"],
                    event_type="attestation_issue_failed",
                    detail={"submission_id": sub_id, "msg": str(e)},
                )
            continue
        conn.execute(
            "UPDATE submissions SET attestation_id = ? WHERE id = ?",
            (att, sub_id),
        )
        counters.attestations_written += 1

    return counters


def _log_event(
    conn: sqlite3.Connection,
    *,
    handle: Optional[str],
    event_type: str,
    detail: dict,
) -> None:
    conn.execute(
        "INSERT INTO events (ip, handle, event_type, detail_json, created_at) "
        "VALUES ('chain', ?, ?, ?, ?)",
        (handle, event_type, json.dumps(detail), _now_iso()),
    )
