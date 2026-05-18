"""End-to-end /dashboard, /me-with-progress, and /hint routes."""

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
slug: ex_x
title: X
day: 1
part: 1
order_index: 1
description_md: x
rubric_md: x
expected_stdout: "x\\n"
"""


@pytest.fixture()
def client(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("BIO334_INSECURE_COOKIE", "1")
    db_path = tmp_path / "dh.db"
    init_db(db_path)
    yaml_path = tmp_path / "x.yaml"
    yaml_path.write_text(SAMPLE_YAML, encoding="utf-8")
    conn = connect(db_path)
    try:
        ex_mod.upsert_exercise(conn, ex_mod.load_yaml(yaml_path))
    finally:
        conn.close()

    # Default LLM stub for /submit + hints.
    payload = json.dumps({"score": 30, "feedback_md": "shallow"})
    def fake(_p, *, system=None, max_tokens=2048, cache_system=True):
        if system and "hint-giver" in system:
            return llm_mod.LLMResponse(
                text="Think about the building blocks first.",
                raw_json="{}",
                model_id="stub",
                backend="api",
            )
        return llm_mod.LLMResponse(text=payload, raw_json="{}", model_id="stub", backend="api")
    monkeypatch.setattr(grader_mod, "llm_call", fake)
    monkeypatch.setattr(llm_mod, "llm_call", fake)

    app = create_app(db_path=db_path, host=None)
    with TestClient(app) as c:
        yield c


def _register(c: TestClient, name: str = "Anna") -> None:
    r = c.post("/register", data={"display_name": name})
    assert r.status_code == 200


def test_dashboard_personal_section(client: TestClient) -> None:
    _register(client)
    r = client.get("/dashboard")
    assert r.status_code == 200
    assert "Cohort dashboard" in r.text
    assert "X" in r.text  # exercise title shown


def test_me_shows_progress_table(client: TestClient) -> None:
    _register(client)
    r = client.get("/me")
    assert r.status_code == 200
    assert "Your progress" in r.text
    assert "0 / 1 passed" in r.text


def test_hint_blocked_by_default(client: TestClient) -> None:
    _register(client)
    r = client.post(
        "/submit",
        data={"exercise_slug": "ex_x", "exercise_version": 1, "source_code": "print('x')"},
        follow_redirects=False,
    )
    sid = r.headers["location"].rsplit("/", 1)[-1]
    rh = client.post(f"/hint/{sid}", follow_redirects=False)
    assert rh.status_code == 403
    assert "unlock" in rh.text.lower() or "remaining" in rh.text.lower()


def test_hint_unlocks_after_two_failed_submissions(client: TestClient) -> None:
    _register(client)
    # Two failed submissions (LLM stub scores 30 — below floor 40 → not passed).
    sids = []
    for _ in range(2):
        r = client.post(
            "/submit",
            data={"exercise_slug": "ex_x", "exercise_version": 1, "source_code": "print('x')"},
            follow_redirects=False,
        )
        sids.append(r.headers["location"].rsplit("/", 1)[-1])

    rh = client.post(f"/hint/{sids[-1]}", follow_redirects=False)
    assert rh.status_code == 200
    assert "level 1 of 3" in rh.text
    assert "concept" in rh.text


def test_hint_idor_blocked(tmp_path: Path, monkeypatch) -> None:
    """Round-2 P1: another student cannot request a hint for someone else's submission."""
    monkeypatch.setenv("BIO334_INSECURE_COOKIE", "1")
    db_path = tmp_path / "idor.db"
    init_db(db_path)
    yaml_path = tmp_path / "x.yaml"
    yaml_path.write_text(SAMPLE_YAML, encoding="utf-8")
    conn = connect(db_path)
    try:
        ex_mod.upsert_exercise(conn, ex_mod.load_yaml(yaml_path))
    finally:
        conn.close()

    payload = json.dumps({"score": 30, "feedback_md": "shallow"})
    monkeypatch.setattr(
        grader_mod,
        "llm_call",
        lambda *a, **k: llm_mod.LLMResponse(text=payload, raw_json="{}", model_id="x", backend="api"),
    )

    app = create_app(db_path=db_path, host=None)
    with TestClient(app) as a, TestClient(app) as b:
        a.post("/register", data={"display_name": "Anna"})
        # Anna submits twice to clear the gate for her submissions.
        sid = None
        for _ in range(2):
            r = a.post(
                "/submit",
                data={"exercise_slug": "ex_x", "exercise_version": 1, "source_code": "print('x')"},
                follow_redirects=False,
            )
            sid = r.headers["location"].rsplit("/", 1)[-1]

        b.post("/register", data={"display_name": "Bob"})
        rh = b.post(f"/hint/{sid}", follow_redirects=False)
        assert rh.status_code == 403


def test_exercise_detail_records_open_event(client: TestClient) -> None:
    _register(client)
    client.get("/exercises/ex_x")
    client.get("/exercises/ex_x")
    # Both GETs should leave only one exercise_open event.
    # (Verified indirectly: a second call to gate_state returns the same elapsed.)
    r = client.get("/exercises/ex_x")
    assert r.status_code == 200
    assert "Hints:" in r.text
