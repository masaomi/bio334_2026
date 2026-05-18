"""Anonymous end-of-course survey routes.

- ``GET  /survey``         render the form (only when admin has enabled it)
- ``POST /survey``         persist responses (NO user_handle stored)
- ``GET  /survey/thanks``  confirmation page

The student-facing link on /me is conditional on
``survey.is_enabled()`` so the URL is effectively hidden until the
instructor turns it on from /admin (R-2026-05-13 directive).
"""

from __future__ import annotations

import sqlite3

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse

from bio334_checker.core import survey
from bio334_checker.interfaces.web.dependencies import get_db


router = APIRouter()


@router.get("/survey", response_class=HTMLResponse)
def survey_form(
    request: Request,
    db: sqlite3.Connection = Depends(get_db),
) -> HTMLResponse:
    if not survey.is_enabled(db):
        raise HTTPException(
            status.HTTP_404_NOT_FOUND, detail="survey not currently open"
        )
    return request.app.state.templates.TemplateResponse(
        "survey.html",
        {"request": request, "questions": survey.SURVEY_QUESTIONS},
    )


@router.post("/survey")
async def survey_submit(
    request: Request,
    db: sqlite3.Connection = Depends(get_db),
) -> RedirectResponse:
    if not survey.is_enabled(db):
        raise HTTPException(
            status.HTTP_404_NOT_FOUND, detail="survey not currently open"
        )
    form = await request.form()
    answers = {k: str(v) for k, v in form.items() if isinstance(v, str)}
    survey.submit_responses(db, answers)
    return RedirectResponse("/survey/thanks", status_code=status.HTTP_303_SEE_OTHER)


@router.get("/survey/thanks", response_class=HTMLResponse)
def survey_thanks(request: Request) -> HTMLResponse:
    return request.app.state.templates.TemplateResponse(
        "survey_thanks.html", {"request": request}
    )
