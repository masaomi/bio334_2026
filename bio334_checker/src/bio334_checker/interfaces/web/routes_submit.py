"""Submit + result routes (Phase 3).

POST /submit                  Grade and persist; redirect to result page.
GET  /submissions/{id}        Result detail (provisional banner, disagreement
                              banner, sandbox output, LLM feedback).

Per ARCHITECTURE.md §9.3 (R-11): the result page renders a provisional
banner with the v0.3 wording. Per §6.2: when ``exact_match`` and
``llm_pass`` disagree the disagreement banner is rendered and an
``events`` row is logged (``event_type='grader_disagreement'``).
"""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Form, HTTPException, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse

from bio334_checker.core import exercises as ex_mod
from bio334_checker.core import grader as grader_mod
from bio334_checker.core import submissions as sub_repo
from bio334_checker.interfaces.web.dependencies import get_current_handle, get_db


router = APIRouter()


def _log_event(
    conn: sqlite3.Connection,
    *,
    request: Request,
    handle: str,
    event_type: str,
    detail: dict,
) -> None:
    conn.execute(
        "INSERT INTO events (ip, handle, event_type, detail_json, created_at) "
        "VALUES (?, ?, ?, ?, ?)",
        (
            request.client.host if request.client else "?",
            handle,
            event_type,
            json.dumps(detail),
            datetime.now(timezone.utc).isoformat(),
        ),
    )


@router.post("/submit")
def submit(
    request: Request,
    exercise_slug: str = Form(...),
    exercise_version: int = Form(...),
    source_code: str = Form(...),
    handle: str = Depends(get_current_handle),
    db: sqlite3.Connection = Depends(get_db),
) -> RedirectResponse:
    detail = ex_mod.get_exercise_detail(db, exercise_slug)
    if detail is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="exercise not found")
    if not ex_mod.is_visible_to_students(db, exercise_slug):
        # Hidden exercises cannot accept new submissions even if the student
        # crafts the form by hand. Past submissions stay readable.
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="exercise not found")

    if exercise_version != detail.version:
        # Drift between the page the student loaded and the current latest.
        # We grade against whatever they submitted against, but we resolve
        # to the version they pinned (I-VERSION-1). If the pinned version
        # doesn't exist anymore, 409.
        pinned = ex_mod.get_exercise_detail(db, exercise_slug, version=exercise_version)
        if pinned is None:
            raise HTTPException(
                status.HTTP_409_CONFLICT,
                detail=f"exercise revision v{exercise_version} no longer exists",
            )
        detail = pinned

    result = grader_mod.grade(source_code, detail)
    submission_id = sub_repo.insert_submission(
        db,
        handle=handle,
        exercise=detail,
        source_code=source_code,
        result=result,
    )

    _log_event(
        db,
        request=request,
        handle=handle,
        event_type="submit",
        detail={
            "submission_id": submission_id,
            "exercise_slug": detail.slug,
            "exercise_version": detail.version,
            "status": result.status,
            "passed": int(result.passed),
        },
    )

    # Disagreement is only meaningful when the exercise has a canonical
    # expected_stdout; otherwise exact_match is always False by code and
    # the banner "your output differs from the canonical answer" would
    # mislead. (Surfaced during 2026-05-11 dry-run.)
    if detail.expected_stdout is not None:
        disagreement = grader_mod.disagreement_kind(
            exact_match=result.exact_match, llm_pass=result.llm_pass
        )
    else:
        disagreement = None
    if disagreement is not None:
        _log_event(
            db,
            request=request,
            handle=handle,
            event_type="grader_disagreement",
            detail={
                "submission_id": submission_id,
                "kind": disagreement,
                "exact_match": int(result.exact_match),
                "llm_score": result.llm_score,
            },
        )

    return RedirectResponse(
        f"/submissions/{submission_id}",
        status_code=status.HTTP_303_SEE_OTHER,
    )


@router.get("/submissions/{submission_id}", response_class=HTMLResponse)
def submission_detail(
    submission_id: int,
    request: Request,
    handle: str = Depends(get_current_handle),
    db: sqlite3.Connection = Depends(get_db),
) -> HTMLResponse:
    row = sub_repo.get_submission(db, submission_id)
    if row is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="submission not found")
    if row["user_handle"] != handle:
        # Prevent cross-handle peeking (§I-PRIV-1).
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail="not yours")

    disagreement = None
    if row["status"] == "graded" and row["llm_score"] is not None:
        meta = _revision_meta(db, row["exercise_slug"], row["exercise_version"])
        if meta["expected_stdout"] is not None:
            llm_pass = bool(row["llm_score"] >= int(meta["pass_threshold"]))
            disagreement = grader_mod.disagreement_kind(
                exact_match=bool(row["exact_match"]), llm_pass=llm_pass
            )

    next_slug = _next_exercise_slug(db, row["exercise_slug"])
    return request.app.state.templates.TemplateResponse(
        "submission_result.html",
        {
            "request": request,
            "handle": handle,
            "row": row,
            "disagreement": disagreement,
            "next_slug": next_slug,
        },
    )


def _next_exercise_slug(conn: sqlite3.Connection, current_slug: str) -> str | None:
    """Next exercise the student is allowed to see. Skips hidden ones so
    the post-pass forward arrow does not point into a 404."""
    items = ex_mod.list_exercises(conn, student_view=True)
    for i, it in enumerate(items):
        if it.slug == current_slug and i + 1 < len(items):
            return items[i + 1].slug
    return None


def _revision_meta(conn: sqlite3.Connection, slug: str, version: int) -> dict:
    row = conn.execute(
        "SELECT pass_threshold, expected_stdout FROM exercise_revisions "
        "WHERE slug=? AND version=?",
        (slug, version),
    ).fetchone()
    if row is None:
        return {"pass_threshold": 70, "expected_stdout": None}
    return {
        "pass_threshold": int(row["pass_threshold"]),
        "expected_stdout": row["expected_stdout"],
    }
