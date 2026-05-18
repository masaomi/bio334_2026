"""End-to-end /submit + /submissions/{id} via TestClient."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from bio334_checker.core import exercises as ex_mod
from bio334_checker.core import grader as grader_mod
from bio334_checker.core import llm_call as llm_mod
from bio334_checker.db.connection import connect, init_db
from bio334_checker.interfaces.web.app import create_app


SAMPLE_YAML = """\
slug: ex_hello
title: Hello
day: 1
part: 1
order_index: 1
description_md: |
  Print hello.
rubric_md: |
  100 if prints hello.
expected_stdout: "hello\\n"
"""


@pytest.fixture()
def client(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("BIO334_INSECURE_COOKIE", "1")
    db_path = tmp_path / "submit.db"
    init_db(db_path)

    yaml_path = tmp_path / "ex.yaml"
    yaml_path.write_text(SAMPLE_YAML, encoding="utf-8")
    conn = connect(db_path)
    try:
        ex_mod.upsert_exercise(conn, ex_mod.load_yaml(yaml_path))
    finally:
        conn.close()

    # Default LLM stub: score 88, feedback "ok".
    payload = json.dumps({"score": 88, "feedback_md": "ok", "hints": []})
    def fake(_p, *, system=None, max_tokens=2048, cache_system=True):
        return llm_mod.LLMResponse(text=payload, raw_json="{}", model_id="stub", backend="api")
    monkeypatch.setattr(grader_mod, "llm_call", fake)

    app = create_app(db_path=db_path, host=None)
    with TestClient(app) as c:
        yield c


def _register(client: TestClient) -> None:
    r = client.post("/register", data={"display_name": "Anna"})
    assert r.status_code == 200


def test_submit_passes_redirect_and_result_page(client: TestClient) -> None:
    _register(client)
    r = client.post(
        "/submit",
        data={
            "exercise_slug": "ex_hello",
            "exercise_version": 1,
            "source_code": "print('hello')",
        },
        follow_redirects=False,
    )
    assert r.status_code in (302, 303)
    location = r.headers["location"]
    assert location.startswith("/submissions/")

    r2 = client.get(location)
    assert r2.status_code == 200
    assert "PASSED" in r2.text
    assert "may be wrong" in r2.text  # provisional banner (R-11 wording)


def test_submit_requires_auth(client: TestClient) -> None:
    r = client.post(
        "/submit",
        data={
            "exercise_slug": "ex_hello",
            "exercise_version": 1,
            "source_code": "print('hello')",
        },
    )
    assert r.status_code == 401


def test_submission_owner_only(tmp_path: Path, monkeypatch) -> None:
    """A different student cannot view another's submission (I-PRIV-1)."""
    monkeypatch.setenv("BIO334_INSECURE_COOKIE", "1")
    db_path = tmp_path / "owner.db"
    init_db(db_path)
    yaml_path = tmp_path / "ex.yaml"
    yaml_path.write_text(SAMPLE_YAML, encoding="utf-8")
    conn = connect(db_path)
    try:
        ex_mod.upsert_exercise(conn, ex_mod.load_yaml(yaml_path))
    finally:
        conn.close()

    payload = json.dumps({"score": 88, "feedback_md": "ok"})
    monkeypatch.setattr(
        grader_mod,
        "llm_call",
        lambda *a, **k: llm_mod.LLMResponse(text=payload, raw_json="{}", model_id="x", backend="api"),
    )
    app = create_app(db_path=db_path, host=None)
    with TestClient(app) as c1, TestClient(app) as c2:
        c1.post("/register", data={"display_name": "Anna"})
        r = c1.post(
            "/submit",
            data={"exercise_slug": "ex_hello", "exercise_version": 1, "source_code": "print('hello')"},
            follow_redirects=False,
        )
        sid = r.headers["location"].rsplit("/", 1)[-1]

        c2.post("/register", data={"display_name": "Bob"})
        r2 = c2.get(f"/submissions/{sid}")
        assert r2.status_code == 403


def test_submit_pending_when_llm_transient(tmp_path: Path, monkeypatch) -> None:
    """Transient LLM failure -> status='pending', UI shows queued banner."""
    monkeypatch.setenv("BIO334_INSECURE_COOKIE", "1")
    db_path = tmp_path / "pending.db"
    init_db(db_path)
    yaml_path = tmp_path / "ex.yaml"
    yaml_path.write_text(SAMPLE_YAML, encoding="utf-8")
    conn = connect(db_path)
    try:
        ex_mod.upsert_exercise(conn, ex_mod.load_yaml(yaml_path))
    finally:
        conn.close()

    def boom(*a, **k):
        raise llm_mod.LLMError("api down", transient=True)

    monkeypatch.setattr(grader_mod, "llm_call", boom)
    app = create_app(db_path=db_path, host=None)
    with TestClient(app) as c:
        c.post("/register", data={"display_name": "Carol"})
        r = c.post(
            "/submit",
            data={"exercise_slug": "ex_hello", "exercise_version": 1, "source_code": "print('hello')"},
            follow_redirects=False,
        )
        loc = r.headers["location"]
        rr = c.get(loc)
        assert rr.status_code == 200
        assert "grading queued" in rr.text.lower()


def test_submit_unknown_slug_404(client: TestClient) -> None:
    _register(client)
    r = client.post(
        "/submit",
        data={"exercise_slug": "no_such", "exercise_version": 1, "source_code": "print('x')"},
    )
    assert r.status_code == 404


def test_no_disagreement_when_expected_stdout_is_null(tmp_path: Path, monkeypatch) -> None:
    """Regression: dry-run on 2026-05-11 found that creative-task exercises
    (expected_stdout=null) were getting the disagreement banner on every
    passing submission, because exact_match is False by code when there's
    no canonical answer. The route layer now suppresses the banner.
    """
    monkeypatch.setenv("BIO334_INSECURE_COOKIE", "1")
    db_path = tmp_path / "no_canon.db"
    init_db(db_path)
    yaml_path = tmp_path / "ex.yaml"
    yaml_path.write_text(
        "slug: ex_creative\ntitle: C\nday: 1\npart: 1\norder_index: 1\n"
        "description_md: x\nrubric_md: x\n",
        encoding="utf-8",
    )
    conn = connect(db_path)
    try:
        ex_mod.upsert_exercise(conn, ex_mod.load_yaml(yaml_path))
    finally:
        conn.close()

    payload = json.dumps({"score": 90, "feedback_md": "ok"})
    monkeypatch.setattr(
        grader_mod, "llm_call",
        lambda *a, **k: llm_mod.LLMResponse(text=payload, raw_json="{}", model_id="x", backend="api"),
    )
    app = create_app(db_path=db_path, host=None)
    with TestClient(app) as c:
        c.post("/register", data={"display_name": "Anna"})
        r = c.post(
            "/submit",
            data={"exercise_slug": "ex_creative", "exercise_version": 1, "source_code": "print('anything')"},
            follow_redirects=False,
        )
        loc = r.headers["location"]
        rr = c.get(loc)
        assert rr.status_code == 200
        # Provisional banner present, disagreement banner NOT present.
        assert "may be wrong" in rr.text
        assert "differs from the canonical answer" not in rr.text
        assert "Grader disagreement" not in rr.text

    # And: no grader_disagreement event was logged.
    conn = connect(db_path)
    try:
        rows = conn.execute(
            "SELECT COUNT(*) AS c FROM events WHERE event_type='grader_disagreement'"
        ).fetchone()
    finally:
        conn.close()
    assert rows["c"] == 0


def test_submit_logs_disagreement(tmp_path: Path, monkeypatch) -> None:
    """When match==True but llm_pass==False, an event is logged."""
    monkeypatch.setenv("BIO334_INSECURE_COOKIE", "1")
    db_path = tmp_path / "dis.db"
    init_db(db_path)
    yaml_path = tmp_path / "ex.yaml"
    yaml_path.write_text(SAMPLE_YAML, encoding="utf-8")
    conn = connect(db_path)
    try:
        ex_mod.upsert_exercise(conn, ex_mod.load_yaml(yaml_path))
    finally:
        conn.close()

    # Match (output is "hello") but LLM scores below threshold AND below floor.
    payload = json.dumps({"score": 30, "feedback_md": "shallow"})
    monkeypatch.setattr(
        grader_mod,
        "llm_call",
        lambda *a, **k: llm_mod.LLMResponse(text=payload, raw_json="{}", model_id="x", backend="api"),
    )
    app = create_app(db_path=db_path, host=None)
    with TestClient(app) as c:
        c.post("/register", data={"display_name": "Dave"})
        c.post(
            "/submit",
            data={"exercise_slug": "ex_hello", "exercise_version": 1, "source_code": "print('hello')"},
            follow_redirects=False,
        )

    conn2 = connect(db_path)
    try:
        ev = conn2.execute(
            "SELECT event_type FROM events WHERE event_type='grader_disagreement'"
        ).fetchall()
    finally:
        conn2.close()
    assert len(ev) == 1
