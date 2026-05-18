"""Gated hint endpoint.

POST /hint/{submission_id}

The submission_id ties the request to a specific (handle, exercise) pair
so we can:
- enforce I-PRIV-1 ownership (only the submission's owner can request),
- look up the right exercise context,
- count the failed attempts on that exercise.

This prevents the round-2 IDOR concern about /hint/{submission_id}.
"""

from __future__ import annotations

import sqlite3

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import HTMLResponse

from bio334_checker.core import exercises as ex_mod
from bio334_checker.core import hints as hint_mod
from bio334_checker.core import llm_call as llm_mod
from bio334_checker.core import submissions as sub_repo
from bio334_checker.interfaces.web.dependencies import get_current_handle, get_db


router = APIRouter()


@router.post("/hint/{submission_id}", response_class=HTMLResponse)
def request_hint(
    submission_id: int,
    request: Request,
    handle: str = Depends(get_current_handle),
    db: sqlite3.Connection = Depends(get_db),
) -> HTMLResponse:
    sub = sub_repo.get_submission(db, submission_id)
    if sub is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="submission not found")
    if sub["user_handle"] != handle:
        # IDOR guard (round-2 P1).
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail="not yours")

    detail = ex_mod.get_exercise_detail(
        db, sub["exercise_slug"], version=int(sub["exercise_version"])
    )
    if detail is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="exercise revision missing")

    gate = hint_mod.gate_state(db, handle=handle, exercise_slug=detail.slug)
    if not gate.allowed:
        return request.app.state.templates.TemplateResponse(
            "hint_blocked.html",
            {"request": request, "handle": handle, "gate": gate, "submission_id": submission_id, "exercise_slug": detail.slug},
            status_code=status.HTTP_403_FORBIDDEN,
        )

    try:
        hint = hint_mod.generate_hint(
            exercise=detail,
            level=gate.next_level,
            failed_attempts=gate.failed_attempts,
        )
    except llm_mod.LLMError as e:
        return request.app.state.templates.TemplateResponse(
            "hint_unavailable.html",
            {"request": request, "handle": handle, "transient": e.transient, "submission_id": submission_id, "exercise_slug": detail.slug},
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        )

    hint_mod.record_hint_request(
        db,
        handle=handle,
        exercise_slug=detail.slug,
        level=hint.level,
        ip=request.client.host if request.client else "?",
    )
    return request.app.state.templates.TemplateResponse(
        "hint_response.html",
        {
            "request": request,
            "handle": handle,
            "hint": hint,
            "submission_id": submission_id,
            "exercise_slug": detail.slug,
        },
    )
