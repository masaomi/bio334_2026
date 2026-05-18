"""Drain task: re-grade ``status='pending'`` submissions.

Per ARCHITECTURE.md §6.3 (R-12): a pending submission gets retried up to
``MAX_RETRIES=5`` times. On exhaustion the row transitions to
``status='failed'`` and the student-facing UI shows the failure banner.

The drain function is plain synchronous code intentionally so it can be
called from a CLI (``bio334-checker drain-pending``) or from the FastAPI
lifespan background task. Wiring the periodic loop is left to Phase 5
(KairosChain bridge runtime) so the same singleton-worker pattern handles
both retry and chain writes.
"""

from __future__ import annotations

import json
import sqlite3
from typing import Optional

from bio334_checker.core import exercises as ex_mod
from bio334_checker.core import grader as grader_mod
from bio334_checker.core import submissions as sub_repo


MAX_RETRIES = 5


def _retry_count(conn: sqlite3.Connection, submission_id: int) -> int:
    row = conn.execute(
        "SELECT detail_json FROM events "
        "WHERE event_type='drain_retry' AND detail_json LIKE ? "
        "ORDER BY id DESC",
        (f'%"submission_id": {submission_id}%',),
    ).fetchall()
    # Each row in the result is one prior retry attempt; this is OK at our
    # 30-student / 3-day scale even though it's not indexed.
    return len(row)


def _record_retry(
    conn: sqlite3.Connection, submission_id: int, *, outcome: str
) -> None:
    conn.execute(
        "INSERT INTO events (ip, handle, event_type, detail_json, created_at) "
        "VALUES ('drain', NULL, 'drain_retry', ?, datetime('now'))",
        (json.dumps({"submission_id": submission_id, "outcome": outcome}),),
    )


def drain_once(conn: sqlite3.Connection, *, limit: int = 32) -> dict[str, int]:
    """One pass over pending submissions. Returns counters.

    Returns a dict with ``retried`` (count attempted), ``graded`` (newly
    graded), ``still_pending`` (transient failure but retries remain), and
    ``failed`` (retries exhausted, flipped to failed).
    """
    counters = {"retried": 0, "graded": 0, "still_pending": 0, "failed": 0}
    pending = sub_repo.list_pending_submissions(conn, limit=limit)
    for row in pending:
        sub_id = int(row["id"])
        attempts = _retry_count(conn, sub_id)
        if attempts >= MAX_RETRIES:
            sub_repo.update_pending_to_failed(conn, sub_id)
            _record_retry(conn, sub_id, outcome="exhausted")
            counters["failed"] += 1
            continue

        detail = ex_mod.get_exercise_detail(
            conn, row["exercise_slug"], version=int(row["exercise_version"])
        )
        if detail is None:
            # Pinned revision lost (shouldn't happen). Mark failed.
            sub_repo.update_pending_to_failed(conn, sub_id)
            _record_retry(conn, sub_id, outcome="exercise_revision_missing")
            counters["failed"] += 1
            continue

        result = grader_mod.grade(row["source_code"], detail)
        counters["retried"] += 1

        if result.status == "graded":
            conn.execute(
                """UPDATE submissions SET
                       sandbox_stdout=?, sandbox_stderr=?, sandbox_rc=?,
                       exact_match=?, llm_score=?, llm_feedback_md=?,
                       llm_raw_response_json=?, passed=?, status='graded',
                       model_id=?
                     WHERE id=?""",
                (
                    result.sandbox_stdout,
                    result.sandbox_stderr,
                    result.sandbox_rc,
                    int(result.exact_match),
                    result.llm_score,
                    result.llm_feedback_md,
                    result.llm_raw_response_json,
                    int(result.passed),
                    result.model_id or "",
                    sub_id,
                ),
            )
            _record_retry(conn, sub_id, outcome="graded")
            counters["graded"] += 1
        elif result.status == "failed":
            sub_repo.update_pending_to_failed(conn, sub_id)
            _record_retry(conn, sub_id, outcome="permanent_failure")
            counters["failed"] += 1
        else:
            # still pending — leave as is
            _record_retry(conn, sub_id, outcome="still_pending")
            counters["still_pending"] += 1
    return counters
