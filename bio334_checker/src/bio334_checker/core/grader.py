"""Two-stage grader: sandbox + LLM rubric, AND-logic with floor.

Per ARCHITECTURE.md §6.1 (v0.3 R-1):

    passed = rc_ok AND llm_score >= pass_threshold AND llm_score >= llm_floor

Exact-match alone never passes — output-only fakery (e.g.
``print("<expected>")`` with no real algorithmic content) is blocked
because the LLM rubric can score it below the floor.

Disagreement (``exact_match XOR llm_pass``) is surfaced verbatim by the
caller (§6.2 / I-GRADE-3); the grader returns the raw stage results and
lets the route layer render the disagreement banner.

Degraded mode (§6.3): on a transient LLM failure the result has
``status='pending'`` and the route persists it as such; a drain task
retries later. On a permanent LLM failure (or final retry exhaustion)
the result has ``status='failed'``.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from bio334_checker.core import prompt as prompt_mod
from bio334_checker.core.exercises import ExerciseDetail
from bio334_checker.core.llm_call import LLMError, LLMResponse, llm_call
from bio334_checker.core.prompt import (
    GRADER_VERSION,
    GraderJudgement,
    GraderJudgementError,
)
from bio334_checker.core.sandbox import ExecutionResult, PythonSandbox


# Where per-exercise input files live. The convention is
# ``{EXERCISE_FILES_ROOT}/{slug}/<filename>``. The sandbox symlinks
# every file under that directory into the per-submission temp dir.
EXERCISE_FILES_ROOT_ENV = "BIO334_EXERCISE_FILES_DIR"
DEFAULT_EXERCISE_FILES_ROOT = "data/exercise_files"


def _exercise_data_dir(exercise: ExerciseDetail) -> Optional[Path]:
    """Resolve the per-exercise data directory, or None if not provided."""
    if not exercise.files_provided:
        return None
    root = Path(os.getenv(EXERCISE_FILES_ROOT_ENV, DEFAULT_EXERCISE_FILES_ROOT))
    candidate = root / exercise.slug
    return candidate if candidate.is_dir() else None


@dataclass
class GradeResult:
    # sandbox stage
    sandbox_stdout: str
    sandbox_stderr: str
    sandbox_rc: Optional[int]
    sandbox_truncated: bool
    exact_match: bool

    # LLM stage (None when sandbox fails early or LLM is unreachable)
    llm_score: Optional[int]
    llm_feedback_md: Optional[str]
    llm_hints: list[str]
    llm_raw_response_json: Optional[str]
    llm_pass: Optional[bool]
    floor_ok: Optional[bool]

    # verdict
    passed: bool
    status: str  # 'graded' | 'pending' | 'failed'
    grader_version: str
    model_id: Optional[str]


def grade(
    source_code: str,
    exercise: ExerciseDetail,
    *,
    sandbox: Optional[PythonSandbox] = None,
) -> GradeResult:
    """Run sandbox + LLM rubric and return the merged verdict."""
    sb = sandbox or PythonSandbox(timeout=exercise.timeout_s)
    data_dir = _exercise_data_dir(exercise)
    exec_result: ExecutionResult = sb.execute(
        source_code,
        args=list(exercise.argv) or None,
        data_dir=data_dir,
    )

    exact_match = (
        exercise.expected_stdout is not None
        and _normalize(exec_result.stdout) == _normalize(exercise.expected_stdout)
    )
    rc_ok = (exec_result.return_code == 0) or bool(exercise.allow_nonzero_rc)

    # Stage-1 reject: code did not execute cleanly, no LLM call.
    if not rc_ok:
        return GradeResult(
            sandbox_stdout=exec_result.stdout,
            sandbox_stderr=exec_result.stderr,
            sandbox_rc=exec_result.return_code,
            sandbox_truncated=exec_result.truncated,
            exact_match=exact_match,
            llm_score=None,
            llm_feedback_md=(
                "Your program did not execute cleanly. "
                "Read the error message below and try again.\n\n"
                f"```\n{_excerpt(exec_result.stderr)}\n```"
            ),
            llm_hints=[],
            llm_raw_response_json=None,
            llm_pass=None,
            floor_ok=None,
            passed=False,
            status="graded",
            grader_version=GRADER_VERSION,
            model_id=None,
        )

    # Stage 2: LLM rubric.
    p = prompt_mod.build_grader_prompt(
        rubric_md=exercise.rubric_md,
        expected_stdout=exercise.expected_stdout,
        sandbox_stdout=exec_result.stdout,
        sandbox_stderr=exec_result.stderr,
        return_code=exec_result.return_code,
        student_code=source_code,
    )

    try:
        resp: LLMResponse = llm_call(p.user, system=p.system)
    except LLMError as e:
        # Degraded mode: return pending. The drain task will retry; if it
        # exhausts retries the route layer flips status to 'failed'.
        return GradeResult(
            sandbox_stdout=exec_result.stdout,
            sandbox_stderr=exec_result.stderr,
            sandbox_rc=exec_result.return_code,
            sandbox_truncated=exec_result.truncated,
            exact_match=exact_match,
            llm_score=None,
            llm_feedback_md=None,
            llm_hints=[],
            llm_raw_response_json=None,
            llm_pass=None,
            floor_ok=None,
            passed=False,
            status="pending" if e.transient else "failed",
            grader_version=GRADER_VERSION,
            model_id=None,
        )

    try:
        judgement: GraderJudgement = prompt_mod.parse_grader_response(resp.text)
    except GraderJudgementError:
        # The LLM responded but produced unparseable output. Treat as graded
        # with score 0 so the student gets feedback rather than a stuck
        # 'pending' state. The raw response is persisted for audit.
        judgement = GraderJudgement(
            score=0,
            feedback_md=(
                "The grader returned a response that could not be parsed. "
                "This is likely a transient grader-side issue; please resubmit. "
                "(Your code itself was not at fault.)"
            ),
            hints=[],
        )

    llm_pass = judgement.score >= exercise.pass_threshold
    floor_ok = judgement.score >= exercise.llm_floor
    passed = rc_ok and llm_pass and floor_ok

    return GradeResult(
        sandbox_stdout=exec_result.stdout,
        sandbox_stderr=exec_result.stderr,
        sandbox_rc=exec_result.return_code,
        sandbox_truncated=exec_result.truncated,
        exact_match=exact_match,
        llm_score=judgement.score,
        llm_feedback_md=judgement.feedback_md,
        llm_hints=judgement.hints,
        llm_raw_response_json=resp.raw_json,
        llm_pass=llm_pass,
        floor_ok=floor_ok,
        passed=passed,
        status="graded",
        grader_version=GRADER_VERSION,
        model_id=resp.model_id,
    )


def disagreement_kind(
    *, exact_match: bool, llm_pass: Optional[bool]
) -> Optional[str]:
    """Classify §6.2 disagreement, or None if there is none."""
    if llm_pass is None:
        return None
    if exact_match and not llm_pass:
        return "match_but_grader_failed"
    if (not exact_match) and llm_pass:
        return "grader_passed_but_no_match"
    return None


# ----------------------------------------------------------------------------
# helpers
# ----------------------------------------------------------------------------

def _normalize(s: str) -> str:
    """Trim trailing whitespace per line + overall trailing newlines."""
    return "\n".join(line.rstrip() for line in s.splitlines()).rstrip()


def _excerpt(text: str, limit: int = 1200) -> str:
    if len(text) <= limit:
        return text
    return text[:limit] + f"\n... [truncated; original {len(text)} bytes]"
