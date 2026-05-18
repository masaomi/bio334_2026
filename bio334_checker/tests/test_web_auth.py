"""End-to-end auth flow via FastAPI TestClient."""

from __future__ import annotations

import os
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from bio334_checker.interfaces.web.app import create_app
from bio334_checker.interfaces.web.dependencies import SESSION_COOKIE_NAME


@pytest.fixture()
def client(tmp_path: Path, monkeypatch):
    # TestClient runs over plain HTTP, so drop the Secure flag.
    monkeypatch.setenv("BIO334_INSECURE_COOKIE", "1")
    app = create_app(db_path=tmp_path / "web.db", host=None)
    with TestClient(app) as c:
        yield c


def test_landing_renders(client: TestClient) -> None:
    r = client.get("/")
    assert r.status_code == 200
    assert "Register" in r.text


def test_register_then_me(client: TestClient) -> None:
    r = client.post("/register", data={"display_name": "Anna"}, follow_redirects=False)
    assert r.status_code == 200
    assert "Your handle is" in r.text
    assert SESSION_COOKIE_NAME in client.cookies

    r2 = client.get("/me")
    assert r2.status_code == 200
    assert "Anna" in r2.text


def test_bootstrap_via_root_url_with_u_query(client: TestClient) -> None:
    """Regression: ``GET /?u=<handle>`` IS the canonical bootstrap URL given
    to students (QR + paper memo). Previously the landing route ignored the
    ``?u=`` query parameter, so after logout the URL led back to the
    register screen instead of re-authenticating. Found during the
    2026-05-12 dry-run.
    """
    r = client.post("/register", data={"display_name": "Anna"})
    assert r.status_code == 200
    handle = _extract_handle(r.text)

    # Log out — cookie cleared, session revoked.
    client.cookies.clear()

    # The QR / paper-memo URL hits /?u=handle directly. This must
    # bootstrap a fresh session and redirect to /me.
    r = client.get(f"/?u={handle}", follow_redirects=False)
    assert r.status_code in (302, 303), f"got {r.status_code}, body={r.text[:200]}"
    assert r.headers["location"] == "/me"
    assert SESSION_COOKIE_NAME in client.cookies


def test_login_via_url_token_reusable(client: TestClient) -> None:
    """v0.3 R-3: handle URL is reusable bootstrap, not single-use."""
    r = client.post("/register", data={"display_name": "Bob"})
    assert r.status_code == 200
    handle = _extract_handle(r.text)

    # Wipe cookies; simulate a different device.
    client.cookies.clear()

    r = client.get(f"/login?u={handle}", follow_redirects=False)
    assert r.status_code in (302, 303)
    assert SESSION_COOKIE_NAME in client.cookies

    # And again from yet another "device" — must still work (reusable).
    client.cookies.clear()
    r2 = client.get(f"/login?u={handle}", follow_redirects=False)
    assert r2.status_code in (302, 303)


def test_login_unknown_handle_returns_401(client: TestClient) -> None:
    r = client.get("/login?u=zzzz", follow_redirects=False)
    assert r.status_code == 401


def test_logout_clears_session(client: TestClient) -> None:
    r = client.post("/register", data={"display_name": "Carol"})
    assert r.status_code == 200
    r = client.post("/logout", follow_redirects=False)
    assert r.status_code in (302, 303)
    # /me now requires auth and we are logged out
    r = client.get("/me")
    assert r.status_code == 401


def test_me_requires_cookie(client: TestClient) -> None:
    r = client.get("/me")
    assert r.status_code == 401


def test_admin_blocked_for_non_loopback() -> None:
    """v0.3 R-6: /admin* must be 127.0.0.1 only.

    The middleware refuses requests whose client.host is not loopback. The
    TestClient default client host is 'testclient', which fails the check.
    """
    app = create_app(host=None)
    with TestClient(app) as c:
        r = c.get("/admin")
        assert r.status_code == 403


def _extract_handle(html: str) -> str:
    import re

    m = re.search(r'<span class="handle">([a-z0-9]{4})</span>', html)
    assert m, f"handle not found in:\n{html[:400]}"
    return m.group(1)
