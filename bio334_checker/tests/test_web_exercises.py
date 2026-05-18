"""End-to-end exercise list / detail routes."""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from bio334_checker.core import exercises as ex_mod
from bio334_checker.db.connection import connect, init_db
from bio334_checker.interfaces.web.app import create_app


SAMPLE_YAML = """\
slug: day1_p1_hello
title: Hello world
day: 1
part: 1
order_index: 1
description_md: |
  Print hello.
rubric_md: |
  Score 100 if prints "hello".
expected_stdout: "hello\\n"
"""


@pytest.fixture()
def client(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("BIO334_INSECURE_COOKIE", "1")
    db_path = tmp_path / "web_ex.db"
    init_db(db_path)

    # Pre-seed one exercise.
    yaml_path = tmp_path / "ex.yaml"
    yaml_path.write_text(SAMPLE_YAML, encoding="utf-8")
    conn = connect(db_path)
    try:
        spec = ex_mod.load_yaml(yaml_path)
        ex_mod.upsert_exercise(conn, spec)
    finally:
        conn.close()

    app = create_app(db_path=db_path, host=None)
    with TestClient(app) as c:
        yield c


def _register(client: TestClient, name: str = "Anna") -> None:
    r = client.post("/register", data={"display_name": name})
    assert r.status_code == 200


def test_list_requires_auth(client: TestClient) -> None:
    r = client.get("/exercises")
    assert r.status_code == 401


def test_list_shows_seeded_exercise(client: TestClient) -> None:
    _register(client)
    r = client.get("/exercises")
    assert r.status_code == 200
    assert "Hello world" in r.text
    assert "Day 1" in r.text


def test_detail_renders(client: TestClient) -> None:
    _register(client)
    r = client.get("/exercises/day1_p1_hello")
    assert r.status_code == 200
    assert "Hello world" in r.text
    assert "Print hello." in r.text
    # Submission form is present (Phase 3 will wire the action).
    assert 'name="source_code"' in r.text


def test_detail_prefills_textarea_with_last_submission(client: TestClient, monkeypatch) -> None:
    """After submitting, returning to /exercises/{slug} pre-fills the
    textarea with the student's most recent source_code so they can
    iterate instead of starting from scratch.
    """
    import json

    from bio334_checker.core import grader as grader_mod
    from bio334_checker.core import llm_call as llm_mod

    payload = json.dumps({"score": 90, "feedback_md": "ok"})
    monkeypatch.setattr(
        grader_mod, "llm_call",
        lambda *a, **k: llm_mod.LLMResponse(text=payload, raw_json="{}", model_id="x", backend="api"),
    )

    _register(client)

    # First visit: textarea should be empty (no prior submission).
    r0 = client.get("/exercises/day1_p1_hello")
    assert r0.status_code == 200
    assert 'name="source_code"' in r0.text
    # No content between the >...</textarea> tags besides whitespace.
    import re
    m = re.search(r'<textarea[^>]*name="source_code"[^>]*>(.*?)</textarea>',
                  r0.text, flags=re.DOTALL)
    assert m is not None and m.group(1).strip() == ""

    # Submit something distinctive.
    distinctive = "print('my distinctive solution v1')"
    client.post(
        "/submit",
        data={"exercise_slug": "day1_p1_hello", "exercise_version": 1, "source_code": distinctive},
        follow_redirects=False,
    )

    # Revisit detail: the textarea must be prefilled.
    r1 = client.get("/exercises/day1_p1_hello")
    assert r1.status_code == 200
    assert "preloaded below" in r1.text
    m = re.search(r'<textarea[^>]*name="source_code"[^>]*>(.*?)</textarea>',
                  r1.text, flags=re.DOTALL)
    assert m is not None
    # HTML-escape via Jinja2 leaves the apostrophes as &#39; — checks pass.
    assert "my distinctive solution v1" in m.group(1)

    # Submit another version; the prefill should reflect the *latest*.
    distinctive_v2 = "print('my distinctive solution v2')"
    client.post(
        "/submit",
        data={"exercise_slug": "day1_p1_hello", "exercise_version": 1, "source_code": distinctive_v2},
        follow_redirects=False,
    )
    r2 = client.get("/exercises/day1_p1_hello")
    m = re.search(r'<textarea[^>]*name="source_code"[^>]*>(.*?)</textarea>',
                  r2.text, flags=re.DOTALL)
    assert m is not None
    assert "v2" in m.group(1)
    assert "v1" not in m.group(1)


def test_detail_404_for_unknown_slug(client: TestClient) -> None:
    _register(client)
    r = client.get("/exercises/no_such_slug")
    assert r.status_code == 404


def test_submit_route_now_wired(client: TestClient) -> None:
    """Phase 3: /submit is no longer a 501 placeholder. We don't exercise the
    LLM here (covered in test_web_submit.py); we just confirm the route is
    not the old 501 stub."""
    _register(client)
    r = client.post(
        "/submit",
        data={
            "exercise_slug": "day1_p1_hello",
            "exercise_version": "1",
            "source_code": "print('hello')",
        },
        follow_redirects=False,
    )
    # Either redirect (LLM ran) or 5xx (LLM not configured / network) — but
    # never the Phase-2 501 placeholder.
    assert r.status_code != 501
