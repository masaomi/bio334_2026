"""Knowledge base reader for BIO334 teaching skills.

Reads .md files with YAML frontmatter from the bundled knowledge/ directory.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


@dataclass
class KnowledgeSkill:
    """A single knowledge skill loaded from a markdown file."""

    name: str
    description: str
    version: str
    tags: list[str]
    content: str
    frontmatter: dict


def _parse_frontmatter(text: str) -> tuple[dict, str]:
    """Parse YAML frontmatter from markdown text.

    Returns (frontmatter_dict, content_without_frontmatter).
    """
    pattern = re.compile(r"\A---\s*\n(.*?\n)---\s*\n", re.DOTALL)
    match = pattern.match(text)
    if not match:
        return {}, text

    raw = match.group(1)
    content = text[match.end():]

    # Simple YAML-like parser for flat key-value frontmatter.
    # Handles: strings (quoted or unquoted), lists (inline [...]).
    fm: dict = {}
    for line in raw.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if ":" not in line:
            continue
        key, _, value = line.partition(":")
        key = key.strip()
        value = value.strip()
        # Remove surrounding quotes
        if (value.startswith('"') and value.endswith('"')) or (
            value.startswith("'") and value.endswith("'")
        ):
            value = value[1:-1]
        # Inline list: [a, b, c]
        if value.startswith("[") and value.endswith("]"):
            items = value[1:-1].split(",")
            fm[key] = [item.strip().strip("\"'") for item in items if item.strip()]
        else:
            fm[key] = value
    return fm, content


def _skill_from_text(text: str, filename: str) -> KnowledgeSkill:
    """Create a KnowledgeSkill from raw markdown text."""
    fm, content = _parse_frontmatter(text)
    name = fm.get("name", Path(filename).stem)
    description = fm.get("description", "")
    version = fm.get("version", "0.0")
    tags_raw = fm.get("tags", [])
    tags = tags_raw if isinstance(tags_raw, list) else [tags_raw]
    return KnowledgeSkill(
        name=name,
        description=description,
        version=version,
        tags=tags,
        content=content.strip(),
        frontmatter=fm,
    )


class KnowledgeBase:
    """Reads and queries bundled knowledge markdown files.

    Knowledge files live in the ``knowledge/`` directory inside the
    ``bio334_teaching`` package.  Each ``.md`` file is expected to have
    YAML frontmatter with at least a ``name`` field.
    """

    def __init__(self, knowledge_dir: Optional[Path] = None) -> None:
        if knowledge_dir is not None:
            self._dir = Path(knowledge_dir)
        else:
            # Resolve relative to this file:
            # core/knowledge.py -> bio334_teaching/ -> knowledge/
            self._dir = Path(__file__).resolve().parent.parent / "knowledge"

        self._skills: dict[str, KnowledgeSkill] = {}
        self._summaries: dict[str, KnowledgeSkill] = {}
        self._system_prompt: str | None = None
        self._loaded = False

    # ------------------------------------------------------------------
    # Internal loading
    # ------------------------------------------------------------------

    def _ensure_loaded(self) -> None:
        if self._loaded:
            return
        self._loaded = True

        if not self._dir.is_dir():
            return

        # Load top-level .md files
        for md_file in sorted(self._dir.glob("*.md")):
            text = md_file.read_text(encoding="utf-8")
            if md_file.name == "system_prompt.md":
                _, content = _parse_frontmatter(text)
                self._system_prompt = content.strip()
                continue
            skill = _skill_from_text(text, md_file.name)
            self._skills[skill.name] = skill

        # Load summaries
        summaries_dir = self._dir / "summaries"
        if summaries_dir.is_dir():
            for md_file in sorted(summaries_dir.glob("*.md")):
                text = md_file.read_text(encoding="utf-8")
                skill = _skill_from_text(text, md_file.name)
                self._summaries[skill.name] = skill

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def list_skills(self) -> list[KnowledgeSkill]:
        """Return all loaded knowledge skills."""
        self._ensure_loaded()
        return list(self._skills.values())

    def get_skill(self, name: str) -> KnowledgeSkill | None:
        """Get a full skill by name, or None if not found."""
        self._ensure_loaded()
        return self._skills.get(name)

    def get_summary(self, name: str) -> KnowledgeSkill | None:
        """Get a summary version of a skill by name."""
        self._ensure_loaded()
        return self._summaries.get(name)

    def get_system_prompt(self) -> str:
        """Return the base system prompt (L0 instruction)."""
        self._ensure_loaded()
        return self._system_prompt or ""

    def search(self, query: str) -> list[KnowledgeSkill]:
        """Simple keyword search across skill names, tags, and content.

        Returns matching skills ordered by relevance (name match first,
        then tag match, then content match).
        """
        self._ensure_loaded()
        query_lower = query.lower()
        terms = query_lower.split()

        name_matches: list[KnowledgeSkill] = []
        tag_matches: list[KnowledgeSkill] = []
        content_matches: list[KnowledgeSkill] = []

        for skill in self._skills.values():
            if any(t in skill.name.lower() for t in terms):
                name_matches.append(skill)
            elif any(t in tag.lower() for tag in skill.tags for t in terms):
                tag_matches.append(skill)
            elif any(t in skill.content.lower() for t in terms):
                content_matches.append(skill)

        return name_matches + tag_matches + content_matches

    def get_skills_for_block(
        self, block_id: str, timetable_data: list[dict]
    ) -> list[KnowledgeSkill]:
        """Return skills referenced by a timetable block.

        Parameters
        ----------
        block_id:
            A block identifier such as ``"day1_0930"`` or a time string.
        timetable_data:
            Parsed timetable entries (list of dicts with ``skill_ref`` key).

        Returns a list of matching KnowledgeSkill objects.
        """
        self._ensure_loaded()
        skill_refs: set[str] = set()
        for entry in timetable_data:
            entry_id = entry.get("block_id", "")
            if entry_id == block_id or entry.get("time", "") == block_id:
                ref = entry.get("skill_ref", "")
                if ref:
                    for r in ref.split(","):
                        r = r.strip().strip("`")
                        if r and r != "—":
                            skill_refs.add(r)

        results: list[KnowledgeSkill] = []
        for ref in skill_refs:
            skill = self._skills.get(ref)
            if skill is not None:
                results.append(skill)
        return results
