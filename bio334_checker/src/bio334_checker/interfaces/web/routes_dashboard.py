"""Dashboard route: personal progress + cohort median (anonymized)."""

from __future__ import annotations

import sqlite3

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse

from bio334_checker.core import progress as progress_mod
from bio334_checker.interfaces.web.dependencies import get_current_handle, get_db


router = APIRouter()


@router.get("/dashboard", response_class=HTMLResponse)
def dashboard(
    request: Request,
    handle: str = Depends(get_current_handle),
    db: sqlite3.Connection = Depends(get_db),
) -> HTMLResponse:
    personal = progress_mod.personal_progress(db, handle, student_view=True)
    cohort = progress_mod.cohort_progress(db, student_view=True)

    # Merge by slug so the template can render a single table.
    cohort_by_slug = {c.slug: c for c in cohort}
    rows = [
        {
            "personal": p,
            "cohort": cohort_by_slug.get(p.slug),
        }
        for p in personal
    ]
    return request.app.state.templates.TemplateResponse(
        request,
        "dashboard.html",
        {
            "handle": handle,
            "rows": rows,
            "min_submitters": progress_mod.COHORT_MEDIAN_MIN_SUBMITTERS,
        },
    )
