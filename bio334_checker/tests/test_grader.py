"""Two-stage grader behavior with a stubbed LLM backend.

The grader's LLM call goes through ``bio334_checker.core.llm_call.llm_call``,
which we monkeypatch per-test to return a controlled :class:`LLMResponse`
or raise :class:`LLMError`. Sandbox runs for real (it is stdlib-only and
fast).
"""

from __future__ import annotations

import json

import pytest

from bio334_checker.core import grader as grader_mod
from bio334_checker.core import llm_call as llm_mod
from bio334_checker.core.exercises import ExerciseDetail


def _ex(
    *,
    expected: str | None = "hello\n",
    pass_th: int = 70,
    floor: int = 40,
    rubric: str = "Score 100 if prints hello.",
    timeout_s: int = 10,
    allow_nonzero_rc: bool = False,
) -> ExerciseDetail:
    return ExerciseDetail(
        slug="t",
        title="t",
        day=1,
        part=1,
        order_index=1,
        version=1,
        description_md="d",
        rubric_md=rubric,
        expected_stdout=expected,
        argv=[],
        files_provided=[],
        max_score=100,
        pass_threshold=pass_th,
        llm_floor=floor,
        allow_nonzero_rc=allow_nonzero_rc,
        timeout_s=timeout_s,
        source_gist_url=None,
    )


def _stub_llm(monkeypatch, *, score: int, feedback: str = "ok", model: str = "stub") -> None:
    payload = json.dumps({"score": score, "feedback_md": feedback, "hints": []})

    def fake(_prompt: str, *, system=None, max_tokens=2048, cache_system=True) -> llm_mod.LLMResponse:
        return llm_mod.LLMResponse(
            text=payload, raw_json="{}", model_id=model, backend="api"
        )

    monkeypatch.setattr(grader_mod, "llm_call", fake)


def _stub_llm_error(monkeypatch, *, transient: bool) -> None:
    def fake(*_a, **_k):
        raise llm_mod.LLMError("boom", transient=transient)

    monkeypatch.setattr(grader_mod, "llm_call", fake)


def _stub_llm_returns_garbage(monkeypatch) -> None:
    def fake(*_a, **_k):
        return llm_mod.LLMResponse(text="not json", raw_json="{}", model_id="x", backend="api")

    monkeypatch.setattr(grader_mod, "llm_call", fake)


# ---------------------------------------------------------------------------
# AND-logic invariant
# ---------------------------------------------------------------------------

def test_passes_when_both_match_and_llm_high(monkeypatch) -> None:
    _stub_llm(monkeypatch, score=90)
    r = grader_mod.grade("print('hello')", _ex())
    assert r.status == "graded"
    assert r.exact_match is True
    assert r.llm_score == 90
    assert r.passed is True


def test_fails_when_match_but_llm_below_floor(monkeypatch) -> None:
    """Output-only fakery: stdout matches but rubric assigns a low score."""
    _stub_llm(monkeypatch, score=20)
    r = grader_mod.grade("print('hello')", _ex(floor=40))
    assert r.exact_match is True
    assert r.llm_score == 20
    assert r.floor_ok is False
    assert r.passed is False


def test_fails_when_llm_above_floor_but_below_threshold(monkeypatch) -> None:
    _stub_llm(monkeypatch, score=55)
    r = grader_mod.grade("print('hello')", _ex(pass_th=70, floor=40))
    assert r.floor_ok is True
    assert r.llm_pass is False
    assert r.passed is False


def test_match_alone_never_passes(monkeypatch) -> None:
    """v0.3 R-1 / I-GRADE-1: exact_match alone must not pass."""
    _stub_llm(monkeypatch, score=39)
    r = grader_mod.grade("print('hello')", _ex(floor=40, pass_th=70))
    assert r.exact_match is True
    assert r.passed is False


def test_normalize_trims_trailing_whitespace(monkeypatch) -> None:
    _stub_llm(monkeypatch, score=80)
    # Student adds trailing spaces; the normalizer should still match.
    r = grader_mod.grade("print('hello   ')", _ex())
    assert r.exact_match is True


# ---------------------------------------------------------------------------
# Sandbox early-reject path
# ---------------------------------------------------------------------------

def test_nonzero_rc_skips_llm(monkeypatch) -> None:
    called = {"n": 0}

    def fake(*_a, **_k):
        called["n"] += 1
        return llm_mod.LLMResponse(text="{}", raw_json="{}", model_id="x", backend="api")

    monkeypatch.setattr(grader_mod, "llm_call", fake)

    r = grader_mod.grade("import sys; sys.exit(1)", _ex())
    assert called["n"] == 0
    assert r.passed is False
    assert r.status == "graded"
    assert r.llm_score is None


def test_allow_nonzero_rc_proceeds_to_llm(monkeypatch) -> None:
    _stub_llm(monkeypatch, score=80)
    r = grader_mod.grade(
        "import sys; print('h'); sys.exit(3)",
        _ex(expected=None, allow_nonzero_rc=True),
    )
    assert r.llm_score == 80
    assert r.passed is True


# ---------------------------------------------------------------------------
# Degraded mode
# ---------------------------------------------------------------------------

def test_transient_llm_error_marks_pending(monkeypatch) -> None:
    _stub_llm_error(monkeypatch, transient=True)
    r = grader_mod.grade("print('hello')", _ex())
    assert r.status == "pending"
    assert r.passed is False
    assert r.llm_score is None


def test_permanent_llm_error_marks_failed(monkeypatch) -> None:
    _stub_llm_error(monkeypatch, transient=False)
    r = grader_mod.grade("print('hello')", _ex())
    assert r.status == "failed"
    assert r.passed is False


def test_unparseable_llm_response_falls_back_to_zero(monkeypatch) -> None:
    _stub_llm_returns_garbage(monkeypatch)
    r = grader_mod.grade("print('hello')", _ex())
    assert r.status == "graded"
    assert r.llm_score == 0
    assert r.passed is False


# ---------------------------------------------------------------------------
# Disagreement classification
# ---------------------------------------------------------------------------

def test_files_provided_symlinked_into_sandbox(tmp_path, monkeypatch) -> None:
    """Regression: when an exercise has files_provided, the grader resolves
    BIO334_EXERCISE_FILES_DIR/<slug>/ and hands the directory to the sandbox
    so the student code can open files referenced from sys.argv.
    """
    files_root = tmp_path / "exfiles"
    (files_root / "test_slug").mkdir(parents=True)
    (files_root / "test_slug" / "input.fa").write_text(">a\nATGC\n", encoding="utf-8")
    monkeypatch.setenv("BIO334_EXERCISE_FILES_DIR", str(files_root))

    _stub_llm(monkeypatch, score=90)
    ex = grader_mod.ExerciseDetail.__bases__  # ensure import works
    from bio334_checker.core.exercises import ExerciseDetail
    detail = ExerciseDetail(
        slug="test_slug", title="t", day=2, part=3, order_index=1, version=1,
        description_md="d", rubric_md="r",
        expected_stdout="ATGC\n", argv=["input.fa"], files_provided=["input.fa"],
        max_score=100, pass_threshold=70, llm_floor=40,
        allow_nonzero_rc=False, timeout_s=10, source_gist_url=None,
    )
    src = """\
import sys
with open(sys.argv[1]) as f:
    for line in f:
        if not line.startswith('>'):
            print(line.rstrip())
"""
    result = grader_mod.grade(src, detail)
    assert result.status == "graded"
    assert result.sandbox_rc == 0
    assert result.exact_match is True


def test_files_provided_missing_dir_falls_back_to_no_data(tmp_path, monkeypatch) -> None:
    """If BIO334_EXERCISE_FILES_DIR/<slug>/ doesn't exist, grade proceeds
    without provisioning. The student code will hit FileNotFoundError on
    sys.argv[1] and the sandbox stage rejects with rc != 0.
    """
    monkeypatch.setenv("BIO334_EXERCISE_FILES_DIR", str(tmp_path / "nonexistent"))
    _stub_llm(monkeypatch, score=90)
    from bio334_checker.core.exercises import ExerciseDetail
    detail = ExerciseDetail(
        slug="missing_slug", title="t", day=2, part=3, order_index=1, version=1,
        description_md="d", rubric_md="r",
        expected_stdout=None, argv=["input.fa"], files_provided=["input.fa"],
        max_score=100, pass_threshold=70, llm_floor=40,
        allow_nonzero_rc=False, timeout_s=10, source_gist_url=None,
    )
    result = grader_mod.grade("open(__import__('sys').argv[1])", detail)
    assert result.status == "graded"
    assert result.sandbox_rc != 0
    assert result.passed is False


def test_disagreement_kind_match_no_llm() -> None:
    assert grader_mod.disagreement_kind(exact_match=True, llm_pass=False) == \
        "match_but_grader_failed"
    assert grader_mod.disagreement_kind(exact_match=False, llm_pass=True) == \
        "grader_passed_but_no_match"
    assert grader_mod.disagreement_kind(exact_match=True, llm_pass=True) is None
    assert grader_mod.disagreement_kind(exact_match=False, llm_pass=False) is None
    assert grader_mod.disagreement_kind(exact_match=True, llm_pass=None) is None
