"""Class-wide clear-matrix leaderboard (Phase-7+ addition).

Student-facing: anonymized ``somebody_N`` row labels, ✓/empty cells per
exercise, medals 🥇 🥈 🥉 for the top-3 distinct total-score buckets.
Per ARCHITECTURE.md §1.1 + the 2026-05-13 user direction: total score is
internal-only for ranking; it is NEVER rendered to other students.

A student can find their own row by the highlighted "(you)" marker; their
own personal page (``/me``) is the only place that shows the numeric
total score for an individual.
"""

from __future__ import annotations

import sqlite3

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse

from bio334_checker.core import progress as progress_mod
from bio334_checker.interfaces.web.dependencies import get_current_handle, get_db


router = APIRouter()


@router.get("/leaderboard", response_class=HTMLResponse)
def leaderboard_view(
    request: Request,
    handle: str = Depends(get_current_handle),
    db: sqlite3.Connection = Depends(get_db),
) -> HTMLResponse:
    entries, exercises = progress_mod.leaderboard(db, student_view=True)
    return request.app.state.templates.TemplateResponse(
        request,
        "leaderboard.html",
        {
            "handle": handle,
            "entries": entries,
            "exercises": exercises,
        },
    )
