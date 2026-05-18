"""FastAPI app factory.

Per ARCHITECTURE.md §9.1:
- Cookie-based auth (HttpOnly + Secure + SameSite=Lax via dependencies).
- ``/admin*`` is bound to 127.0.0.1 — verified at startup. The app refuses
  to start if it detects a non-loopback bind for these routes.

Phase 1 wires only the auth router. Other routers (exercises, submit, hint,
admin, dashboard) are added in later phases.
"""

from __future__ import annotations

import os
from importlib import resources
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from bio334_checker.chain.client import KCClient
from bio334_checker.chain.worker import BackgroundWorker
from bio334_checker.db.connection import DEFAULT_DB_PATH, init_db
from bio334_checker.interfaces.web.routes_admin import router as admin_router
from bio334_checker.interfaces.web.routes_auth import router as auth_router
from bio334_checker.interfaces.web.routes_dashboard import router as dashboard_router
from bio334_checker.interfaces.web.routes_exercises import router as exercises_router
from bio334_checker.interfaces.web.routes_hint import router as hint_router
from bio334_checker.interfaces.web.routes_leaderboard import router as leaderboard_router
from bio334_checker.interfaces.web.routes_submit import router as submit_router
from bio334_checker.interfaces.web.routes_survey import router as survey_router


def _templates_dir() -> Path:
    return Path(resources.files("bio334_checker.interfaces.web").joinpath("templates"))


def _register_markdown_filter(templates: Jinja2Templates) -> None:
    """Add a ``markdown`` Jinja2 filter that safely renders Markdown to HTML.

    Per ARCHITECTURE.md §9.1 (R-9): use ``markdown-it-py`` with HTML
    DISABLED — raw HTML in the source is text-escaped, not rendered.
    Output is HTML and can be piped through ``| safe`` in templates.
    """
    from markupsafe import Markup
    from markdown_it import MarkdownIt

    md = MarkdownIt("commonmark", {"html": False, "linkify": True, "breaks": False})

    def _render(text: str | None) -> Markup:
        return Markup(md.render(text or ""))

    templates.env.filters["markdown"] = _render


def create_app(
    *,
    db_path: Path | None = None,
    host: str | None = None,
    kc_client: KCClient | None = None,
    enable_worker: bool = False,
    admin_allowed_hosts: tuple[str, ...] = ("127.0.0.1", "::1"),
) -> FastAPI:
    """Build a configured FastAPI app.

    Parameters
    ----------
    db_path:
        SQLite file. Defaults to ``$BIO334_DB`` or ``./bio334_checker.db``.
    host:
        The interface this app intends to bind to. Used by the admin
        bind-check; pass the value you'll give to uvicorn. ``None`` skips the
        check (e.g., test client).
    kc_client:
        Override the chain client. ``None`` uses the env-driven default.
    enable_worker:
        Start the singleton background worker (drain + chain). Tests pass
        ``False`` and exercise the drain code synchronously.
    """
    app = FastAPI(title="bio334-checker", version="0.1.0.dev0")
    app.state.db_path = db_path or DEFAULT_DB_PATH
    templates = Jinja2Templates(directory=str(_templates_dir()))
    _register_markdown_filter(templates)
    app.state.templates = templates
    app.state.host = host
    app.state.kc_client = kc_client
    app.state.worker: BackgroundWorker | None = None
    app.state.admin_allowed_hosts = admin_allowed_hosts

    @app.on_event("startup")
    async def _startup() -> None:
        init_db(app.state.db_path)
        _verify_admin_bind(app)
        if enable_worker:
            worker = BackgroundWorker(
                db_path=app.state.db_path,
                kc_client=app.state.kc_client,
            )
            await worker.start()
            app.state.worker = worker

    @app.on_event("shutdown")
    async def _shutdown() -> None:
        worker: BackgroundWorker | None = app.state.worker
        if worker is not None:
            await worker.stop()

    app.include_router(auth_router)
    app.include_router(exercises_router)
    app.include_router(submit_router)
    app.include_router(hint_router)
    app.include_router(dashboard_router)
    app.include_router(leaderboard_router)
    app.include_router(survey_router)
    app.include_router(admin_router)

    # /admin* loopback guard (v0.3 R-6). Enforces 127.0.0.1 access even if a
    # future code change accidentally exposes an admin route on a different
    # interface. The startup _verify_admin_bind() also refuses to bind a
    # non-loopback host when the worker is enabled.
    @app.middleware("http")
    async def _admin_loopback_guard(request: Request, call_next):
        if request.url.path.startswith("/admin"):
            client = request.client.host if request.client else ""
            allowed = request.app.state.admin_allowed_hosts
            if client not in allowed:
                return HTMLResponse(
                    "/admin* is restricted to loopback.",
                    status_code=status.HTTP_403_FORBIDDEN,
                )
        return await call_next(request)

    return app


def _verify_admin_bind(app: FastAPI) -> None:
    """Refuse to start if the configured bind exposes /admin* publicly.

    v0.3 R-6: ``/admin`` and ``/admin/export`` must be bound to 127.0.0.1.
    Remote instructor access is via SSH tunnel.
    """
    host = app.state.host
    if host is None:
        return  # no host known (e.g., TestClient) — skip
    if host in ("127.0.0.1", "localhost", "::1"):
        return
    raise RuntimeError(
        f"refusing to start: /admin* must be bound to 127.0.0.1, but host={host!r}. "
        f"Set BIO334_HOST=127.0.0.1 (default), or use SSH tunnel for remote access."
    )
