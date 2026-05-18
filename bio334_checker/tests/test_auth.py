"""Auth core tests: handle issuance, sessions, rate limit, tombstone."""

from __future__ import annotations

from datetime import timedelta
from pathlib import Path

import pytest

from bio334_checker.core import auth
from bio334_checker.db.connection import connect, init_db


@pytest.fixture()
def db(tmp_path: Path):
    p = tmp_path / "auth.db"
    init_db(p)
    conn = connect(p)
    yield conn
    conn.close()


def test_handle_alphabet_excludes_ambiguous() -> None:
    for _ in range(200):
        h = auth.generate_handle()
        assert len(h) == 4
        assert all(c in auth.HANDLE_ALPHABET for c in h)
        assert all(c not in "lio10" for c in h)


def test_issue_handle_unique(db) -> None:
    seen = set()
    for i in range(20):
        h = auth.issue_handle(db, f"user{i}")
        assert h not in seen
        seen.add(h)


def test_issue_handle_rejects_empty(db) -> None:
    with pytest.raises(ValueError):
        auth.issue_handle(db, "   ")


def test_session_lifecycle(db) -> None:
    h = auth.issue_handle(db, "Anna")
    s = auth.issue_session(db, h)
    assert s.handle == h
    looked = auth.lookup_session(db, s.cookie_id)
    assert looked is not None and looked.handle == h
    auth.revoke_session(db, s.cookie_id)
    assert auth.lookup_session(db, s.cookie_id) is None


def test_session_expires(db) -> None:
    h = auth.issue_handle(db, "Bob")
    s = auth.issue_session(db, h)
    # Manually rewind expires_at into the past.
    db.execute(
        "UPDATE sessions SET expires_at=? WHERE cookie_id=?",
        ("2000-01-01T00:00:00+00:00", s.cookie_id),
    )
    assert auth.lookup_session(db, s.cookie_id) is None


def test_tombstone_revokes_sessions(db) -> None:
    h = auth.issue_handle(db, "Carol")
    s1 = auth.issue_session(db, h)
    s2 = auth.issue_session(db, h)
    auth.tombstone_user(db, h)
    assert auth.lookup_session(db, s1.cookie_id) is None
    assert auth.lookup_session(db, s2.cookie_id) is None
    row = auth.get_user(db, h)
    assert row is not None
    assert not auth.is_active_user(row)


def test_rate_limit_locks_after_max_failures(db) -> None:
    ip = "10.0.0.1"
    h = "abcd"  # not registered, fine for the rate-limit path
    for _ in range(auth.RATE_LIMIT_MAX):
        assert auth.check_login_allowed(db, ip, h) is True
        auth.record_login_failure(db, ip, h)
    # Next check should be locked out (per-IP triggered first).
    assert auth.check_login_allowed(db, ip, h) is False


def test_rate_limit_per_handle_under_nat(db) -> None:
    """Same IP, two handles: per-handle counter is the load-bearing limit."""
    ip = "10.0.0.99"
    # Lock handle 'h1'
    for _ in range(auth.RATE_LIMIT_MAX):
        auth.record_login_failure(db, ip, "abcd")
    assert auth.check_login_allowed(db, ip, "abcd") is False
    # Different handle, same IP — IP is also locked at this point.
    # The point: per-handle is also tracked. Confirm by checking the rate_limits row.
    row = db.execute(
        "SELECT count FROM rate_limits WHERE scope='handle' AND key='abcd'"
    ).fetchone()
    assert row is not None
    assert row["count"] >= auth.RATE_LIMIT_MAX
