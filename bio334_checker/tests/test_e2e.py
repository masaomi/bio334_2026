"""End-to-end smoke test of the full student + instructor flow.

Walks through:
  1. App boot + DB migrate.
  2. Bundled YAML exercises load.
  3. Student registers, lists exercises, opens one, submits.
  4. Submission gets graded (LLM stubbed) and shown on /me + /dashboard.
  5. Instructor admin views the heat map and exports tar.gz.

Acts as the Phase 7 "demo dry-run" gate.
"""

from __future__ import annotations

import base64
import io
import json
import tarfile
from importlib import resources
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from bio334_checker.core import exercises as ex_mod
from bio334_checker.core import grader as grader_mod
from bio334_checker.core import llm_call as llm_mod
from bio334_checker.db.connection import connect, init_db
from bio334_checker.interfaces.web.app import create_app


def _basic(user: str, pwd: str) -> dict:
    raw = base64.b64encode(f"{user}:{pwd}".encode("utf-8")).decode("ascii")
    return {"Authorization": f"Basic {raw}"}


@pytest.fixture()
def world(tmp_path: Path, monkeypatch):
    """Spin up an app with the bundled exercise YAMLs imported."""
    monkeypatch.setenv("BIO334_INSECURE_COOKIE", "1")
    monkeypatch.setenv("BIO334_ADMIN_USER", "instructor")
    monkeypatch.setenv("BIO334_ADMIN_PASS", "tunnel")

    db_path = tmp_path / "e2e.db"
    init_db(db_path)

    # Import every bundled YAML exercise (skips *.example.yaml).
    pkg_data = Path(resources.files("bio334_checker.data").joinpath("exercises"))
    conn = connect(db_path)
    try:
        for spec in ex_mod.load_dir(pkg_data):
            ex_mod.upsert_exercise(conn, spec)
    finally:
        conn.close()

    # LLM stub: pass when source contains substring 'def ', else low score.
    def stub(_p, *, system=None, max_tokens=2048, cache_system=True):
        # Distinguish hint vs grade by inspecting the system prompt.
        if system and "hint-giver" in system:
            return llm_mod.LLMResponse(
                text="Think about iterating positionally.",
                raw_json="{}", model_id="stub", backend="api",
            )
        # Default grader: produce a decent passing score so the e2e flow
        # exercises the passed=1 → attestation path.
        payload = json.dumps({"score": 80, "feedback_md": "Looks reasonable.", "hints": []})
        return llm_mod.LLMResponse(text=payload, raw_json="{}", model_id="stub", backend="api")

    monkeypatch.setattr(grader_mod, "llm_call", stub)
    monkeypatch.setattr(llm_mod, "llm_call", stub)

    app = create_app(
        db_path=db_path,
        host=None,
        admin_allowed_hosts=("127.0.0.1", "::1", ""),
    )
    return {
        "app": app,
        "db_path": db_path,
    }


def test_full_student_then_admin_flow(world, tmp_path) -> None:
    app = world["app"]

    with TestClient(app) as student:
        # 1. Student registers.
        r = student.post("/register", data={"display_name": "Anna"})
        assert r.status_code == 200
        # Handle ends up in localStorage in real life; the cookie lets us
        # continue without it here.

        # 2. Student lists exercises and sees the bundled set.
        r = student.get("/exercises")
        assert r.status_code == 200
        for slug in ("day1_p2_seq_compare", "day2_p3_tajima_d", "day3_final"):
            assert slug in r.text

        # 3. Student opens one exercise (records exercise_open event).
        r = student.get("/exercises/day1_p2_seq_compare")
        assert r.status_code == 200
        assert "Hints:" in r.text

        # 4. Student submits code.
        r = student.post(
            "/submit",
            data={
                "exercise_slug": "day1_p2_seq_compare",
                "exercise_version": 1,
                "source_code": "def diff(a, b):\n    return sum(x != y for x, y in zip(a, b))\nprint(diff('AAA', 'AAT'))",
            },
            follow_redirects=False,
        )
        assert r.status_code in (302, 303)
        location = r.headers["location"]
        assert location.startswith("/submissions/")

        # 5. Result page shows provisional banner and the passing verdict.
        rr = student.get(location)
        assert rr.status_code == 200
        assert "may be wrong" in rr.text
        assert "PASSED" in rr.text

        # 6. /me shows progress.
        rm = student.get("/me")
        assert rm.status_code == 200
        assert "passed" in rm.text.lower()

        # 7. /dashboard renders.
        rd = student.get("/dashboard")
        assert rd.status_code == 200
        assert "Cohort dashboard" in rd.text

    # 8. Admin pulls the heat map and the export tarball (separate client
    #    so cookies don't leak between roles).
    with TestClient(app) as admin:
        ra = admin.get("/admin", headers=_basic("instructor", "tunnel"))
        assert ra.status_code == 200
        assert "Heat map" in ra.text
        assert "Anna" in ra.text  # display_name visible to admin (R-13)

        rx = admin.get("/admin/export", headers=_basic("instructor", "tunnel"))
        assert rx.status_code == 200
        with tarfile.open(fileobj=io.BytesIO(rx.content), mode="r:gz") as tar:
            names = tar.getnames()
        assert any(n.endswith(".db") for n in names)


def test_chain_replay_after_submission(world, tmp_path) -> None:
    """Sanity-check the post-course reconciliation pathway.

    Run a submission, then call the chain bridge directly. The submission
    should land both a chain_record and (because it passed) an attestation.
    """
    from bio334_checker.chain.bridge import chain_drain_once
    from bio334_checker.chain.client import LogKCClient

    app = world["app"]
    with TestClient(app) as student:
        student.post("/register", data={"display_name": "Bob"})
        student.post(
            "/submit",
            data={
                "exercise_slug": "day1_p3_pi_intro",
                "exercise_version": 1,
                "source_code": "def f(): pass\nprint(0.0)",
            },
            follow_redirects=False,
        )

    log_path = tmp_path / "chain.jsonl"
    conn = connect(world["db_path"])
    try:
        counters = chain_drain_once(conn, LogKCClient(log_path))
    finally:
        conn.close()

    assert counters.records_written == 1
    assert counters.attestations_written == 1
    text = log_path.read_text(encoding="utf-8")
    assert '"display_name"' not in text  # I-PRIV-2 holds end-to-end
