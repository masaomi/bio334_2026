"""FastAPI dependencies: per-request DB connection, current session, current user.

The session cookie is named ``bio334_session``. POST endpoints require the
cookie (I-AUTH-3); a bare ``?u=`` cannot mutate state.

In production, the cookie has the ``Secure`` flag set (v0.3 R-7), which
requires HTTPS. For local dev / tests we honor ``BIO334_INSECURE_COOKIE=1``
to drop the flag (state explicitly so it never silently happens in prod).
"""

from __future__ import annotations

import os
import sqlite3
from typing import Iterator

from fastapi import Depends, HTTPException, Request, Response, status

from bio334_checker.core import auth
from bio334_checker.db.connection import connect


SESSION_COOKIE_NAME = "bio334_session"
SESSION_COOKIE_MAX_AGE = 24 * 60 * 60  # 24h, matches sliding TTL window


def _cookie_secure() -> bool:
    return os.getenv("BIO334_INSECURE_COOKIE", "").strip() not in ("1", "true", "yes")


def get_db(request: Request) -> Iterator[sqlite3.Connection]:
    """Open a SQLite connection per request. Path is injected from app state."""
    db_path = request.app.state.db_path
    conn = connect(db_path)
    try:
        yield conn
    finally:
        conn.close()


def get_session(
    request: Request, db: sqlite3.Connection = Depends(get_db)
) -> auth.Session:
    """Look up + slide-extend the current session. Raises 401 if absent/expired."""
    cookie = request.cookies.get(SESSION_COOKIE_NAME)
    if not cookie:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="not authenticated")
    sess = auth.lookup_session(db, cookie)
    if sess is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="session invalid")
    return auth.touch_session(db, sess)


def get_current_handle(session: auth.Session = Depends(get_session)) -> str:
    return session.handle


def set_session_cookie(response: Response, session: auth.Session) -> None:
    """Apply v0.3 R-7 cookie attributes: HttpOnly + Secure + SameSite=Lax."""
    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=session.cookie_id,
        max_age=SESSION_COOKIE_MAX_AGE,
        httponly=True,
        secure=_cookie_secure(),
        samesite="lax",
        path="/",
    )


def clear_session_cookie(response: Response) -> None:
    response.delete_cookie(SESSION_COOKIE_NAME, path="/")
