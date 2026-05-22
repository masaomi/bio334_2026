"""System prompt builder for BIO334 teaching chain.

Composes a system prompt within a 10,000 token budget by combining
base instructions, teaching guardrails, timetable context, student
state, and knowledge skills.
"""

from __future__ import annotations

from typing import Optional

from bio334_teaching.core.knowledge import KnowledgeBase, KnowledgeSkill
from bio334_teaching.core.progress import StudentProgress, TopicProgress
from bio334_teaching.core.timetable import TimetableManager

# Hard token budget (estimated at ~4 chars per token)
TOKEN_BUDGET = 10_000
CHARS_PER_TOKEN = 4

# Component token budgets (approximate)
_BUDGET_BASE = 2000
_BUDGET_ANTI_REGURGITATION = 200
_BUDGET_GUARDRAILS = 300
_BUDGET_TIMETABLE = 500
_BUDGET_STUDENT_STATE = 500
_BUDGET_PRIMARY_SKILL = 3000
_BUDGET_SECONDARY_SKILLS = 1500

ANTI_REGURGITATION_INSTRUCTION = """\
## Knowledge Usage Rules
The knowledge sections below are your REFERENCE MATERIAL. DO NOT reproduce them verbatim.
Adapt explanations to the student's demonstrated level:
- Phase 1 students: Use analogies, simple language, step-by-step guidance
- Phase 2 students: Use precise terminology, provide function signatures
- Phase 3 students: Reference only when asked, focus on verification and interpretation"""

TEACHING_GUARDRAILS = """\
## Teaching Guardrails
NEVER provide complete solutions to exercises. You may provide:
- The next single step or conceptual hint
- A skeleton with blanks to fill
- A related but different worked example
You may NOT provide:
- Complete working code for the current exercise
- Direct answers to checkpoint questions
If the student insists on getting the answer, respond: "I understand you want the answer, \
but my role is to help you understand. Let me break this down differently...\""""


class SystemPromptBuilder:
    """Builds a token-budgeted system prompt for the BIO334 teaching chain.

    Parameters
    ----------
    knowledge:
        The knowledge base containing L0/L1 skills and system prompt.
    timetable:
        The timetable manager for schedule-aware context.
    """

    def __init__(
        self,
        knowledge: KnowledgeBase,
        timetable: TimetableManager,
    ) -> None:
        self._kb = knowledge
        self._tt = timetable

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def build(self, progress: StudentProgress, user_message: str = "") -> str:
        """Compose the full system prompt within the token budget.

        Parameters
        ----------
        progress:
            Current student progress state.
        user_message:
            The latest user message, used for keyword-based skill selection.

        Returns
        -------
        str
            The assembled system prompt.
        """
        # 1. L0 base instruction
        base = self._kb.get_system_prompt()

        # 2. Anti-regurgitation instruction
        anti_regurg = ANTI_REGURGITATION_INSTRUCTION

        # 3. Teaching guardrails
        guardrails = TEACHING_GUARDRAILS

        # 4. Timetable context
        timetable_ctx = self._tt.get_context(progress)

        # 5. Student state
        student_state = self._format_student_state(progress)

        # 6. Primary L1 skill (full content)
        primary_skill = self._select_primary_skill(progress, user_message)
        primary_text = ""
        if primary_skill is not None:
            primary_text = self._format_skill_full(primary_skill)

        # 7. Secondary L1 skills (summaries only)
        exclude = primary_skill.name if primary_skill else ""
        secondary_skills = self._select_secondary_skills(
            progress, user_message, exclude
        )
        secondary_text = self._format_secondary_skills(secondary_skills)

        # Assemble components in order
        components = [
            base,
            anti_regurg,
            guardrails,
            timetable_ctx,
            student_state,
            primary_text,
            secondary_text,
        ]

        # Filter empty components and join
        assembled = "\n\n".join(c for c in components if c.strip())

        # Enforce token budget — truncate secondary first, then primary
        if self._estimate_tokens(assembled) > TOKEN_BUDGET:
            # Try without secondary skills
            components_no_secondary = [
                base,
                anti_regurg,
                guardrails,
                timetable_ctx,
                student_state,
                primary_text,
            ]
            assembled = "\n\n".join(c for c in components_no_secondary if c.strip())

            if self._estimate_tokens(assembled) > TOKEN_BUDGET:
                # Use summary for primary instead of full
                primary_summary = self._get_skill_summary(primary_skill)
                components_minimal = [
                    base,
                    anti_regurg,
                    guardrails,
                    timetable_ctx,
                    student_state,
                    primary_summary,
                ]
                assembled = "\n\n".join(
                    c for c in components_minimal if c.strip()
                )

                # Final hard truncation if still over budget
                max_chars = TOKEN_BUDGET * CHARS_PER_TOKEN
                if len(assembled) > max_chars:
                    assembled = assembled[:max_chars]

        return assembled

    # ------------------------------------------------------------------
    # Skill selection
    # ------------------------------------------------------------------

    def _select_primary_skill(
        self, progress: StudentProgress, user_message: str
    ) -> KnowledgeSkill | None:
        """Select the primary skill based on the current timetable block.

        This is deterministic: it uses the timetable block's ``skill_ref``.
        """
        block = self._tt.get_current_block(progress)
        if block is None:
            return None

        skill_ref = block.get("skill_ref", "")
        if not skill_ref:
            return None

        # Take the first skill_ref if there are multiple
        refs = [r.strip() for r in skill_ref.split(",")]
        for ref in refs:
            if ref and ref != "—":
                skill = self._kb.get_skill(ref)
                if skill is not None:
                    return skill

        return None

    def _select_secondary_skills(
        self,
        progress: StudentProgress,
        user_message: str,
        exclude: str,
    ) -> list[KnowledgeSkill]:
        """Select up to 2 secondary skills via keyword matching.

        Matches user message keywords against skill names and tags.
        Excludes the primary skill.
        """
        if not user_message.strip():
            return self._select_adjacent_skills(progress, exclude)

        terms = user_message.lower().split()
        all_skills = self._kb.list_skills()
        scored: list[tuple[int, str]] = []

        for skill in all_skills:
            if skill.name == exclude:
                continue

            score = 0
            name_lower = skill.name.lower()
            tags_lower = [t.lower() for t in skill.tags]

            for term in terms:
                if len(term) < 3:
                    continue
                if term in name_lower:
                    score += 3
                if any(term in tag for tag in tags_lower):
                    score += 2
                if term in skill.description.lower():
                    score += 1

            if score > 0:
                scored.append((score, skill.name))

        # Sort by score descending, take top 2
        scored.sort(key=lambda x: x[0], reverse=True)
        results: list[KnowledgeSkill] = []
        for _, name in scored[:2]:
            skill = self._kb.get_skill(name)
            if skill is not None:
                results.append(skill)

        # If no keyword matches, fall back to adjacent blocks
        if not results:
            return self._select_adjacent_skills(progress, exclude)

        return results

    def _select_adjacent_skills(
        self, progress: StudentProgress, exclude: str
    ) -> list[KnowledgeSkill]:
        """Select skills from adjacent timetable blocks as secondary."""
        block = self._tt.get_current_block(progress)
        if block is None:
            return []

        block_id = block.get("block_id", "")
        schedule = self._tt.get_schedule()

        # Find index of current block
        current_idx: int | None = None
        for idx, entry in enumerate(schedule):
            if entry.get("block_id") == block_id:
                current_idx = idx
                break

        if current_idx is None:
            return []

        # Look at adjacent blocks (before and after)
        adjacent_refs: list[str] = []
        for offset in [1, -1, 2, -2]:
            adj_idx = current_idx + offset
            if 0 <= adj_idx < len(schedule):
                ref = schedule[adj_idx].get("skill_ref", "")
                if ref and ref != exclude:
                    for r in ref.split(","):
                        r = r.strip()
                        if r and r != "—" and r != exclude and r not in adjacent_refs:
                            adjacent_refs.append(r)

        results: list[KnowledgeSkill] = []
        for ref in adjacent_refs[:2]:
            skill = self._kb.get_skill(ref)
            if skill is not None:
                results.append(skill)

        return results

    # ------------------------------------------------------------------
    # Formatting helpers
    # ------------------------------------------------------------------

    def _format_student_state(self, progress: StudentProgress) -> str:
        """Format student progress into a readable summary."""
        lines: list[str] = []
        lines.append("## Student State")
        lines.append(f"- Current day: {progress.current_day}")
        lines.append(f"- Current block: {progress.current_block or 'not set'}")
        lines.append(f"- Last active: {progress.last_active}")

        if progress.topics:
            lines.append("")
            lines.append("### Topic Progress")
            for topic_name, tp in progress.topics.items():
                phase = self._infer_phase(tp)
                lines.append(
                    f"- **{topic_name}**: Phase {phase} "
                    f"(conceptual={tp.conceptual}, "
                    f"instruction={tp.instruction}, "
                    f"implementation={tp.implementation}, "
                    f"verification={tp.verification})"
                )
                if tp.notes:
                    lines.append(f"  - Notes: {tp.notes}")

        if progress.checkpoint_results:
            lines.append("")
            lines.append("### Recent Checkpoints")
            # Show last 3 checkpoints
            for cp in progress.checkpoint_results[-3:]:
                topic = cp.get("topic", "unknown")
                result = cp.get("result", "unknown")
                ts = cp.get("timestamp", "")
                lines.append(f"- {topic}: {result} ({ts})")

        if progress.session_summary:
            lines.append("")
            lines.append("### Session Summary")
            lines.append(progress.session_summary)

        return "\n".join(lines)

    @staticmethod
    def _infer_phase(tp: TopicProgress) -> int:
        """Infer the scaffolding phase from topic progress levels.

        Phase 1: Default / low conceptual understanding
        Phase 2: Medium+ conceptual, still building instruction/implementation
        Phase 3: Medium+ in all four dimensions (verification at least low)
        """
        level_order = {"not_assessed": 0, "low": 1, "medium": 2, "high": 3}
        c = level_order.get(tp.conceptual, 0)
        i = level_order.get(tp.instruction, 0)
        m = level_order.get(tp.implementation, 0)
        v = level_order.get(tp.verification, 0)

        if c >= 2 and i >= 2 and m >= 2 and v >= 1:
            return 3
        if c >= 2:
            return 2
        return 1

    @staticmethod
    def _format_skill_full(skill: KnowledgeSkill) -> str:
        """Format a skill with full content for primary injection."""
        lines: list[str] = []
        lines.append(f"## Primary Skill: {skill.name}")
        if skill.description:
            lines.append(f"*{skill.description}*")
        lines.append("")
        lines.append(skill.content)
        return "\n".join(lines)

    def _format_secondary_skills(
        self, skills: list[KnowledgeSkill]
    ) -> str:
        """Format secondary skills using summaries only."""
        if not skills:
            return ""

        lines: list[str] = []
        lines.append("## Secondary Skills (Reference)")
        for skill in skills:
            summary = self._get_skill_summary_text(skill)
            lines.append(f"\n### {skill.name}")
            if skill.description:
                lines.append(f"*{skill.description}*")
            lines.append(summary)

        return "\n".join(lines)

    def _get_skill_summary_text(self, skill: KnowledgeSkill) -> str:
        """Get the summary text for a skill, falling back to truncation."""
        summary_skill = self._kb.get_summary(skill.name)
        if summary_skill is not None:
            return summary_skill.content

        # Fallback: truncate full content to ~500 tokens
        max_chars = 500 * CHARS_PER_TOKEN
        content = skill.content
        if len(content) > max_chars:
            content = content[:max_chars] + "\n\n[... truncated]"
        return content

    def _get_skill_summary(
        self, skill: KnowledgeSkill | None
    ) -> str:
        """Get a formatted summary version of the primary skill."""
        if skill is None:
            return ""

        summary_text = self._get_skill_summary_text(skill)
        lines: list[str] = []
        lines.append(f"## Primary Skill (Summary): {skill.name}")
        if skill.description:
            lines.append(f"*{skill.description}*")
        lines.append("")
        lines.append(summary_text)
        return "\n".join(lines)

    # ------------------------------------------------------------------
    # Token estimation
    # ------------------------------------------------------------------

    @staticmethod
    def _estimate_tokens(text: str) -> int:
        """Rough token estimate: ~4 characters per token."""
        return len(text) // CHARS_PER_TOKEN
