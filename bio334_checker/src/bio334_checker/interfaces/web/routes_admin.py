"""Instructor admin routes.

GET /admin              heat map + students + disagreement log + hint log
GET /admin/exercises    per-exercise student-visibility toggle
POST /admin/exercises/visibility  bulk-set visibility from the checkbox form
GET /admin/export       tar.gz containing the SQLite file + chain JSONL

All routes are guarded by basic-auth (``require_admin``); the 127.0.0.1
bind is enforced separately by middleware in :mod:`app`.
"""

from __future__ import annotations

import io
import os
import sqlite3
import tarfile
import time
from pathlib import Path

from fastapi import APIRouter, Depends, Form, Request, Response
from fastapi.responses import HTMLResponse, RedirectResponse, StreamingResponse

from bio334_checker.chain.client import DEFAULT_LOG_PATH
from bio334_checker.core import admin_stats
from bio334_checker.core import charts as charts_mod
from bio334_checker.core import exercises as ex_mod
from bio334_checker.core import progress as progress_mod
from bio334_checker.core import survey as survey_mod
from bio334_checker.interfaces.web.admin_auth import require_admin
from bio334_checker.interfaces.web.dependencies import get_db


router = APIRouter()


@router.get("/admin", response_class=HTMLResponse)
def admin_dashboard(
    request: Request,
    _user: str = Depends(require_admin),
    db: sqlite3.Connection = Depends(get_db),
) -> HTMLResponse:
    cells = admin_stats.heat_map(db)
    students = admin_stats.students_overview(db)
    disagreements = admin_stats.disagreement_log(db, limit=200)
    hints = admin_stats.hint_log(db, limit=200)
    leaderboard, lb_exercises = progress_mod.leaderboard(db)
    survey_enabled = survey_mod.is_enabled(db)
    all_ex = ex_mod.list_exercises(db)
    visibility_summary = {
        "visible": sum(1 for e in all_ex if e.visible_to_students),
        "total": len(all_ex),
    }
    token_usage = admin_stats.token_usage_summary(db)
    return request.app.state.templates.TemplateResponse(
        "admin.html",
        {
            "request": request,
            "cells": cells,
            "students": students,
            "disagreements": disagreements,
            "hints": hints,
            "leaderboard": leaderboard,
            "lb_exercises": lb_exercises,
            "survey_enabled": survey_enabled,
            "visibility_summary": visibility_summary,
            "token_usage": token_usage,
        },
    )


@router.get("/admin/exercises", response_class=HTMLResponse)
def admin_exercises(
    request: Request,
    _user: str = Depends(require_admin),
    db: sqlite3.Connection = Depends(get_db),
) -> HTMLResponse:
    """Per-exercise checkbox grid: tick to reveal to students, untick to
    hide. Default state for a freshly-imported exercise is visible (1)."""
    items = ex_mod.list_exercises(db)
    grouped: dict[int, list] = {}
    for it in items:
        grouped.setdefault(it.day, []).append(it)
    return request.app.state.templates.TemplateResponse(
        "admin_exercises.html",
        {
            "request": request,
            "groups": sorted(grouped.items()),
            "total": len(items),
            "visible_count": sum(1 for it in items if it.visible_to_students),
        },
    )


@router.post("/admin/exercises/visibility")
async def admin_set_visibility(
    request: Request,
    _user: str = Depends(require_admin),
    db: sqlite3.Connection = Depends(get_db),
) -> RedirectResponse:
    """Bulk-update student visibility. The form supports two paths:

    - ``preset=show_all`` / ``hide_all`` / ``day_le_<N>`` for one-click
      bulk operations (rendered as buttons in the admin template).
    - Otherwise: every ``slug=<slug>`` field present in the form body is
      treated as "checked", and every slug absent is "unchecked". HTML
      checkboxes naturally produce exactly this shape.
    """
    form = await request.form()
    preset = (form.get("preset") or "").strip()
    all_items = ex_mod.list_exercises(db)
    if preset == "show_all":
        visible = [it.slug for it in all_items]
    elif preset == "hide_all":
        visible = []
    elif preset.startswith("day_le_"):
        try:
            cutoff = int(preset.removeprefix("day_le_"))
        except ValueError:
            cutoff = 0
        visible = [it.slug for it in all_items if it.day <= cutoff]
    else:
        visible = list(form.getlist("slug"))
    ex_mod.bulk_set_visibility(db, visible)
    return RedirectResponse(url="/admin/exercises", status_code=303)


@router.post("/admin/survey/toggle")
def admin_toggle_survey(
    _user: str = Depends(require_admin),
    db: sqlite3.Connection = Depends(get_db),
) -> Response:
    survey_mod.set_enabled(db, not survey_mod.is_enabled(db))
    return RedirectResponse("/admin", status_code=303)


@router.get("/admin/survey", response_class=HTMLResponse)
def admin_survey(
    request: Request,
    _user: str = Depends(require_admin),
    db: sqlite3.Connection = Depends(get_db),
) -> HTMLResponse:
    """Aggregation page: pie/bar charts per question + free-text list."""
    blocks = []
    for q in survey_mod.SURVEY_QUESTIONS:
        if q["type"] == "text":
            blocks.append(
                {
                    "q": q,
                    "kind": "text",
                    "responses": survey_mod.aggregate_text(db, q["key"]),
                    "chart": "",
                }
            )
        else:
            data = survey_mod.aggregate_choice(db, q["key"])
            items = [(label, count) for _, label, count in data]
            if q["type"] == "single":
                chart = charts_mod.pie_chart_svg(items)
            else:
                chart = charts_mod.bar_chart_svg(items)
            blocks.append(
                {"q": q, "kind": q["type"], "chart": chart, "data": data}
            )
    return request.app.state.templates.TemplateResponse(
        "admin_survey.html",
        {
            "request": request,
            "blocks": blocks,
            "total": survey_mod.total_submissions(db),
            "enabled": survey_mod.is_enabled(db),
        },
    )


@router.get("/admin/export")
def admin_export(
    request: Request,
    _user: str = Depends(require_admin),
) -> Response:
    """Stream a tar.gz containing the SQLite DB + chain JSONL.

    The /admin/export route is the post-course reconciliation artifact.
    Bound to 127.0.0.1 (R-6) and basic-auth gated so only the
    instructor on the local box can pull it.
    """
    db_path: Path = request.app.state.db_path
    chain_log = Path(os.getenv("BIO334_CHAIN_LOG", str(DEFAULT_LOG_PATH)))

    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz") as tar:
        if db_path.exists():
            tar.add(db_path, arcname=db_path.name)
        if chain_log.exists():
            tar.add(chain_log, arcname=chain_log.name)
    buf.seek(0)

    fname = f"bio334_export_{int(time.time())}.tar.gz"
    return StreamingResponse(
        iter([buf.getvalue()]),
        media_type="application/gzip",
        headers={"Content-Disposition": f'attachment; filename="{fname}"'},
    )
