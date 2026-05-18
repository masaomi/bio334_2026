"""Survey: schema, enable flag, anonymity, aggregation."""

from __future__ import annotations

import base64
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from bio334_checker.core import survey as survey_mod
from bio334_checker.db.connection import connect, init_db
from bio334_checker.interfaces.web.app import create_app


def _basic(user: str, pwd: str) -> dict:
    raw = base64.b64encode(f"{user}:{pwd}".encode()).decode()
    return {"Authorization": f"Basic {raw}"}


@pytest.fixture()
def db(tmp_path: Path):
    p = tmp_path / "sv.db"
    init_db(p)
    conn = connect(p)
    yield conn
    conn.close()


def test_disabled_by_default(db) -> None:
    assert survey_mod.is_enabled(db) is False


def test_toggle(db) -> None:
    survey_mod.set_enabled(db, True)
    assert survey_mod.is_enabled(db) is True
    survey_mod.set_enabled(db, False)
    assert survey_mod.is_enabled(db) is False


def test_submit_validates_single_choice(db) -> None:
    n = survey_mod.submit_responses(
        db,
        {
            "prior_python": "10_50h",        # valid
            "comfort_now": "3",              # valid likert
            "pace": "lightning",             # invalid → dropped
            "free_comment": "Loved it!",
            "unknown_key": "x",              # unknown key → dropped
        },
    )
    assert n == 3  # 2 valid choices + 1 free comment


def test_empty_text_is_skipped(db) -> None:
    n = survey_mod.submit_responses(db, {"free_comment": "   "})
    assert n == 0


def test_anonymous_storage_no_handle_column(db) -> None:
    """Regression: survey_responses must NOT have a user_handle column."""
    cols = [
        r["name"] for r in db.execute("PRAGMA table_info(survey_responses)")
    ]
    assert "user_handle" not in cols
    assert "handle" not in cols
    assert "ip" not in cols


def test_aggregate_choice_returns_option_order(db) -> None:
    for v in ["never", "never", "under_10h", "over_50h", "never"]:
        survey_mod.submit_responses(db, {"prior_python": v})
    agg = survey_mod.aggregate_choice(db, "prior_python")
    # Returned in the question's declared option order, not by count.
    keys = [v for v, _, _ in agg]
    assert keys == ["never", "under_10h", "10_50h", "over_50h"]
    counts = {v: c for v, _, c in agg}
    assert counts == {"never": 3, "under_10h": 1, "10_50h": 0, "over_50h": 1}


def test_aggregate_likert_returns_1_to_5(db) -> None:
    for v in ["5", "5", "3", "4", "1"]:
        survey_mod.submit_responses(db, {"comfort_now": v})
    agg = survey_mod.aggregate_choice(db, "comfort_now")
    keys = [v for v, _, _ in agg]
    assert keys == ["1", "2", "3", "4", "5"]


def test_route_404_when_disabled(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("BIO334_INSECURE_COOKIE", "1")
    db_path = tmp_path / "r.db"
    init_db(db_path)
    app = create_app(db_path=db_path, host=None)
    with TestClient(app) as c:
        assert c.get("/survey").status_code == 404
        assert c.post("/survey", data={"prior_python": "never"}).status_code == 404


def test_route_works_when_enabled(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("BIO334_INSECURE_COOKIE", "1")
    db_path = tmp_path / "r.db"
    init_db(db_path)
    conn = connect(db_path)
    try:
        survey_mod.set_enabled(conn, True)
    finally:
        conn.close()
    app = create_app(db_path=db_path, host=None)
    with TestClient(app) as c:
        r = c.get("/survey")
        assert r.status_code == 200
        assert "anonymous" in r.text.lower()
        # Submit
        r2 = c.post(
            "/survey",
            data={"prior_python": "10_50h", "comfort_now": "4"},
            follow_redirects=False,
        )
        assert r2.status_code == 303
        assert r2.headers["location"] == "/survey/thanks"

    # Anonymity: 2 rows landed, no link to any user.
    conn = connect(db_path)
    try:
        rows = conn.execute("SELECT q_key, answer FROM survey_responses").fetchall()
    finally:
        conn.close()
    assert {(r["q_key"], r["answer"]) for r in rows} == {
        ("prior_python", "10_50h"),
        ("comfort_now", "4"),
    }


def test_admin_toggle_route(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("BIO334_INSECURE_COOKIE", "1")
    monkeypatch.setenv("BIO334_ADMIN_USER", "i")
    monkeypatch.setenv("BIO334_ADMIN_PASS", "p")
    db_path = tmp_path / "ra.db"
    init_db(db_path)
    app = create_app(
        db_path=db_path, host=None,
        admin_allowed_hosts=("127.0.0.1", "::1", ""),
    )
    with TestClient(app) as c:
        r = c.post("/admin/survey/toggle", headers=_basic("i", "p"),
                   follow_redirects=False)
        assert r.status_code == 303

    conn = connect(db_path)
    try:
        assert survey_mod.is_enabled(conn) is True
    finally:
        conn.close()
