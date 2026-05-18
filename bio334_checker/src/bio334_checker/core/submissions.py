"""SQLite I/O for the ``submissions`` table.

The grader writes grading fields; the chain bridge later writes the
chain fields (``chain_block_ref``, ``attestation_id``). Per §6.1 the
grader is the *sole inserter*; this module is the only place INSERTs
happen.
"""

from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from typing import Optional

from bio334_checker.core.exercises import ExerciseDetail
from bio334_checker.core.grader import GradeResult


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def insert_submission(
    conn: sqlite3.Connection,
    *,
    handle: str,
    exercise: ExerciseDetail,
    source_code: str,
    result: GradeResult,
) -> int:
    """Insert a submissions row. Returns the new row id."""
    cur = conn.execute(
        """INSERT INTO submissions (
              user_handle, exercise_slug, exercise_version,
              source_code,
              sandbox_stdout, sandbox_stderr, sandbox_rc,
              exact_match, llm_score, llm_feedback_md, llm_raw_response_json,
              passed, status, grader_version, model_id, created_at
           ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            handle,
            exercise.slug,
            exercise.version,
            source_code,
            result.sandbox_stdout,
            result.sandbox_stderr,
            result.sandbox_rc,
            int(result.exact_match),
            result.llm_score,
            result.llm_feedback_md,
            result.llm_raw_response_json,
            int(result.passed),
            result.status,
            result.grader_version,
            result.model_id or "",
            _now_iso(),
        ),
    )
    return int(cur.lastrowid)


def get_submission(
    conn: sqlite3.Connection, submission_id: int
) -> Optional[sqlite3.Row]:
    return conn.execute(
        "SELECT * FROM submissions WHERE id = ?", (submission_id,)
    ).fetchone()


def list_submissions_for_handle(
    conn: sqlite3.Connection,
    handle: str,
    *,
    exercise_slug: Optional[str] = None,
) -> list[sqlite3.Row]:
    if exercise_slug is None:
        return conn.execute(
            "SELECT * FROM submissions WHERE user_handle = ? ORDER BY id DESC",
            (handle,),
        ).fetchall()
    return conn.execute(
        "SELECT * FROM submissions WHERE user_handle = ? AND exercise_slug = ? "
        "ORDER BY id DESC",
        (handle, exercise_slug),
    ).fetchall()


def count_failed_attempts(
    conn: sqlite3.Connection, *, handle: str, exercise_slug: str
) -> int:
    """Number of *graded* non-passing submissions for (handle, exercise)."""
    row = conn.execute(
        "SELECT COUNT(*) AS c FROM submissions "
        "WHERE user_handle = ? AND exercise_slug = ? "
        "  AND status = 'graded' AND passed = 0",
        (handle, exercise_slug),
    ).fetchone()
    return int(row["c"]) if row else 0


def update_pending_to_failed(
    conn: sqlite3.Connection, submission_id: int
) -> None:
    conn.execute(
        "UPDATE submissions SET status='failed' WHERE id=? AND status='pending'",
        (submission_id,),
    )


def list_pending_submissions(
    conn: sqlite3.Connection, *, limit: int = 32
) -> list[sqlite3.Row]:
    return conn.execute(
        "SELECT * FROM submissions WHERE status='pending' ORDER BY id LIMIT ?",
        (limit,),
    ).fetchall()
