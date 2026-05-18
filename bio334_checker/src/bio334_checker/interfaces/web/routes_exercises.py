"""Exercise list / detail routes (Phase 2).

Submission and grading (POST /submit) lands in Phase 3; the detail view's
submission form is wired to a placeholder so it 501s until then.
"""

from __future__ import annotations

import sqlite3
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import HTMLResponse

from bio334_checker.core import exercises
from bio334_checker.core import hints as hint_mod
from bio334_checker.core import progress as progress_mod
from bio334_checker.core import submissions as sub_repo
from bio334_checker.interfaces.web.dependencies import get_current_handle, get_db


router = APIRouter()


@router.get("/exercises", response_class=HTMLResponse)
def list_view(
    request: Request,
    day: Optional[int] = None,
    handle: str = Depends(get_current_handle),
    db: sqlite3.Connection = Depends(get_db),
) -> HTMLResponse:
    items = exercises.list_exercises(db, day=day, student_view=True)
    status_by_slug = {
        p.slug: ("passed" if p.passed else ("attempted" if p.attempted else "todo"))
        for p in progress_mod.personal_progress(db, handle, student_view=True)
    }
    grouped: dict[int, list] = {}
    for it in items:
        grouped.setdefault(it.day, []).append(it)
    return request.app.state.templates.TemplateResponse(
        request,
        "exercises_list.html",
        {
            "handle": handle,
            "groups": sorted(grouped.items()),
            "filter_day": day,
            "status_by_slug": status_by_slug,
        },
    )


@router.get("/exercises/{slug}", response_class=HTMLResponse)
def detail_view(
    slug: str,
    request: Request,
    handle: str = Depends(get_current_handle),
    db: sqlite3.Connection = Depends(get_db),
) -> HTMLResponse:
    detail = exercises.get_exercise_detail(db, slug)
    if detail is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="exercise not found")
    if not exercises.is_visible_to_students(db, slug):
        # Hidden by admin — students get a plain 404 so the existence of
        # not-yet-revealed exercises is not leaked through URL probing.
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="exercise not found")
    hint_mod.note_exercise_opened(
        db,
        handle=handle,
        exercise_slug=slug,
        ip=request.client.host if request.client else "?",
    )
    gate = hint_mod.gate_state(db, handle=handle, exercise_slug=slug)

    # Prefill the textarea with the student's most recent submission for
    # this exercise (regardless of pass/fail) so "Try again →" continues
    # from where they left off rather than wiping their code.
    prior = sub_repo.list_submissions_for_handle(db, handle, exercise_slug=slug)
    prior_source = prior[0]["source_code"] if prior else ""

    return request.app.state.templates.TemplateResponse(
        request,
        "exercise_detail.html",
        {
            "handle": handle,
            "ex": detail,
            "gate": gate,
            "prior_source": prior_source,
        },
    )
