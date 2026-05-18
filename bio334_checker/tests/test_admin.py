"""Instructor admin: stats aggregation + basic-auth-gated routes."""

from __future__ import annotations

import base64
import io
import json
import tarfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from bio334_checker.core import admin_stats
from bio334_checker.core import exercises as ex_mod
from bio334_checker.core import grader as grader_mod
from bio334_checker.core import llm_call as llm_mod
from bio334_checker.core import submissions as sub_repo
from bio334_checker.db.connection import connect, init_db
from bio334_checker.interfaces.web.app import create_app


SAMPLE_YAML = """\
slug: ex_a
title: A
day: 1
part: 1
order_index: 1
description_md: a
rubric_md: a
expected_stdout: "a\\n"
"""


def _basic(user: str, pwd: str) -> dict:
    raw = base64.b64encode(f"{user}:{pwd}".encode("utf-8")).decode("ascii")
    return {"Authorization": f"Basic {raw}"}


@pytest.fixture()
def db(tmp_path: Path):
    p = tmp_path / "ad.db"
    init_db(p)
    conn = connect(p)
    yaml_path = tmp_path / "a.yaml"
    yaml_path.write_text(SAMPLE_YAML, encoding="utf-8")
    ex_mod.upsert_exercise(conn, ex_mod.load_yaml(yaml_path))
    yield conn
    conn.close()


def _seed_user(conn, handle: str) -> None:
    conn.execute(
        "INSERT INTO users (handle, display_name, created_at, last_seen_at) "
        "VALUES (?, ?, datetime('now'), datetime('now'))",
        (handle, f"Name-{handle}"),
    )


def _seed(conn, handle: str, *, score: int, passed: bool, status: str = "graded") -> int:
    detail = ex_mod.get_exercise_detail(conn, "ex_a")
    assert detail is not None
    res = grader_mod.GradeResult(
        sandbox_stdout="a\n", sandbox_stderr="", sandbox_rc=0,
        sandbox_truncated=False, exact_match=True, llm_score=score,
        llm_feedback_md="ok", llm_hints=[], llm_raw_response_json="{}",
        llm_pass=score >= 70, floor_ok=score >= 40, passed=passed,
        status=status, grader_version="v1", model_id="stub",
    )
    return sub_repo.insert_submission(
        conn, handle=handle, exercise=detail, source_code="print('a')", result=res
    )


# ---------------------------------------------------------------------------
# Pure stats aggregation
# ---------------------------------------------------------------------------

def test_heat_map_counts(db) -> None:
    for h in ("aaaa", "bbbb", "cccc"):
        _seed_user(db, h)
    _seed(db, "aaaa", score=85, passed=True)
    _seed(db, "bbbb", score=85, passed=True)
    _seed(db, "cccc", score=30, passed=False)
    _seed(db, "cccc", score=0, passed=False, status="failed")

    cells = admin_stats.heat_map(db)
    assert len(cells) == 1
    cell = cells[0]
    assert cell.submitters == 3
    assert cell.pass_count == 2
    assert cell.failed_count == 1
    assert cell.median_score is not None


def test_students_overview_lists_by_last_seen(db) -> None:
    _seed_user(db, "aaaa")
    _seed_user(db, "bbbb")
    _seed(db, "aaaa", score=85, passed=True)
    rows = admin_stats.students_overview(db)
    handles = [r.handle for r in rows]
    assert set(handles) == {"aaaa", "bbbb"}
    by_handle = {r.handle: r for r in rows}
    assert by_handle["aaaa"].passed == 1
    assert by_handle["bbbb"].passed == 0


def test_disagreement_log_extracts_event_detail(db) -> None:
    _seed_user(db, "aaaa")
    sid = _seed(db, "aaaa", score=20, passed=False)
    db.execute(
        "INSERT INTO events (ip, handle, event_type, detail_json, created_at) "
        "VALUES ('?', 'aaaa', 'grader_disagreement', ?, datetime('now'))",
        (json.dumps({"submission_id": sid, "kind": "match_but_grader_failed",
                     "exact_match": 1, "llm_score": 20}),),
    )
    rows = admin_stats.disagreement_log(db)
    assert len(rows) == 1
    assert rows[0].kind == "match_but_grader_failed"
    assert rows[0].submission_id == sid


def test_hint_log_extracts_level(db) -> None:
    _seed_user(db, "aaaa")
    db.execute(
        "INSERT INTO events (ip, handle, event_type, detail_json, created_at) "
        "VALUES ('?', 'aaaa', 'hint_requested', ?, datetime('now'))",
        (json.dumps({"slug": "ex_a", "level": 2}),),
    )
    rows = admin_stats.hint_log(db)
    assert len(rows) == 1
    assert rows[0].level == 2
    assert rows[0].exercise_slug == "ex_a"


# ---------------------------------------------------------------------------
# Web layer: auth + loopback
# ---------------------------------------------------------------------------

def _client(tmp_path: Path, monkeypatch, *, allow_test_host: bool = True) -> TestClient:
    monkeypatch.setenv("BIO334_INSECURE_COOKIE", "1")
    monkeypatch.setenv("BIO334_ADMIN_USER", "admin")
    monkeypatch.setenv("BIO334_ADMIN_PASS", "secret")
    db_path = tmp_path / "ad.db"
    init_db(db_path)
    yaml_path = tmp_path / "a.yaml"
    yaml_path.write_text(SAMPLE_YAML, encoding="utf-8")
    conn = connect(db_path)
    try:
        ex_mod.upsert_exercise(conn, ex_mod.load_yaml(yaml_path))
        conn.execute(
            "INSERT INTO users (handle, display_name, created_at, last_seen_at) "
            "VALUES ('aaaa', 'Anna', datetime('now'), datetime('now'))"
        )
    finally:
        conn.close()

    payload = json.dumps({"score": 85, "feedback_md": "ok"})
    monkeypatch.setattr(
        grader_mod, "llm_call",
        lambda *a, **k: llm_mod.LLMResponse(text=payload, raw_json="{}", model_id="x", backend="api"),
    )
    # TestClient leaves request.client = None; the middleware reads "" in
    # that case. Allowing "" simulates the loopback-only deployment for tests.
    allowed = ("127.0.0.1", "::1", "") if allow_test_host else ("127.0.0.1", "::1")
    app = create_app(db_path=db_path, host=None, admin_allowed_hosts=allowed)
    return TestClient(app)


def test_admin_blocked_from_non_loopback(tmp_path, monkeypatch) -> None:
    """Round-2 reminder: /admin* on non-loopback returns 403 from middleware."""
    c = _client(tmp_path, monkeypatch, allow_test_host=False)
    with c:
        r = c.get("/admin", headers=_basic("admin", "secret"))
        assert r.status_code == 403


def test_admin_requires_basic_auth(tmp_path, monkeypatch) -> None:
    c = _client(tmp_path, monkeypatch)
    with c:
        r = c.get("/admin")
        assert r.status_code == 401
        assert r.headers.get("www-authenticate", "").startswith("Basic")


def test_admin_wrong_credentials(tmp_path, monkeypatch) -> None:
    c = _client(tmp_path, monkeypatch)
    with c:
        r = c.get("/admin", headers=_basic("admin", "wrong"))
        assert r.status_code == 401


def test_admin_credentials_unconfigured(tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("BIO334_ADMIN_USER", raising=False)
    monkeypatch.delenv("BIO334_ADMIN_PASS", raising=False)
    monkeypatch.setenv("BIO334_INSECURE_COOKIE", "1")
    db_path = tmp_path / "no_creds.db"
    init_db(db_path)
    app = create_app(db_path=db_path, admin_allowed_hosts=("127.0.0.1", "::1", ""))
    with TestClient(app) as c:
        r = c.get("/admin", headers=_basic("admin", "secret"))
        assert r.status_code == 503


def test_admin_renders_with_correct_credentials(tmp_path, monkeypatch) -> None:
    c = _client(tmp_path, monkeypatch)
    with c:
        r = c.get("/admin", headers=_basic("admin", "secret"))
        assert r.status_code == 200
        assert "Heat map" in r.text
        assert "Anna" in r.text  # display_name shown to admin (R-13)
        assert "aaaa" in r.text  # handle alongside


def test_visibility_round_trip(tmp_path, monkeypatch) -> None:
    """Hide-all → student gets 404; show-all → student sees the exercise.
    Also: admin can read /admin/exercises and the checkbox form posts back."""
    c = _client(tmp_path, monkeypatch)
    with c:
        # Initial state: visible=1 (default), student-facing list shows it.
        # Register a student so we have a cookie for the student-side checks.
        r = c.post("/register", data={"display_name": "S"}, follow_redirects=False)
        assert r.status_code == 200
        assert c.cookies.get("bio334_session")

        r = c.get("/exercises")
        assert "ex_a" in r.text

        # Admin: GET /admin/exercises shows the checkbox grid.
        r = c.get("/admin/exercises", headers=_basic("admin", "secret"))
        assert r.status_code == 200
        assert "ex_a" in r.text
        assert "Visible" in r.text

        # POST preset=hide_all → student-facing list now omits it.
        r = c.post("/admin/exercises/visibility",
                   data={"preset": "hide_all"},
                   headers=_basic("admin", "secret"),
                   follow_redirects=False)
        assert r.status_code == 303
        r = c.get("/exercises")
        assert "ex_a" not in r.text
        # Detail URL becomes a 404 to avoid leaking existence.
        r = c.get("/exercises/ex_a")
        assert r.status_code == 404

        # POST checkbox form re-enabling ex_a → visible again.
        r = c.post("/admin/exercises/visibility",
                   data={"slug": "ex_a"},
                   headers=_basic("admin", "secret"),
                   follow_redirects=False)
        assert r.status_code == 303
        r = c.get("/exercises/ex_a")
        assert r.status_code == 200


def test_admin_export_returns_targz(tmp_path, monkeypatch) -> None:
    c = _client(tmp_path, monkeypatch)
    # Force the chain log somewhere we control so the tar contains it.
    log_path = tmp_path / "chain.jsonl"
    log_path.write_text('{"kind":"record","id":"x","payload":{}}\n', encoding="utf-8")
    monkeypatch.setenv("BIO334_CHAIN_LOG", str(log_path))

    with c:
        r = c.get("/admin/export", headers=_basic("admin", "secret"))
        assert r.status_code == 200
        assert r.headers["content-type"] == "application/gzip"
        with tarfile.open(fileobj=io.BytesIO(r.content), mode="r:gz") as tar:
            names = tar.getnames()
        assert any(n.endswith(".db") for n in names)
        assert any(n.endswith(".jsonl") for n in names)
