"""Chat interface for BIO334 teaching chain.

Provides both async streaming and synchronous interfaces to the Claude API,
with automatic progress tracking and message history management.

Supports two backends:
- **api** (default): Direct Anthropic API calls via the ``anthropic`` package.
- **claude-code**: Uses the locally installed ``claude`` CLI as a subprocess.
  No API key is needed — the CLI uses its own authentication.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from collections.abc import AsyncIterator
from datetime import datetime, timezone
from typing import Optional

from bio334_teaching.core.knowledge import KnowledgeBase
from bio334_teaching.core.progress import ProgressTracker, StudentProgress, TopicProgress
from bio334_teaching.core.prompt import SystemPromptBuilder
from bio334_teaching.core.timetable import TimetableManager

# Default model
DEFAULT_MODEL = "claude-sonnet-4-20250514"
CLAUDE_CODE_MODEL = "sonnet"

# Maximum messages to keep per session
MAX_HISTORY_MESSAGES = 20

# Error messages
_ERROR_UNAVAILABLE = (
    "The AI tutor is currently unavailable. Please check your internet "
    "connection and try again in a moment."
)
_ERROR_RATE_LIMIT = (
    "Too many requests. Please wait a moment before sending another message."
)
_ERROR_GENERIC = (
    "An unexpected error occurred while communicating with the AI tutor. "
    "Please try again."
)

# Try to import anthropic; set a flag if unavailable
try:
    import anthropic

    _ANTHROPIC_AVAILABLE = True
except ImportError:
    anthropic = None  # type: ignore[assignment]
    _ANTHROPIC_AVAILABLE = False


def _now_iso() -> str:
    """Return current UTC time as ISO 8601 string."""
    return datetime.now(timezone.utc).isoformat()


# ------------------------------------------------------------------
# Topic detection keywords → topic names
# ------------------------------------------------------------------

_TOPIC_KEYWORDS: dict[str, list[str]] = {
    "python_basics_for_bio": [
        "variable", "list", "dict", "tuple", "set", "loop", "for loop",
        "while loop", "if else", "conditional", "data type", "string",
        "integer", "float", "boolean", "python basics", "control flow",
    ],
    "python_file_io_parsing": [
        "file", "open(", "read", "write", "sys.argv", "fasta parsing",
        "file i/o", "parsing", "command line", "command-line",
    ],
    "python_functions_modules": [
        "function", "def ", "return", "module", "import", "refactor",
        "reusab", "abstraction",
    ],
    "python_batch_processing": [
        "batch", "glob", "os.listdir", "shell script", "multiple files",
        "automation",
    ],
    "popgen_nucleotide_diversity": [
        "nucleotide diversity", "pi ", "π", "pairwise difference",
        "pairwise comparison", "genetic diversity",
    ],
    "popgen_segregating_sites": [
        "segregating site", "snp", "theta", "θ", "watterson",
        "polymorphi",
    ],
    "popgen_tajimas_d": [
        "tajima", "tajima's d", "neutrality test", "selection test",
        "d statistic",
    ],
    "popgen_wright_fisher": [
        "wright-fisher", "wright fisher", "genetic drift", "simulation",
        "population size", "bottleneck", "expansion",
    ],
    "akamchatica_biology": [
        "kamchatica", "halleri", "lyrata", "homoeolog", "subgenome",
        "allotetraploid", "hma4", "heavy metal", "d_a", "net divergence",
        "pi_between", "dxy", "divergence between",
    ],
    "bioinformatics_file_formats": [
        "fasta", "vcf", "file format", "genotype", "variant call",
    ],
}

# Positive feedback indicators (AI confirms student understanding)
_POSITIVE_INDICATORS = [
    "correct", "exactly", "well done", "great job", "that's right",
    "good explanation", "you've got it", "nice work", "perfect",
    "excellent", "spot on", "you understand", "good answer",
]

# Indicators that code was discussed
_CODE_INDICATORS = [
    "```python", "```py", "def ", "import ", "for ", "function",
]

# Indicators of conceptual discussion
_CONCEPT_INDICATORS = [
    "means that", "measures", "represents", "defined as", "formula",
    "biologically", "interpretation", "the reason", "because",
]


def _detect_topics(text: str) -> list[str]:
    """Detect which topics are mentioned in the text."""
    text_lower = text.lower()
    found = []
    for topic, keywords in _TOPIC_KEYWORDS.items():
        for kw in keywords:
            if kw.lower() in text_lower:
                found.append(topic)
                break
    return found


def _do_auto_update_progress(
    progress_tracker: ProgressTracker,
    session_id: str,
    user_message: str,
    ai_response: str,
) -> None:
    """Shared progress auto-update logic for both chat backends.

    Key design decisions:
    - Topic detection uses ONLY the student's message (not AI response),
      so AI explanations don't inflate progress.
    - Level starts at "low" only when the student actively engages with
      a topic (asks a substantive question or provides an explanation).
    - "medium" requires the student to demonstrate understanding
      (long explanation + positive AI feedback).
    - "high" is never set automatically — only via explicit checkpoint
      assessment or manual API call.
    """
    student_progress = progress_tracker.load(session_id)
    student_progress.last_active = _now_iso()

    response_lower = ai_response.lower()
    user_msg = user_message.strip()
    user_lower = user_msg.lower()

    # Detect topics ONLY from the student's message
    topics = _detect_topics(user_msg)

    if topics and len(user_msg) > 15:
        # Signals from the student's message
        user_has_code = any(c in user_msg for c in _CODE_INDICATORS)
        student_explaining = len(user_msg) > 120  # Substantive explanation

        # Signals from AI response (only for upgrade decisions)
        has_positive = any(p in response_lower for p in _POSITIVE_INDICATORS)

        for topic in topics:
            if topic not in student_progress.topics:
                student_progress.topics[topic] = TopicProgress()

            tp = student_progress.topics[topic]

            # Conceptual: "low" when student asks about the topic
            if tp.conceptual == "not_assessed":
                tp.conceptual = "low"

            # Conceptual → "medium": student gives a long explanation
            # AND AI confirms it's correct
            if (tp.conceptual == "low"
                    and student_explaining
                    and has_positive):
                tp.conceptual = "medium"

            # Instruction: "low" when student writes a code-related prompt
            # (student must include code or give implementation instructions)
            if user_has_code or (len(user_msg) > 50 and any(
                w in user_lower for w in [
                    "write", "create", "implement", "calculate",
                    "compute", "parse", "read the", "build",
                ]
            )):
                if tp.instruction == "not_assessed":
                    tp.instruction = "low"
                # → "medium": AI confirms the code/instruction was correct
                if tp.instruction == "low" and has_positive and user_has_code:
                    tp.instruction = "medium"

            # Implementation: "low" only when student actually writes code
            if user_has_code:
                if tp.implementation == "not_assessed":
                    tp.implementation = "low"

            # Verification (Layer 4): student interprets results biologically
            verification_indicators = [
                "biologically", "means that", "this tells us",
                "interpretation", "the result shows", "this suggests",
                "in terms of", "the value of",
                "selective sweep", "positive selection", "purifying selection",
                "balancing selection", "neutral evolution", "neutrally evolving",
                "reduced diversity", "low diversity", "high diversity",
                "ancestral polymorphism", "population expansion", "bottleneck",
                "subgenome", "homoeolog", "halleri copy", "lyrata copy",
                "pi is", "pi =", "theta", "d_a",
                "consistent with", "expected because", "explained by",
            ]
            student_interprets = any(
                v in user_lower for v in verification_indicators
            )
            if student_interprets and len(user_msg) > 60:
                if tp.verification == "not_assessed":
                    tp.verification = "low"
                if (tp.verification == "low"
                        and student_explaining
                        and has_positive):
                    tp.verification = "medium"

            tp.last_checkpoint = _now_iso()

    # Record checkpoint questions (from AI response)
    checkpoint_indicators = [
        "can you explain", "what do you think", "what would happen",
        "predict the output", "before you run", "why does this",
        "what is the difference",
    ]
    has_checkpoint = any(ci in response_lower for ci in checkpoint_indicators)

    if has_checkpoint:
        student_progress.checkpoint_results.append({
            "timestamp": _now_iso(),
            "type": "checkpoint_posed",
            "context": user_message[:200],
        })
        if len(student_progress.checkpoint_results) > 50:
            student_progress.checkpoint_results = (
                student_progress.checkpoint_results[-50:]
            )

    progress_tracker.save(session_id, student_progress)


class TeachingChat:
    """Chat interface to Claude for BIO334 teaching.

    Manages message history, system prompt construction, and automatic
    progress updates after each exchange.

    Parameters
    ----------
    knowledge:
        The knowledge base for skill content.
    progress:
        The progress tracker for loading/saving student state.
    timetable:
        The timetable manager for schedule context.
    prompt_builder:
        The system prompt builder.
    api_key:
        Anthropic API key. If not provided, falls back to
        ``ANTHROPIC_API_KEY`` environment variable.
    proxy_url:
        Optional proxy URL. If provided, the anthropic client uses
        this as its ``base_url``.
    model:
        Model identifier. Defaults to ``claude-sonnet-4-20250514``.
    """

    def __init__(
        self,
        knowledge: KnowledgeBase,
        progress: ProgressTracker,
        timetable: TimetableManager,
        prompt_builder: SystemPromptBuilder,
        api_key: Optional[str] = None,
        proxy_url: Optional[str] = None,
        model: str = DEFAULT_MODEL,
    ) -> None:
        self._kb = knowledge
        self._progress = progress
        self._tt = timetable
        self._prompt_builder = prompt_builder
        self._model = model

        # Resolve API key
        resolved_key = api_key or os.environ.get("ANTHROPIC_API_KEY", "")

        # Build client kwargs
        self._client: object | None = None
        self._async_client: object | None = None

        if _ANTHROPIC_AVAILABLE:
            client_kwargs: dict = {}
            if resolved_key:
                client_kwargs["api_key"] = resolved_key
            if proxy_url:
                client_kwargs["base_url"] = proxy_url

            self._client = anthropic.Anthropic(**client_kwargs)
            self._async_client = anthropic.AsyncAnthropic(**client_kwargs)

        # In-memory message history per session
        self._message_history: dict[str, list[dict]] = {}

    # ------------------------------------------------------------------
    # Message history management
    # ------------------------------------------------------------------

    def _get_history(self, session_id: str) -> list[dict]:
        """Get message history for a session, creating if needed."""
        if session_id not in self._message_history:
            self._message_history[session_id] = []
        return self._message_history[session_id]

    def _append_message(
        self, session_id: str, role: str, content: str
    ) -> None:
        """Append a message to session history, enforcing max size."""
        history = self._get_history(session_id)
        history.append({"role": role, "content": content})
        # Trim to last MAX_HISTORY_MESSAGES
        if len(history) > MAX_HISTORY_MESSAGES:
            self._message_history[session_id] = history[-MAX_HISTORY_MESSAGES:]

    def _build_messages(
        self, session_id: str, user_message: str
    ) -> list[dict]:
        """Build the messages array including history and current message."""
        history = self._get_history(session_id)
        messages = list(history)  # Copy existing history
        messages.append({"role": "user", "content": user_message})
        return messages

    # ------------------------------------------------------------------
    # Async streaming interface
    # ------------------------------------------------------------------

    async def send_message(
        self, message: str, session_id: str = "default"
    ) -> AsyncIterator[str]:
        """Send a message and stream the response.

        Parameters
        ----------
        message:
            The user's message text.
        session_id:
            Session identifier for progress tracking and history.

        Yields
        ------
        str
            Text chunks of the assistant's response as they arrive.
        """
        if not _ANTHROPIC_AVAILABLE:
            yield _ERROR_UNAVAILABLE + " (anthropic package not installed)"
            return

        assert self._async_client is not None

        # Load student progress
        student_progress = self._progress.load(session_id)

        # Build system prompt
        system_prompt = self._prompt_builder.build(student_progress, message)

        # Build messages
        messages = self._build_messages(session_id, message)

        # Save user message to history
        self._append_message(session_id, "user", message)

        try:
            # Emit model metadata
            yield json.dumps({
                "type": "meta",
                "model": self._model,
                "backend": "api",
            })

            full_response: list[str] = []

            async with self._async_client.messages.stream(
                model=self._model,
                max_tokens=2048,
                system=system_prompt,
                messages=messages,
            ) as stream:
                async for text in stream.text_stream:
                    full_response.append(text)
                    yield text

            # Accumulate and save response
            response_text = "".join(full_response)
            self._append_message(session_id, "assistant", response_text)

            # Auto-update progress
            self._auto_update_progress(session_id, message, response_text)

        except Exception as exc:
            error_msg = self._handle_api_error(exc)
            yield error_msg

    # ------------------------------------------------------------------
    # Synchronous interface (for MCP / Agent SDK)
    # ------------------------------------------------------------------

    def send_message_sync(
        self, message: str, session_id: str = "default"
    ) -> str:
        """Send a message and return the full response (non-streaming).

        Parameters
        ----------
        message:
            The user's message text.
        session_id:
            Session identifier for progress tracking and history.

        Returns
        -------
        str
            The complete assistant response.
        """
        if not _ANTHROPIC_AVAILABLE:
            return _ERROR_UNAVAILABLE + " (anthropic package not installed)"

        assert self._client is not None

        # Load student progress
        student_progress = self._progress.load(session_id)

        # Build system prompt
        system_prompt = self._prompt_builder.build(student_progress, message)

        # Build messages
        messages = self._build_messages(session_id, message)

        # Save user message to history
        self._append_message(session_id, "user", message)

        try:
            response = self._client.messages.create(
                model=self._model,
                max_tokens=2048,
                system=system_prompt,
                messages=messages,
            )

            # Extract text from response
            response_text = ""
            for block in response.content:
                if hasattr(block, "text"):
                    response_text += block.text

            # Save to history
            self._append_message(session_id, "assistant", response_text)

            # Auto-update progress
            self._auto_update_progress(session_id, message, response_text)

            return response_text

        except Exception as exc:
            return self._handle_api_error(exc)

    # ------------------------------------------------------------------
    # Progress auto-update
    # ------------------------------------------------------------------

    def _auto_update_progress(
        self, session_id: str, user_message: str, ai_response: str
    ) -> None:
        """Automatically detect topics and update progress levels.

        Uses keyword matching to detect which topics are being discussed,
        and heuristics on the AI response to estimate understanding level.
        """
        try:
            _do_auto_update_progress(
                self._progress, session_id, user_message, ai_response
            )
        except Exception:
            # Progress update failures should not break the chat
            pass

    # ------------------------------------------------------------------
    # Error handling
    # ------------------------------------------------------------------

    @staticmethod
    def _handle_api_error(exc: Exception) -> str:
        """Convert API exceptions to user-friendly error messages."""
        if not _ANTHROPIC_AVAILABLE:
            return _ERROR_UNAVAILABLE

        if isinstance(exc, anthropic.APIConnectionError):
            return _ERROR_UNAVAILABLE
        if isinstance(exc, anthropic.RateLimitError):
            return _ERROR_RATE_LIMIT
        if isinstance(exc, anthropic.APIStatusError):
            return _ERROR_GENERIC
        # Unknown error — still return a friendly message
        return _ERROR_GENERIC


class ClaudeCodeChat:
    """Chat backend that uses the locally installed ``claude`` CLI.

    Instead of calling the Anthropic API directly, this spawns the
    ``claude`` CLI in print mode (``-p``) with a system prompt.
    The CLI handles its own authentication, so no API key is needed.

    Parameters
    ----------
    knowledge:
        The knowledge base for skill content.
    progress:
        The progress tracker for loading/saving student state.
    timetable:
        The timetable manager for schedule context.
    prompt_builder:
        The system prompt builder.
    model:
        Model alias for the Claude CLI (e.g. ``"sonnet"``, ``"opus"``).
        If ``None``, the CLI uses whatever the student has configured.
    """

    def __init__(
        self,
        knowledge: KnowledgeBase,
        progress: ProgressTracker,
        timetable: TimetableManager,
        prompt_builder: SystemPromptBuilder,
        model: str | None = None,
    ) -> None:
        self._kb = knowledge
        self._progress = progress
        self._tt = timetable
        self._prompt_builder = prompt_builder
        self._model = model  # None = use student's Claude Code default
        self._message_history: dict[str, list[dict]] = {}

        # Verify claude CLI is available
        self._claude_path = shutil.which("claude")
        if self._claude_path is None:
            raise RuntimeError(
                "Claude Code CLI not found. Install it first:\n"
                "  npm install -g @anthropic-ai/claude-code"
            )

    # ------------------------------------------------------------------
    # Message history (simplified — Claude CLI doesn't support multi-turn
    # natively in -p mode, so we include recent history in the prompt)
    # ------------------------------------------------------------------

    def _get_history(self, session_id: str) -> list[dict]:
        if session_id not in self._message_history:
            self._message_history[session_id] = []
        return self._message_history[session_id]

    def _append_message(self, session_id: str, role: str, content: str) -> None:
        history = self._get_history(session_id)
        history.append({"role": role, "content": content})
        if len(history) > MAX_HISTORY_MESSAGES:
            self._message_history[session_id] = history[-MAX_HISTORY_MESSAGES:]

    def _build_history_context(self, session_id: str) -> str:
        """Format recent history as part of the user message for the CLI."""
        history = self._get_history(session_id)
        if not history:
            return ""
        lines = ["<conversation_history>"]
        for msg in history[-6:]:  # Last 3 exchanges
            role = msg["role"].upper()
            lines.append(f"[{role}]: {msg['content']}")
        lines.append("</conversation_history>\n")
        return "\n".join(lines)

    # ------------------------------------------------------------------
    # Async streaming interface (compatible with TeachingChat)
    # ------------------------------------------------------------------

    async def send_message(
        self, message: str, session_id: str = "default"
    ) -> AsyncIterator[str]:
        """Send a message via claude CLI and stream the response.

        Yields JSON-encoded strings. Most are text chunks, but special
        metadata events are also emitted:

        - ``{"type": "meta", "model": "...", "backend": "claude-code"}``
          — emitted once at the start when model info is available.
        - ``{"type": "meta", "duration_ms": ..., "cost_usd": ...}``
          — emitted once when the CLI finishes.
        - Plain text strings for the actual response content.

        The SSE route in ``routes.py`` handles these appropriately.
        """
        import asyncio

        student_progress = self._progress.load(session_id)
        system_prompt = self._prompt_builder.build(student_progress, message)

        history_ctx = self._build_history_context(session_id)
        full_message = f"{history_ctx}{message}" if history_ctx else message

        self._append_message(session_id, "user", message)

        cmd = [
            self._claude_path,
            "-p",
            "--output-format", "stream-json",
            "--verbose",
            "--system-prompt", system_prompt,
            "--no-session-persistence",
            "--disallowed-tools", "Bash", "Edit", "Write", "Read",
            "Glob", "Grep", "NotebookEdit", "WebFetch", "WebSearch",
        ]
        # Only pass --model if explicitly set; otherwise use student's default
        if self._model:
            cmd.extend(["--model", self._model])

        env = dict(os.environ)
        env.pop("CLAUDECODE", None)

        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=env,
            )
            proc.stdin.write(full_message.encode("utf-8"))
            await proc.stdin.drain()
            proc.stdin.close()

            full_response: list[str] = []
            meta_sent = False

            async for line in proc.stdout:
                line_str = line.decode("utf-8", errors="replace").strip()
                if not line_str:
                    continue
                try:
                    data = json.loads(line_str)
                except json.JSONDecodeError:
                    continue

                msg_type = data.get("type", "")

                # Emit model metadata from init message
                if msg_type == "system" and not meta_sent:
                    meta_sent = True
                    yield json.dumps({
                        "type": "meta",
                        "model": data.get("model", "unknown"),
                        "backend": "claude-code",
                    })

                # Stream text content
                elif msg_type == "assistant":
                    msg = data.get("message", {})
                    for block in msg.get("content", []):
                        if block.get("type") == "text":
                            text = block["text"]
                            full_response.append(text)
                            yield text

                # Emit completion metadata
                elif msg_type == "result":
                    yield json.dumps({
                        "type": "meta",
                        "duration_ms": data.get("duration_ms", 0),
                        "cost_usd": data.get("total_cost_usd", 0),
                    })

            await proc.wait()

            response_text = "".join(full_response)
            if response_text:
                self._append_message(session_id, "assistant", response_text)
                self._auto_update_progress(session_id, message, response_text)
            elif proc.returncode != 0:
                stderr_out = await proc.stderr.read()
                error_msg = stderr_out.decode("utf-8", errors="replace").strip()
                yield f"Error from Claude Code: {error_msg[:500]}"

        except FileNotFoundError:
            yield "Error: Claude Code CLI not found. Please install it."
        except Exception as exc:
            yield f"Error: {exc}"

    # ------------------------------------------------------------------
    # Synchronous interface (for MCP)
    # ------------------------------------------------------------------

    def send_message_sync(
        self, message: str, session_id: str = "default"
    ) -> str:
        """Send a message via claude CLI and return the full response."""
        student_progress = self._progress.load(session_id)
        system_prompt = self._prompt_builder.build(student_progress, message)

        history_ctx = self._build_history_context(session_id)
        full_message = f"{history_ctx}{message}" if history_ctx else message

        self._append_message(session_id, "user", message)

        cmd = [
            self._claude_path,
            "-p",
            "--output-format", "text",
            "--system-prompt", system_prompt,
            "--no-session-persistence",
            "--disallowed-tools", "Bash", "Edit", "Write", "Read",
            "Glob", "Grep", "NotebookEdit", "WebFetch", "WebSearch",
        ]
        if self._model:
            cmd.extend(["--model", self._model])

        env = dict(os.environ)
        env.pop("CLAUDECODE", None)

        try:
            result = subprocess.run(
                cmd,
                input=full_message,
                capture_output=True,
                text=True,
                timeout=120,
                env=env,
            )
            response_text = result.stdout.strip()
            if result.returncode != 0 and not response_text:
                return f"Error from Claude Code: {result.stderr[:500]}"

            if response_text:
                self._append_message(session_id, "assistant", response_text)
                self._auto_update_progress(session_id, message, response_text)
            return response_text

        except subprocess.TimeoutExpired:
            return "Error: Claude Code response timed out (120s)."
        except FileNotFoundError:
            return "Error: Claude Code CLI not found."
        except Exception as exc:
            return f"Error: {exc}"

    # ------------------------------------------------------------------
    # Progress auto-update (shared with TeachingChat)
    # ------------------------------------------------------------------

    def _auto_update_progress(
        self, session_id: str, user_message: str, ai_response: str
    ) -> None:
        try:
            _do_auto_update_progress(
                self._progress, session_id, user_message, ai_response
            )
        except Exception:
            pass
