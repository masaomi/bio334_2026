"""FastAPI application factory for BIO334 Teaching Chain web interface."""

from __future__ import annotations

import os
import secrets
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

from bio334_teaching.core.knowledge import KnowledgeBase
from bio334_teaching.core.progress import ProgressTracker
from bio334_teaching.core.timetable import TimetableManager
from bio334_teaching.core.prompt import SystemPromptBuilder
from bio334_teaching.core.chat import TeachingChat, ClaudeCodeChat
from bio334_teaching.core.sandbox import PythonSandbox

from bio334_teaching.interfaces.web.routes import router


def _package_dir() -> Path:
    """Return the bio334_teaching package root directory."""
    return Path(__file__).resolve().parent.parent.parent


def create_app(
    api_key: Optional[str] = None,
    proxy_url: Optional[str] = None,
    progress_dir: Optional[str] = None,
    backend: str = "auto",
) -> FastAPI:
    """Create and configure the FastAPI application.

    Parameters
    ----------
    api_key:
        Anthropic API key for the chat backend.
    proxy_url:
        Optional API proxy URL.
    progress_dir:
        Directory for storing student progress JSON files.
    backend:
        Chat backend: ``"api"`` (Anthropic API), ``"claude-code"``
        (local Claude CLI), or ``"auto"`` (Claude Code if available
        and no API key provided, else API).

    Returns
    -------
    FastAPI:
        Configured application instance.
    """
    # Initialize core dependencies
    knowledge = KnowledgeBase()
    progress = ProgressTracker(
        progress_dir=Path(progress_dir) if progress_dir else None
    )
    timetable = TimetableManager(knowledge)
    prompt_builder = SystemPromptBuilder(knowledge, timetable)

    # Select chat backend
    resolved_backend = backend
    if resolved_backend == "auto":
        import shutil
        has_api_key = bool(api_key or os.environ.get("ANTHROPIC_API_KEY"))
        has_claude_cli = shutil.which("claude") is not None
        if has_api_key:
            resolved_backend = "api"
        elif has_claude_cli:
            resolved_backend = "claude-code"
        else:
            resolved_backend = "api"  # Will show error when chat is used

    if resolved_backend == "claude-code":
        chat = ClaudeCodeChat(
            knowledge, progress, timetable, prompt_builder,
        )
        print("Chat backend: Claude Code CLI (no API key needed)")
    else:
        chat = TeachingChat(
            knowledge,
            progress,
            timetable,
            prompt_builder,
            api_key=api_key,
            proxy_url=proxy_url,
        )
        print("Chat backend: Anthropic API")

    sandbox = PythonSandbox()

    # Generate a CSRF-protection session token
    session_token = secrets.token_urlsafe(32)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        # Store dependencies in app.state for access from routes
        app.state.knowledge = knowledge
        app.state.progress = progress
        app.state.timetable = timetable
        app.state.chat = chat
        app.state.sandbox = sandbox
        app.state.session_token = session_token
        yield

    app = FastAPI(
        title="BIO334 Teaching Chain",
        description="Learn Python through population genetics with AI guidance",
        version="0.1.0",
        lifespan=lifespan,
    )

    # CORS middleware — only allow localhost origins
    app.add_middleware(
        CORSMiddleware,
        allow_origin_regex=r"^https?://(localhost|127\.0\.0\.1)(:\d+)?$",
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Mount static files
    static_dir = _package_dir() / "static"
    if static_dir.is_dir():
        app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

    # Register API routes
    app.include_router(router)

    # Session token verification middleware for API routes
    import logging
    _mw_logger = logging.getLogger("bio334.middleware")

    @app.middleware("http")
    async def verify_session_token(request: Request, call_next) -> Response:
        # Only enforce token on /api/ routes (not static or root)
        if request.url.path.startswith("/api/"):
            token = request.headers.get("X-Bio334-Token", "")
            # Also accept X-Course-Token for backward compatibility with JS client
            if not token:
                token = request.headers.get("X-Course-Token", "")
            if token != app.state.session_token:
                _mw_logger.warning(
                    "Token mismatch on %s: got=%r expect=%r",
                    request.url.path, token[:8] + "..." if token else "(empty)",
                    app.state.session_token[:8] + "...",
                )
                from fastapi.responses import JSONResponse

                return JSONResponse(
                    status_code=403,
                    content={"detail": "Invalid or missing session token"},
                )
        return await call_next(request)

    # Serve index.html at root, injecting the session token
    @app.get("/", response_class=HTMLResponse)
    async def serve_index():
        index_path = static_dir / "index.html"
        if not index_path.exists():
            return HTMLResponse(
                content="<h1>BIO334 Teaching Chain</h1><p>Static files not found.</p>",
                status_code=500,
            )
        html = index_path.read_text(encoding="utf-8")
        # Inject session token as a script tag before closing </head>
        token_script = (
            f'<script>window.__BIO334_TOKEN = "{app.state.session_token}";</script>'
        )
        html = html.replace("</head>", f"{token_script}\n</head>")
        return HTMLResponse(content=html)

    return app
