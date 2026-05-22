"""Timetable manager for BIO334 3-day intensive course.

Parses the timetable markdown file and provides schedule-aware context
for the teaching chain.
"""

from __future__ import annotations

import re
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Optional

from bio334_teaching.core.knowledge import KnowledgeBase

# Course dates: May 14-16, 2025
COURSE_DATES = [
    datetime(2025, 5, 14, tzinfo=timezone.utc).date(),
    datetime(2025, 5, 15, tzinfo=timezone.utc).date(),
    datetime(2025, 5, 16, tzinfo=timezone.utc).date(),
]
CLASS_START_HOUR = 9
CLASS_END_HOUR = 16

# Zurich is UTC+2 in May (CEST)
ZURICH_OFFSET = timedelta(hours=2)
ZURICH_TZ = timezone(ZURICH_OFFSET)

# Type icon mapping
TYPE_ICONS = {
    "lecture": "📖",
    "hands_on": "💻",
    "checkpoint": "✅",
    "discussion": "💬",
    "break": "☕",
    "review": "🔄",
    "demo": "🎬",
}


def _parse_type_from_icon(cell: str) -> str:
    """Extract activity type from a cell containing an icon + type name."""
    cell = cell.strip()
    # Map icon to type
    for type_name, icon in TYPE_ICONS.items():
        if icon in cell or type_name in cell:
            return type_name
    return cell


def _parse_duration(text: str) -> int:
    """Parse duration string like '20 min' to integer minutes."""
    match = re.search(r"(\d+)", text)
    return int(match.group(1)) if match else 0


def _parse_table_rows(table_text: str) -> list[dict]:
    """Parse a markdown table into a list of row dicts.

    Expects columns: Time | Duration | Type | Topic | Skill Reference | Notes
    """
    rows: list[dict] = []
    lines = table_text.strip().splitlines()

    for line in lines:
        line = line.strip()
        if not line.startswith("|"):
            continue
        cells = [c.strip() for c in line.split("|")]
        # Remove empty first/last from leading/trailing pipes
        cells = [c for c in cells if c != ""]
        if len(cells) < 5:
            continue
        # Skip header separator rows (e.g. |------|------|)
        if all(set(c) <= set("-: ") for c in cells):
            continue
        # Skip actual header row
        if cells[0].lower() in ("time", ""):
            continue

        time_str = cells[0].strip()
        duration_str = cells[1].strip() if len(cells) > 1 else ""
        type_str = cells[2].strip() if len(cells) > 2 else ""
        topic_str = cells[3].strip() if len(cells) > 3 else ""
        skill_ref = cells[4].strip() if len(cells) > 4 else ""
        notes_str = cells[5].strip() if len(cells) > 5 else ""

        # Clean up skill_ref: remove backticks, handle "—"
        skill_ref = skill_ref.replace("`", "").strip()
        if skill_ref in ("—", "-", ""):
            skill_ref = ""

        rows.append(
            {
                "time": time_str,
                "duration_min": _parse_duration(duration_str),
                "type": _parse_type_from_icon(type_str),
                "topic": topic_str,
                "skill_ref": skill_ref,
                "notes": notes_str,
            }
        )
    return rows


def _parse_timetable_md(text: str) -> list[dict]:
    """Parse the full timetable markdown into structured data.

    Each entry gets a ``day`` (1-3) and ``block_id`` field added.
    """
    entries: list[dict] = []
    current_day = 0

    # Split by day headings
    day_pattern = re.compile(r"^## Day (\d+)", re.MULTILINE)

    lines = text.splitlines()
    i = 0
    while i < len(lines):
        line = lines[i]
        day_match = day_pattern.match(line)
        if day_match:
            current_day = int(day_match.group(1))
            i += 1
            continue

        # Detect table sections (starts with | Time)
        if line.strip().startswith("| Time"):
            # Collect table lines
            table_lines: list[str] = []
            while i < len(lines) and lines[i].strip().startswith("|"):
                table_lines.append(lines[i])
                i += 1
            table_text = "\n".join(table_lines)
            rows = _parse_table_rows(table_text)
            for row in rows:
                # Build block_id from day and start time
                start_time = row["time"].split("–")[0].split("-")[0].strip()
                time_clean = start_time.replace(":", "")
                row["day"] = current_day
                row["block_id"] = f"day{current_day}_{time_clean}"
                entries.append(row)
            continue

        i += 1

    return entries


class TimetableManager:
    """Provides schedule-aware context for the BIO334 teaching chain.

    Loads and parses the ``bio334_timetable`` knowledge file. Provides
    methods to query the current block, relevant skills, and whether
    class is in session.
    """

    def __init__(self, knowledge_base: Optional[KnowledgeBase] = None) -> None:
        self._kb = knowledge_base or KnowledgeBase()
        self._entries: list[dict] | None = None

    def _ensure_loaded(self) -> None:
        if self._entries is not None:
            return
        skill = self._kb.get_skill("bio334_timetable")
        if skill is not None:
            self._entries = _parse_timetable_md(skill.content)
        else:
            self._entries = []

    def get_schedule(self) -> list[dict]:
        """Return the full parsed schedule as a list of dicts."""
        self._ensure_loaded()
        assert self._entries is not None
        return list(self._entries)

    def get_current_block(
        self, progress: object | None = None
    ) -> dict | None:
        """Determine the current timetable block.

        During class hours, returns the block matching the current time.
        Outside class hours, falls back to ``progress.current_block``
        if available.

        Parameters
        ----------
        progress:
            A ``StudentProgress`` instance (or any object with
            ``current_block`` attribute).  Used as fallback when outside
            class hours.
        """
        self._ensure_loaded()
        assert self._entries is not None

        if self.is_class_hours():
            now = datetime.now(ZURICH_TZ)
            day_index = None
            for idx, d in enumerate(COURSE_DATES):
                if now.date() == d:
                    day_index = idx + 1
                    break

            if day_index is not None:
                day_entries = [e for e in self._entries if e.get("day") == day_index]
                # Find the block that contains the current time
                current_hhmm = now.hour * 60 + now.minute
                best: dict | None = None
                for entry in day_entries:
                    start_str = entry["time"].split("–")[0].split("-")[0].strip()
                    try:
                        parts = start_str.split(":")
                        entry_hhmm = int(parts[0]) * 60 + int(parts[1])
                    except (ValueError, IndexError):
                        continue
                    if entry_hhmm <= current_hhmm:
                        best = entry
                return best

        # Outside class hours: fall back to progress.current_block
        if progress is not None:
            current_block = getattr(progress, "current_block", "")
            if current_block:
                for entry in self._entries:
                    if entry.get("block_id") == current_block:
                        return entry
        # Default: return first entry
        return self._entries[0] if self._entries else None

    def get_block_skills(self, block_id: str) -> list[str]:
        """Return skill_ref names for a given block_id."""
        self._ensure_loaded()
        assert self._entries is not None
        refs: list[str] = []
        for entry in self._entries:
            if entry.get("block_id") == block_id:
                ref = entry.get("skill_ref", "")
                if ref:
                    for r in ref.split(","):
                        r = r.strip()
                        if r and r not in refs:
                            refs.append(r)
        return refs

    def is_class_hours(self) -> bool:
        """Return True if the current time is within class hours.

        Class hours: May 14-16 2025, 09:00-16:00 Zurich time (CEST).
        """
        now = datetime.now(ZURICH_TZ)
        if now.date() not in COURSE_DATES:
            return False
        return CLASS_START_HOUR <= now.hour < CLASS_END_HOUR

    def get_context(self, progress: object | None = None) -> str:
        """Return a formatted context string for system prompt injection.

        Approximately 500 tokens describing the current schedule state.

        Parameters
        ----------
        progress:
            A ``StudentProgress`` instance for fallback block info.
        """
        self._ensure_loaded()
        assert self._entries is not None

        current = self.get_current_block(progress)
        in_class = self.is_class_hours()

        lines: list[str] = []
        lines.append("## Schedule Context")

        if in_class:
            lines.append("The student is working DURING CLASS HOURS.")
            lines.append("Follow the timetable. Stay on pace.")
        else:
            current_block_id = ""
            if progress is not None:
                current_block_id = getattr(progress, "current_block", "")
            lines.append("The student is working OUTSIDE CLASS HOURS.")
            lines.append("Let them navigate freely.")
            if current_block_id:
                lines.append(f"Their last position was: {current_block_id}.")
                lines.append("Resume from there unless they ask to go elsewhere.")

        if current:
            lines.append("")
            lines.append(f"**Current block**: {current.get('topic', 'N/A')}")
            lines.append(f"  - Type: {current.get('type', 'N/A')}")
            lines.append(f"  - Time: {current.get('time', 'N/A')}")
            lines.append(f"  - Day: {current.get('day', 'N/A')}")
            ref = current.get("skill_ref", "")
            if ref:
                lines.append(f"  - Skills: {ref}")

            # Show next 2 blocks for context
            block_id = current.get("block_id", "")
            found = False
            upcoming: list[dict] = []
            for entry in self._entries:
                if found and entry.get("type") != "break":
                    upcoming.append(entry)
                    if len(upcoming) >= 2:
                        break
                if entry.get("block_id") == block_id:
                    found = True

            if upcoming:
                lines.append("")
                lines.append("**Upcoming**:")
                for u in upcoming:
                    lines.append(
                        f"  - {u.get('time', '')}: {u.get('topic', '')} "
                        f"({u.get('type', '')})"
                    )

        return "\n".join(lines)
