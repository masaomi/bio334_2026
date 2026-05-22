"""MCP server for BIO334 Teaching Chain.

Exposes teaching tools and resources via the Model Context Protocol,
enabling integration with MCP-compatible clients such as Claude Desktop.
"""

from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
from typing import Optional

from mcp.server.fastmcp import FastMCP

mcp = FastMCP(
    "bio334-teaching",
    instructions="""\
You are integrated with the BIO334 Teaching Chain. There are TWO modes of operation:

## MCP-Native Mode (No API Key Required)
When a student interacts with you directly through Claude Code or another MCP client,
YOU are the teaching LLM. Use the `get_teaching_context` tool at the start of each
session to load the teaching persona, timetable, and relevant knowledge. Then use
`knowledge_get` to retrieve specific skills as needed. Use `run_python` to execute
student code. Use `progress_update` to track learning.

In this mode, DO NOT call the `teach` tool — that would create a redundant API call.
Instead, embody the teaching persona yourself using the context from `get_teaching_context`.

## API-Proxy Mode (Requires API Key)
When a student uses the Web GUI, the `teach` tool handles everything via the Anthropic API.
The MCP client simply forwards messages.

## Quick Start for MCP-Native Mode
1. Call `get_teaching_context` with the student's first message
2. Read the returned system prompt and adopt that persona
3. Use `knowledge_get` to load specific skills when teaching a topic
4. Use `run_python` to execute code the student writes
5. Use `progress_update` after checkpoints to record understanding levels
""",
)

# Module-level references to core dependencies, initialized in run_mcp()
_knowledge = None
_progress = None
_timetable = None
_prompt_builder = None
_chat = None
_sandbox = None


def _package_dir() -> Path:
    """Return the bio334_teaching package root directory."""
    return Path(__file__).resolve().parent.parent.parent


def _data_dir() -> Path:
    """Return the package data directory."""
    return _package_dir() / "data"


def _init_dependencies(
    api_key: Optional[str] = None,
    proxy: Optional[str] = None,
) -> None:
    """Initialize core dependencies for the MCP server."""
    global _knowledge, _progress, _timetable, _prompt_builder, _chat, _sandbox

    from bio334_teaching.core.knowledge import KnowledgeBase
    from bio334_teaching.core.progress import ProgressTracker
    from bio334_teaching.core.timetable import TimetableManager
    from bio334_teaching.core.prompt import SystemPromptBuilder
    from bio334_teaching.core.chat import TeachingChat
    from bio334_teaching.core.sandbox import PythonSandbox

    _knowledge = KnowledgeBase()
    _progress = ProgressTracker()
    _timetable = TimetableManager(_knowledge)
    _prompt_builder = SystemPromptBuilder(_knowledge, _timetable)
    _chat = TeachingChat(
        _knowledge,
        _progress,
        _timetable,
        _prompt_builder,
        api_key=api_key,
        proxy_url=proxy,
    )
    _sandbox = PythonSandbox()


# ---------------------------------------------------------------------------
# Tools
# ---------------------------------------------------------------------------


@mcp.tool()
def get_teaching_context(
    user_message: str = "",
    session_id: str = "default",
) -> str:
    """Get the full teaching persona and context for MCP-native mode.

    Call this at the start of a teaching session when YOU (the MCP client LLM)
    are acting as the teacher. Returns the system prompt with teaching
    instructions, timetable context, student progress, and relevant knowledge.

    In MCP-native mode, you ARE the teaching LLM — adopt the persona described
    in the returned context. Do NOT call the `teach` tool in this mode.

    Parameters
    ----------
    user_message:
        The student's current message (used to select relevant knowledge skills).
    session_id:
        Student session identifier for progress tracking.

    Returns
    -------
    str:
        The composed teaching system prompt (~10K tokens) including:
        - Teaching persona and philosophy
        - Anti-regurgitation and guardrail rules
        - Current timetable context
        - Student progress state
        - Primary knowledge skill (full content)
        - Secondary knowledge skills (summaries)
    """
    if _prompt_builder is None or _progress is None:
        return "Error: Teaching system not initialized. Please restart the MCP server."
    try:
        progress = _progress.load(session_id)
        return _prompt_builder.build(progress, user_message)
    except Exception as exc:
        return f"Error building teaching context: {exc}"


@mcp.tool()
def teach(message: str, session_id: str = "default") -> str:
    """Send a message to the BIO334 teaching assistant via the Anthropic API.

    This is for API-PROXY MODE only — it makes a Claude API call with the
    full teaching system prompt. Requires an API key to be configured.

    In MCP-NATIVE MODE (when the MCP client LLM is acting as teacher),
    use `get_teaching_context` instead and handle the teaching yourself.

    Parameters
    ----------
    message:
        The student's question or message.
    session_id:
        Student session identifier for progress tracking.

    Returns
    -------
    str:
        The teaching assistant's response.
    """
    if _chat is None:
        return "Error: Teaching chat not initialized. Please restart the MCP server."
    try:
        return _chat.send_message_sync(message, session_id)
    except Exception as exc:
        return f"Error: {exc}"


@mcp.tool()
def run_python(code: str) -> str:
    """Execute Python code in a sandboxed environment.

    Runs the provided Python code in an isolated subprocess with safety
    limits (10s timeout, 256MB memory, 50KB output cap). Data files from
    the course are available in the working directory.

    Parameters
    ----------
    code:
        Python source code to execute.

    Returns
    -------
    str:
        Execution result including stdout, stderr, return code, and timing.
    """
    if _sandbox is None:
        return "Error: Sandbox not initialized."
    data_dir = _data_dir()
    result = _sandbox.execute(code, data_dir=data_dir if data_dir.is_dir() else None)
    parts: list[str] = []
    if result.stdout:
        parts.append(f"Output:\n{result.stdout}")
    if result.stderr:
        parts.append(f"Errors:\n{result.stderr}")
    parts.append(f"Return code: {result.return_code}")
    parts.append(f"Execution time: {result.execution_time_ms}ms")
    if result.truncated:
        parts.append("(output was truncated)")
    return "\n".join(parts)


@mcp.tool()
def knowledge_list() -> str:
    """List all available knowledge skills for BIO334.

    Returns a formatted list of skill names, descriptions, and versions.
    """
    if _knowledge is None:
        return "Error: Knowledge base not initialized."
    skills = _knowledge.list_skills()
    if not skills:
        return "No knowledge skills found."
    lines: list[str] = []
    for s in skills:
        lines.append(f"- {s.name} (v{s.version}): {s.description}")
    return "\n".join(lines)


@mcp.tool()
def knowledge_get(name: str) -> str:
    """Get the full content of a specific knowledge skill.

    Parameters
    ----------
    name:
        The skill name (e.g., ``popgen_nucleotide_diversity``).

    Returns
    -------
    str:
        The skill's markdown content, or an error message if not found.
    """
    if _knowledge is None:
        return "Error: Knowledge base not initialized."
    skill = _knowledge.get_skill(name)
    if skill is None:
        return f"Knowledge skill '{name}' not found. Use knowledge_list to see available skills."
    return f"# {skill.name}\n\n{skill.description}\n\nTags: {', '.join(skill.tags)}\n\n{skill.content}"


@mcp.tool()
def progress_get(session_id: str = "default") -> str:
    """Get the current progress for a student session.

    Parameters
    ----------
    session_id:
        Student session identifier.

    Returns
    -------
    str:
        Formatted progress summary with per-topic assessments.
    """
    if _progress is None:
        return "Error: Progress tracker not initialized."
    try:
        progress = _progress.load(session_id)
        data = asdict(progress)
        if not data.get("topics"):
            return f"Session '{session_id}': No topics assessed yet."
        lines = [f"Session: {session_id}", f"Day: {data['current_day']}", ""]
        for topic_name, tp in data["topics"].items():
            lines.append(f"  {topic_name}:")
            lines.append(f"    Conceptual: {tp['conceptual']}")
            lines.append(f"    Instruction: {tp['instruction']}")
            lines.append(f"    Implementation: {tp['implementation']}")
            lines.append(f"    Verification: {tp.get('verification', 'not_assessed')}")
        return "\n".join(lines)
    except ValueError as exc:
        return f"Error: {exc}"


@mcp.tool()
def progress_update(
    topic: str,
    dimension: str,
    level: str,
    session_id: str = "default",
) -> str:
    """Update a student's progress on a specific topic and dimension.

    Parameters
    ----------
    topic:
        Topic name (e.g., ``popgen_nucleotide_diversity``).
    dimension:
        Assessment dimension: ``conceptual``, ``instruction``, ``implementation``, or ``verification``.
    level:
        Assessment level: ``high``, ``medium``, ``low``, or ``not_assessed``.
    session_id:
        Student session identifier.

    Returns
    -------
    str:
        Confirmation message or error.
    """
    if _progress is None:
        return "Error: Progress tracker not initialized."
    try:
        _progress.update_topic(session_id, topic, dimension, level)
        return f"Updated {topic}.{dimension} = {level} for session {session_id}"
    except ValueError as exc:
        return f"Error: {exc}"


@mcp.tool()
def progress_reset(session_id: str = "default") -> str:
    """Reset (delete) all progress for a student session.

    Parameters
    ----------
    session_id:
        Student session identifier.

    Returns
    -------
    str:
        Confirmation message.
    """
    if _progress is None:
        return "Error: Progress tracker not initialized."
    try:
        _progress.reset(session_id)
        return f"Progress reset for session '{session_id}'."
    except ValueError as exc:
        return f"Error: {exc}"


@mcp.tool()
def timetable_now() -> str:
    """Get the current timetable context.

    Returns schedule information including the current block, whether
    class is in session, and upcoming activities.
    """
    if _timetable is None:
        return "Error: Timetable not initialized."
    return _timetable.get_context()


@mcp.tool()
def data_read(path: str) -> str:
    """Read a data file from the course data directory.

    Parameters
    ----------
    path:
        Relative path within the data directory (e.g., ``examples/example_sequences.fa``).

    Returns
    -------
    str:
        File contents (text), or an error message.
    """
    data_dir = _data_dir()
    file_path = (data_dir / path).resolve()

    # Security: ensure the resolved path is within data_dir
    try:
        file_path.relative_to(data_dir.resolve())
    except ValueError:
        return "Error: Path traversal not allowed."

    if not file_path.exists():
        return f"Error: File '{path}' not found in data directory."
    if not file_path.is_file():
        return f"Error: '{path}' is not a file."

    try:
        content = file_path.read_text(encoding="utf-8")
        # Truncate large files
        if len(content) > 50_000:
            content = content[:50_000] + "\n... [truncated at 50KB]"
        return content
    except UnicodeDecodeError:
        return f"Error: '{path}' is a binary file and cannot be read as text."


# ---------------------------------------------------------------------------
# Resources
# ---------------------------------------------------------------------------


@mcp.resource("knowledge://{name}")
def knowledge_resource(name: str) -> str:
    """Access a knowledge skill as an MCP resource.

    Parameters
    ----------
    name:
        The skill name.
    """
    if _knowledge is None:
        return "Knowledge base not initialized."
    skill = _knowledge.get_skill(name)
    if skill is None:
        return f"Knowledge skill '{name}' not found."
    return skill.content


@mcp.resource("data://{path}")
def data_resource(path: str) -> str:
    """Access a data file as an MCP resource.

    Parameters
    ----------
    path:
        Relative path within the data directory.
    """
    return data_read(path)


# ---------------------------------------------------------------------------
# Server entry point
# ---------------------------------------------------------------------------


def run_mcp(
    http: bool = False,
    port: int = 8335,
    api_key: Optional[str] = None,
    proxy: Optional[str] = None,
) -> None:
    """Start the MCP server.

    Parameters
    ----------
    http:
        If True, use streamable HTTP transport on the given port.
        If False (default), use stdio transport.
    port:
        HTTP port when using HTTP transport (default 8335).
    api_key:
        Anthropic API key for the teaching chat.
    proxy:
        Optional API proxy URL.
    """
    _init_dependencies(api_key=api_key, proxy=proxy)

    if http:
        mcp.run(transport="streamable-http", port=port)
    else:
        mcp.run()
