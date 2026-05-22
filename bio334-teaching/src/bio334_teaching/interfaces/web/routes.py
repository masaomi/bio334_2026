"""API routes for BIO334 Teaching Chain web interface."""

from __future__ import annotations

import json
import logging
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import AsyncIterator

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse, StreamingResponse


def _now_iso() -> str:
    """Return current UTC time as ISO 8601 string."""
    return datetime.now(timezone.utc).isoformat()

logger = logging.getLogger("bio334.routes")

router = APIRouter(prefix="/api")


def _package_dir() -> Path:
    """Return the bio334_teaching package root directory."""
    return Path(__file__).resolve().parent.parent.parent


def _data_dir() -> Path:
    """Return the package data directory."""
    return _package_dir() / "data"


def _workspace_dir() -> Path:
    """Return the user workspace directory (created on first access)."""
    ws = _package_dir() / "workspace"
    ws.mkdir(exist_ok=True)
    return ws


@router.post("/chat")
async def chat(request: Request) -> StreamingResponse:
    """Stream a teaching response via Server-Sent Events.

    Expects JSON body: ``{"message": str, "session_id": str}``.
    Returns SSE stream with ``data: {"text": "chunk"}`` events
    and a final ``data: {"done": true}`` event.
    """
    body = await request.json()
    message: str = body.get("message", "")
    session_id: str = body.get("session_id", "default")

    chat_engine = request.app.state.chat

    if not message.strip():
        return JSONResponse(
            status_code=400,
            content={"detail": "Message cannot be empty"},
        )

    async def event_stream() -> AsyncIterator[str]:
        try:
            logger.info("Chat request: session=%s, message=%s", session_id, message[:80])
            async for chunk in chat_engine.send_message(message, session_id):
                # Check if chunk is a JSON metadata string from ClaudeCodeChat
                if isinstance(chunk, str) and chunk.startswith('{"type":') and '"meta"' in chunk[:30]:
                    try:
                        meta = json.loads(chunk)
                        logger.info("Meta event: %s", meta)
                        yield f"data: {json.dumps(meta)}\n\n"
                        continue
                    except json.JSONDecodeError:
                        pass
                yield f"data: {json.dumps({'type': 'text', 'text': chunk})}\n\n"
            yield f"data: {json.dumps({'done': True})}\n\n"
            logger.info("Chat stream complete for session=%s", session_id)
        except Exception as exc:
            logger.error("Chat stream error: %s", exc, exc_info=True)
            error_msg = str(exc) if str(exc) else "Internal server error"
            yield f"data: {json.dumps({'type': 'error', 'message': error_msg})}\n\n"
            yield f"data: {json.dumps({'done': True})}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/run")
async def run_code(request: Request) -> JSONResponse:
    """Execute Python code in the sandbox.

    Expects JSON body: ``{"code": str, "args": str (optional)}``.
    The ``args`` string is split by whitespace into a list and
    passed as sys.argv[1:] to the student script.
    Returns the ExecutionResult as JSON.
    """
    body = await request.json()
    code: str = body.get("code", "")
    args_str: str = body.get("args", "")

    if not code.strip():
        return JSONResponse(
            status_code=400,
            content={"detail": "Code cannot be empty"},
        )

    # Parse args string into a list (simple whitespace split)
    args: list[str] | None = None
    if args_str.strip():
        import shlex
        try:
            args = shlex.split(args_str)
        except ValueError:
            args = args_str.split()

    sandbox = request.app.state.sandbox
    data_dir = _data_dir()
    ws_dir = _workspace_dir()

    try:
        result = sandbox.execute(
            code,
            data_dir=data_dir if data_dir.is_dir() else None,
            workspace_dir=ws_dir if ws_dir.is_dir() else None,
            args=args,
        )
        return JSONResponse(content=asdict(result))
    except Exception as exc:
        return JSONResponse(
            status_code=500,
            content={
                "stdout": "",
                "stderr": f"Sandbox error: {exc}",
                "return_code": -1,
                "execution_time_ms": 0,
                "truncated": False,
            },
        )


@router.get("/data-files")
async def list_data_files(request: Request) -> JSONResponse:
    """List available data and workspace files for the file browser.

    Returns ``{"data": [...], "workspace": [...]}`` where each entry
    is ``{"name": str, "path": str, "size": int}``.
    Data files are read-only course materials; workspace files are
    user-created and editable.
    """
    # Data files (read-only)
    data_dir = _data_dir()
    data_files: list[dict] = []
    if data_dir.is_dir():
        for item in sorted(data_dir.rglob("*")):
            if item.is_file():
                rel = str(item.relative_to(data_dir))
                data_files.append({
                    "name": item.name,
                    "path": rel,
                    "size": item.stat().st_size,
                })

    # Workspace files (user-created)
    ws_dir = _workspace_dir()
    ws_files: list[dict] = []
    for item in sorted(ws_dir.iterdir()):
        if item.is_file():
            ws_files.append({
                "name": item.name,
                "path": item.name,
                "size": item.stat().st_size,
            })

    return JSONResponse(content={
        "data": data_files,
        "workspace": ws_files,
    })


@router.post("/workspace/save")
async def save_workspace_file(request: Request) -> JSONResponse:
    """Save a file to the user workspace.

    Expects JSON body: ``{"filename": str, "content": str}``.
    Filenames are sanitized to prevent path traversal.
    """
    body = await request.json()
    filename: str = body.get("filename", "").strip()
    content: str = body.get("content", "")

    if not filename:
        return JSONResponse(
            status_code=400,
            content={"detail": "Filename is required"},
        )

    # Sanitize: only allow simple filenames (no path separators)
    import re
    safe_name = re.sub(r'[^\w.\-]', '_', filename)
    if not safe_name or safe_name.startswith('.'):
        return JSONResponse(
            status_code=400,
            content={"detail": "Invalid filename"},
        )

    ws_dir = _workspace_dir()
    filepath = ws_dir / safe_name
    filepath.write_text(content, encoding="utf-8")

    return JSONResponse(content={
        "status": "ok",
        "filename": safe_name,
        "size": filepath.stat().st_size,
    })


@router.delete("/workspace/{filename}")
async def delete_workspace_file(filename: str, request: Request) -> JSONResponse:
    """Delete a file from the user workspace."""
    import re
    safe_name = re.sub(r'[^\w.\-]', '_', filename)

    ws_dir = _workspace_dir()
    filepath = ws_dir / safe_name

    if not filepath.exists():
        return JSONResponse(
            status_code=404,
            content={"detail": f"File '{safe_name}' not found"},
        )

    filepath.unlink()
    return JSONResponse(content={"status": "ok", "filename": safe_name})


@router.get("/workspace/{filename}")
async def get_workspace_file(filename: str, request: Request) -> JSONResponse:
    """Read a workspace file's content."""
    import re
    safe_name = re.sub(r'[^\w.\-]', '_', filename)

    ws_dir = _workspace_dir()
    filepath = ws_dir / safe_name

    if not filepath.exists():
        return JSONResponse(
            status_code=404,
            content={"detail": f"File '{safe_name}' not found"},
        )

    content = filepath.read_text(encoding="utf-8", errors="replace")
    return JSONResponse(content={
        "filename": safe_name,
        "content": content,
        "size": filepath.stat().st_size,
    })


@router.get("/knowledge")
async def list_knowledge(request: Request) -> JSONResponse:
    """List all knowledge skills.

    Returns a JSON array of ``{"name", "description", "version"}`` objects.
    """
    knowledge = request.app.state.knowledge
    skills = knowledge.list_skills()
    return JSONResponse(content=[
        {"name": s.name, "description": s.description, "version": s.version}
        for s in skills
    ])


@router.get("/knowledge/{name}")
async def get_knowledge(name: str, request: Request) -> JSONResponse:
    """Get a specific knowledge skill by name.

    Returns the full skill content including frontmatter and markdown body.
    """
    knowledge = request.app.state.knowledge
    skill = knowledge.get_skill(name)
    if skill is None:
        return JSONResponse(
            status_code=404,
            content={"detail": f"Knowledge skill '{name}' not found"},
        )
    return JSONResponse(
        content={
            "name": skill.name,
            "description": skill.description,
            "version": skill.version,
            "tags": skill.tags,
            "content": skill.content,
        }
    )


@router.get("/timetable")
async def get_timetable(request: Request) -> JSONResponse:
    """Get the full timetable schedule grouped by day.

    Returns a structured object with ``days`` array and current position,
    formatted for the timeline frontend component.
    """
    timetable = request.app.state.timetable
    schedule = timetable.get_schedule()
    current_block_data = timetable.get_current_block()

    # Group entries by day
    days_map: dict[int, list] = {}
    for entry in schedule:
        day_num = entry.get("day", 0)
        if day_num not in days_map:
            days_map[day_num] = []
        days_map[day_num].append({
            "id": entry.get("block_id", ""),
            "title": entry.get("topic", ""),
            "type": entry.get("type", ""),
            "time": entry.get("time", ""),
            "duration_min": entry.get("duration_min", 0),
            "skill_ref": entry.get("skill_ref", ""),
        })

    days = []
    day_dates = {1: "May 14", 2: "May 15", 3: "May 16"}
    for day_num in sorted(days_map.keys()):
        if day_num == 0:
            continue
        days.append({
            "number": day_num,
            "label": f"Day {day_num}",
            "date": day_dates.get(day_num, ""),
            "blocks": days_map[day_num],
        })

    current_day = current_block_data.get("day") if current_block_data else None
    current_block_id = current_block_data.get("block_id") if current_block_data else None
    current_topic = current_block_data.get("topic") if current_block_data else None

    return JSONResponse(content={
        "days": days,
        "current_day": current_day,
        "current_block": current_block_id,
        "current_topic": current_topic,
        "in_class": timetable.is_class_hours(),
    })


@router.post("/session/{session_id}/save")
async def save_session(session_id: str, request: Request) -> JSONResponse:
    """Save chat history and create a save point.

    Expects JSON body::

        {
          "chat_history": [{"role": str, "content": str}, ...],
          "label": str  (optional, brief description of save point)
        }

    Appends a save point with timestamp, message count, and label.
    """
    body = await request.json()
    chat_history: list[dict] = body.get("chat_history", [])
    label: str = body.get("label", "Save point")

    progress_tracker = request.app.state.progress
    try:
        progress = progress_tracker.load(session_id)
        progress.chat_history = chat_history
        save_point = {
            "timestamp": _now_iso(),
            "message_count": len(chat_history),
            "label": label[:100],  # Truncate to 100 chars
        }
        progress.save_points.append(save_point)
        progress_tracker.save(session_id, progress)
        return JSONResponse(content={
            "status": "ok",
            "save_point": save_point,
            "total_save_points": len(progress.save_points),
        })
    except ValueError as exc:
        return JSONResponse(
            status_code=400,
            content={"detail": str(exc)},
        )


@router.get("/session/{session_id}/load")
async def load_session(session_id: str, request: Request) -> JSONResponse:
    """Load saved chat history and save points for a session."""
    progress_tracker = request.app.state.progress
    try:
        progress = progress_tracker.load(session_id)
        return JSONResponse(content={
            "chat_history": progress.chat_history,
            "save_points": progress.save_points,
        })
    except ValueError as exc:
        return JSONResponse(
            status_code=400,
            content={"detail": str(exc)},
        )


@router.get("/progress/{session_id}")
async def get_progress(session_id: str, request: Request) -> JSONResponse:
    """Get student progress for a session.

    Returns the full StudentProgress as JSON including per-topic
    assessments across 4 dimensions, save points, and chat history.
    """
    progress_tracker = request.app.state.progress
    try:
        progress = progress_tracker.load(session_id)
        return JSONResponse(content=asdict(progress))
    except ValueError as exc:
        return JSONResponse(
            status_code=400,
            content={"detail": str(exc)},
        )


@router.post("/progress/{session_id}/update")
async def update_progress(session_id: str, request: Request) -> JSONResponse:
    """Update a single topic's progress dimension.

    Expects JSON body: ``{"topic": str, "dimension": str, "level": str}``.

    - ``dimension``: one of ``conceptual``, ``instruction``, ``implementation``, ``verification``
    - ``level``: one of ``high``, ``medium``, ``low``, ``not_assessed``
    """
    body = await request.json()
    topic: str = body.get("topic", "")
    dimension: str = body.get("dimension", "")
    level: str = body.get("level", "")

    if not all([topic, dimension, level]):
        return JSONResponse(
            status_code=400,
            content={"detail": "Missing required fields: topic, dimension, level"},
        )

    progress_tracker = request.app.state.progress
    try:
        progress_tracker.update_topic(session_id, topic, dimension, level)
        return JSONResponse(content={"status": "ok"})
    except ValueError as exc:
        return JSONResponse(
            status_code=400,
            content={"detail": str(exc)},
        )


@router.post("/progress/{session_id}/reset")
async def reset_progress(session_id: str, request: Request) -> JSONResponse:
    """Reset (delete) student progress for a session."""
    progress_tracker = request.app.state.progress
    try:
        progress_tracker.reset(session_id)
        return JSONResponse(content={"status": "ok"})
    except ValueError as exc:
        return JSONResponse(
            status_code=400,
            content={"detail": str(exc)},
        )


@router.get("/files")
async def list_files(request: Request) -> JSONResponse:
    """List available data files in the package's data directory.

    Returns a JSON array of ``{"name": str, "path": str, "size": int}``
    objects for each file found.
    """
    data_dir = _data_dir()
    if not data_dir.is_dir():
        return JSONResponse(content=[])

    files: list[dict] = []
    for item in sorted(data_dir.rglob("*")):
        if item.is_file():
            rel_path = item.relative_to(data_dir)
            files.append(
                {
                    "name": item.name,
                    "path": str(rel_path),
                    "size": item.stat().st_size,
                }
            )
    return JSONResponse(content=files)
