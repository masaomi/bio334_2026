"""Per-topic, 4-layer student progress tracking for BIO334.

Layers align with the 4-layer pedagogical model:
  1. conceptual      — Layer 1: Conceptual Understanding
  2. instruction     — Layer 2: Instruction (high + low level)
  3. implementation  — Layer 3: Implementation Literacy
  4. verification    — Layer 4: Result Verification (biological interpretation)

Progress data is stored as JSON files under ``~/.bio334/`` (configurable).
"""

from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

# Valid assessment levels
VALID_LEVELS = {"high", "medium", "low", "not_assessed"}

# Valid assessment dimensions
VALID_DIMENSIONS = {"conceptual", "instruction", "implementation", "verification"}

# Session ID validation pattern
SESSION_ID_PATTERN = re.compile(r"^[a-zA-Z0-9_-]{1,64}$")


def _now_iso() -> str:
    """Return current UTC time as ISO 8601 string."""
    return datetime.now(timezone.utc).isoformat()


@dataclass
class TopicProgress:
    """Progress assessment for a single topic across 4 dimensions."""

    conceptual: str = "not_assessed"
    instruction: str = "not_assessed"
    implementation: str = "not_assessed"
    verification: str = "not_assessed"
    last_checkpoint: str = ""
    notes: str = ""

    def __post_init__(self) -> None:
        for dim in VALID_DIMENSIONS:
            val = getattr(self, dim)
            if val not in VALID_LEVELS:
                raise ValueError(
                    f"Invalid level '{val}' for {dim}. Must be one of {VALID_LEVELS}"
                )


@dataclass
class StudentProgress:
    """Full progress state for a student session."""

    session_id: str
    created_at: str = ""
    last_active: str = ""
    current_day: int = 1
    current_block: str = ""
    topics: dict[str, TopicProgress] = field(default_factory=dict)
    session_summary: str = ""
    checkpoint_results: list[dict] = field(default_factory=list)
    chat_history: list[dict] = field(default_factory=list)
    save_points: list[dict] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not self.created_at:
            self.created_at = _now_iso()
        if not self.last_active:
            self.last_active = _now_iso()


def _topic_progress_from_dict(d: dict) -> TopicProgress:
    """Construct a TopicProgress from a plain dict."""
    return TopicProgress(
        conceptual=d.get("conceptual", "not_assessed"),
        instruction=d.get("instruction", "not_assessed"),
        implementation=d.get("implementation", "not_assessed"),
        verification=d.get("verification", "not_assessed"),
        last_checkpoint=d.get("last_checkpoint", ""),
        notes=d.get("notes", ""),
    )


def _student_progress_from_dict(d: dict) -> StudentProgress:
    """Construct a StudentProgress from a plain dict (e.g., loaded JSON)."""
    topics_raw = d.get("topics", {})
    topics = {k: _topic_progress_from_dict(v) for k, v in topics_raw.items()}
    return StudentProgress(
        session_id=d.get("session_id", ""),
        created_at=d.get("created_at", ""),
        last_active=d.get("last_active", ""),
        current_day=d.get("current_day", 1),
        current_block=d.get("current_block", ""),
        topics=topics,
        session_summary=d.get("session_summary", ""),
        checkpoint_results=d.get("checkpoint_results", []),
        chat_history=d.get("chat_history", []),
        save_points=d.get("save_points", []),
    )


def _validate_session_id(session_id: str) -> None:
    """Raise ValueError if session_id is invalid."""
    if not SESSION_ID_PATTERN.match(session_id):
        raise ValueError(
            f"Invalid session_id '{session_id}'. "
            "Must match ^[a-zA-Z0-9_-]{{1,64}}$"
        )


class ProgressTracker:
    """Manages per-student progress stored as JSON files.

    Parameters
    ----------
    progress_dir:
        Directory for storing progress JSON files.
        Defaults to ``~/.bio334/``.
    """

    def __init__(self, progress_dir: Optional[Path] = None) -> None:
        self._dir = Path(progress_dir) if progress_dir else Path.home() / ".bio334"

    def _path_for(self, session_id: str) -> Path:
        """Return the JSON file path for a session."""
        return self._dir / f"{session_id}.json"

    def load(self, session_id: str) -> StudentProgress:
        """Load progress for a session. Creates a new one if not found."""
        _validate_session_id(session_id)
        path = self._path_for(session_id)
        if path.exists():
            data = json.loads(path.read_text(encoding="utf-8"))
            return _student_progress_from_dict(data)
        return StudentProgress(session_id=session_id)

    def save(self, session_id: str, progress: StudentProgress) -> None:
        """Save progress to disk."""
        _validate_session_id(session_id)
        progress.last_active = _now_iso()
        self._dir.mkdir(parents=True, exist_ok=True)
        path = self._path_for(session_id)
        data = asdict(progress)
        path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")

    def update_topic(
        self,
        session_id: str,
        topic: str,
        dimension: str,
        level: str,
    ) -> None:
        """Update a single dimension of a single topic's progress.

        Parameters
        ----------
        session_id:
            Student session identifier.
        topic:
            Topic name (e.g. ``"popgen_nucleotide_diversity"``).
        dimension:
            One of ``"conceptual"``, ``"instruction"``, ``"implementation"``, ``"verification"``.
        level:
            One of ``"high"``, ``"medium"``, ``"low"``, ``"not_assessed"``.
        """
        if dimension not in VALID_DIMENSIONS:
            raise ValueError(
                f"Invalid dimension '{dimension}'. Must be one of {VALID_DIMENSIONS}"
            )
        if level not in VALID_LEVELS:
            raise ValueError(
                f"Invalid level '{level}'. Must be one of {VALID_LEVELS}"
            )

        progress = self.load(session_id)
        if topic not in progress.topics:
            progress.topics[topic] = TopicProgress()
        tp = progress.topics[topic]
        setattr(tp, dimension, level)
        tp.last_checkpoint = _now_iso()
        self.save(session_id, progress)

    def reset(self, session_id: str) -> None:
        """Reset (delete) progress for a session."""
        _validate_session_id(session_id)
        path = self._path_for(session_id)
        if path.exists():
            path.unlink()
