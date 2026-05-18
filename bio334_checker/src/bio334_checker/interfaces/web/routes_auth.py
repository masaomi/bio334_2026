"""Auth routes: /, /register, /login, /logout, /me.

Per ARCHITECTURE.md §5 + §9.1 (v0.3 R-3, R-7):

- ``GET  /``           landing (register form or ``?u=`` bootstrap)
- ``POST /register``   issue handle + session cookie
- ``GET  /login``      consume reusable ``?u=<handle>`` token; issue
                       fresh session cookie; 302 to ``/me``
- ``POST /logout``     revoke session
- ``GET  /me``         personal page (placeholder; full progress in Phase 4)
"""

from __future__ import annotations

import sqlite3

from fastapi import APIRouter, Depends, Form, HTTPException, Request, Response, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from bio334_checker.core import auth
from bio334_checker.core.qr import qr_data_url
from bio334_checker.interfaces.web.dependencies import (
    SESSION_COOKIE_NAME,
    clear_session_cookie,
    get_current_handle,
    get_db,
    get_session,
    set_session_cookie,
)


router = APIRouter()


def _templates(request: Request) -> Jinja2Templates:
    return request.app.state.templates


# ----------------------------------------------------------------------------
# Landing
# ----------------------------------------------------------------------------

@router.get("/")
def landing(
    request: Request,
    u: str | None = None,
    db: sqlite3.Connection = Depends(get_db),
) -> Response:
    """Landing route.

    Per ARCHITECTURE.md §5.3, ``GET /?u=<handle>`` is the canonical
    reusable bootstrap URL given to students (QR + paper memo). If ``u``
    is present, this route delegates to the same logic as ``/login`` so
    the URL token is consumed once-per-visit and a fresh session cookie
    is issued. Without ``u``, this is just the landing page (register
    form), or a redirect to ``/me`` if the user already has a valid
    session cookie.
    """
    if u:
        return _bootstrap_with_handle(request, db, u)
    cookie = request.cookies.get(SESSION_COOKIE_NAME)
    if cookie and auth.lookup_session(db, cookie) is not None:
        return RedirectResponse("/me", status_code=status.HTTP_303_SEE_OTHER)
    return _templates(request).TemplateResponse(
        "landing.html", {"request": request}
    )


def _bootstrap_with_handle(
    request: Request, db: sqlite3.Connection, u: str
) -> Response:
    """Shared bootstrap logic used by ``GET /?u=`` and ``GET /login?u=``."""
    handle = u.strip().lower()
    ip = request.client.host if request.client else "?"

    if not auth.check_login_allowed(db, ip, handle):
        return _too_many_attempts(request)

    user_row = auth.get_user(db, handle)
    if not auth.is_active_user(user_row):
        auth.record_login_failure(db, ip, handle)
        return _login_failed(request, status.HTTP_401_UNAUTHORIZED)

    session = auth.issue_session(db, handle)
    redirect = RedirectResponse("/me", status_code=status.HTTP_303_SEE_OTHER)
    set_session_cookie(redirect, session)
    return redirect


# ----------------------------------------------------------------------------
# Register
# ----------------------------------------------------------------------------

@router.post("/register", response_class=HTMLResponse)
def register(
    request: Request,
    response: Response,
    display_name: str = Form(...),
    db: sqlite3.Connection = Depends(get_db),
) -> HTMLResponse:
    name = display_name.strip()[:32]
    if not name:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="display_name required")

    handle = auth.issue_handle(db, name)
    session = auth.issue_session(db, handle)
    auth._record_event(  # type: ignore[attr-defined]
        db, ip=request.client.host if request.client else "?", handle=handle,
        event_type="register", detail={"display_name": name},
    )

    base = str(request.base_url).rstrip("/")
    handle_url = f"{base}/?u={handle}"
    qr = qr_data_url(handle_url)

    html = _templates(request).TemplateResponse(
        "registered.html",
        {
            "request": request,
            "handle": handle,
            "display_name": name,
            "handle_url": handle_url,
            "qr_data_url": qr,
        },
    )
    set_session_cookie(html, session)
    return html


# ----------------------------------------------------------------------------
# Login (reusable bootstrap from ?u=)
# ----------------------------------------------------------------------------

@router.get("/login")
def login(
    request: Request,
    u: str | None = None,
    db: sqlite3.Connection = Depends(get_db),
) -> Response:
    """Alias for ``GET /?u=<handle>``. Same reusable bootstrap, same semantics."""
    if not u:
        return RedirectResponse("/", status_code=status.HTTP_303_SEE_OTHER)
    return _bootstrap_with_handle(request, db, u)


def _login_failed(request: Request, code: int) -> HTMLResponse:
    return _templates(request).TemplateResponse(
        "login_failed.html",
        {"request": request, "message": "Unknown or revoked handle."},
        status_code=code,
    )


def _too_many_attempts(request: Request) -> HTMLResponse:
    return _templates(request).TemplateResponse(
        "login_failed.html",
        {
            "request": request,
            "message": "Too many failed attempts. Please wait a few minutes and try again.",
        },
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
    )


# ----------------------------------------------------------------------------
# Logout
# ----------------------------------------------------------------------------

@router.post("/logout")
def logout(
    session: auth.Session = Depends(get_session),
    db: sqlite3.Connection = Depends(get_db),
) -> Response:
    auth.revoke_session(db, session.cookie_id)
    redirect = RedirectResponse("/", status_code=status.HTTP_303_SEE_OTHER)
    clear_session_cookie(redirect)
    return redirect


# ----------------------------------------------------------------------------
# /me (personal page; full progress lands in Phase 4)
# ----------------------------------------------------------------------------

@router.get("/me", response_class=HTMLResponse)
def me(
    request: Request,
    handle: str = Depends(get_current_handle),
    db: sqlite3.Connection = Depends(get_db),
) -> HTMLResponse:
    from bio334_checker.core import progress as progress_mod
    from bio334_checker.core import survey as survey_mod

    row = auth.get_user(db, handle)
    personal = progress_mod.personal_progress(db, handle, student_view=True)
    passed = sum(1 for p in personal if p.passed)
    attempted = sum(1 for p in personal if p.attempted)
    total_score = sum(p.best_score for p in personal if p.best_score is not None)
    return _templates(request).TemplateResponse(
        "me.html",
        {
            "request": request,
            "handle": handle,
            "display_name": row["display_name"] if row else "?",
            "personal": personal,
            "passed_count": passed,
            "attempted_count": attempted,
            "total_count": len(personal),
            "total_score": total_score,
            "survey_enabled": survey_mod.is_enabled(db),
        },
    )
