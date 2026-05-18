"""Authentication: handle issuance, sessions, rate limiting, tombstoning.

Per ARCHITECTURE.md §5 / §2 / I-AUTH-1..3 / I-RATE-1.

Handle is a *reusable bootstrap token* (v0.3 R-3): visiting `/?u=<handle>`
issues a fresh session cookie. Subsequent requests use the cookie. Per-IP
*and* per-handle rate limits cap brute force; the per-handle counter is
load-bearing because classroom NAT may share egress IP across 30 students.
"""

from __future__ import annotations

import json
import secrets
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Optional


# 31-char ambiguity-free pool: l/i/o/1/0 excluded
HANDLE_ALPHABET = "abcdefghjkmnpqrstuvwxyz23456789"
HANDLE_LENGTH = 4
HANDLE_COLLISION_RETRY = 100

SESSION_TTL_HOURS = 24

# Rate-limit policy: 5 fails / 60s window → 600s lockout
RATE_LIMIT_MAX = 5
RATE_LIMIT_WINDOW_S = 60
RATE_LIMIT_LOCKOUT_S = 600


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _iso(t: datetime) -> str:
    return t.isoformat()


# ----------------------------------------------------------------------------
# Handle generation
# ----------------------------------------------------------------------------

def generate_handle() -> str:
    """Return one fresh random 4-char handle from the alphabet pool.

    Uniqueness is the caller's responsibility; see :func:`issue_handle`.
    """
    return "".join(secrets.choice(HANDLE_ALPHABET) for _ in range(HANDLE_LENGTH))


def issue_handle(conn: sqlite3.Connection, display_name: str) -> str:
    """Insert a fresh user row with a collision-free handle. Returns the handle."""
    display = display_name.strip()
    if not display:
        raise ValueError("display_name must not be empty")
    if len(display) > 32:
        raise ValueError("display_name must be <= 32 characters")

    now_iso = _iso(_now())
    last_err: Optional[Exception] = None

    for _ in range(HANDLE_COLLISION_RETRY):
        handle = generate_handle()
        try:
            conn.execute(
                "INSERT INTO users (handle, display_name, created_at, last_seen_at) "
                "VALUES (?, ?, ?, ?)",
                (handle, display, now_iso, now_iso),
            )
            return handle
        except sqlite3.IntegrityError as e:
            last_err = e
            continue

    raise RuntimeError(
        f"could not generate a unique handle in {HANDLE_COLLISION_RETRY} tries: {last_err}"
    )


# ----------------------------------------------------------------------------
# Session management
# ----------------------------------------------------------------------------

@dataclass
class Session:
    cookie_id: str
    handle: str
    expires_at: datetime


def issue_session(conn: sqlite3.Connection, handle: str) -> Session:
    """Create a new session row and return its cookie value.

    24h sliding TTL (the TTL is bumped on each authed request via
    :func:`touch_session`).
    """
    cookie_id = secrets.token_urlsafe(32)
    now = _now()
    expires = now + timedelta(hours=SESSION_TTL_HOURS)
    conn.execute(
        "INSERT INTO sessions (cookie_id, handle, created_at, expires_at, last_seen_at) "
        "VALUES (?, ?, ?, ?, ?)",
        (cookie_id, handle, _iso(now), _iso(expires), _iso(now)),
    )
    return Session(cookie_id=cookie_id, handle=handle, expires_at=expires)


def lookup_session(conn: sqlite3.Connection, cookie_id: str) -> Optional[Session]:
    """Return a non-expired session bound to a non-tombstoned user, or None."""
    row = conn.execute(
        """SELECT s.cookie_id, s.handle, s.expires_at, u.tombstoned_at
             FROM sessions s
             JOIN users    u ON u.handle = s.handle
            WHERE s.cookie_id = ?""",
        (cookie_id,),
    ).fetchone()
    if row is None:
        return None
    if row["tombstoned_at"] is not None:
        # Defense in depth: tombstoning should already CASCADE-delete sessions.
        conn.execute("DELETE FROM sessions WHERE cookie_id = ?", (cookie_id,))
        return None
    expires_at = datetime.fromisoformat(row["expires_at"])
    if expires_at < _now():
        conn.execute("DELETE FROM sessions WHERE cookie_id = ?", (cookie_id,))
        return None
    return Session(
        cookie_id=row["cookie_id"], handle=row["handle"], expires_at=expires_at
    )


def touch_session(conn: sqlite3.Connection, session: Session) -> Session:
    """Slide the TTL forward 24h on each authed request."""
    now = _now()
    new_expires = now + timedelta(hours=SESSION_TTL_HOURS)
    conn.execute(
        "UPDATE sessions SET expires_at = ?, last_seen_at = ? WHERE cookie_id = ?",
        (_iso(new_expires), _iso(now), session.cookie_id),
    )
    conn.execute(
        "UPDATE users SET last_seen_at = ? WHERE handle = ?",
        (_iso(now), session.handle),
    )
    return Session(
        cookie_id=session.cookie_id, handle=session.handle, expires_at=new_expires
    )


def revoke_session(conn: sqlite3.Connection, cookie_id: str) -> None:
    conn.execute("DELETE FROM sessions WHERE cookie_id = ?", (cookie_id,))


def sweep_expired_sessions(conn: sqlite3.Connection) -> int:
    """Lazy cleanup: delete any session past its expires_at."""
    now_iso = _iso(_now())
    cur = conn.execute("DELETE FROM sessions WHERE expires_at < ?", (now_iso,))
    return cur.rowcount or 0


# ----------------------------------------------------------------------------
# Rate limiting (per-IP and per-handle)
# ----------------------------------------------------------------------------

def _record_event(
    conn: sqlite3.Connection,
    *,
    ip: str,
    handle: Optional[str],
    event_type: str,
    detail: Optional[dict] = None,
) -> None:
    conn.execute(
        "INSERT INTO events (ip, handle, event_type, detail_json, created_at) "
        "VALUES (?, ?, ?, ?, ?)",
        (
            ip,
            handle,
            event_type,
            json.dumps(detail) if detail else None,
            _iso(_now()),
        ),
    )


def _bump_rate_limit(
    conn: sqlite3.Connection, scope: str, key: str, bucket: str
) -> int:
    """Increment the (scope,key,bucket) counter; return current count.

    Window is sliding: when the existing window is older than RATE_LIMIT_WINDOW_S,
    we reset count to 1 and start a new window. Otherwise we increment.
    Lockout (extra wait beyond the window) is enforced in :func:`check_rate_limit`
    by treating count >= RATE_LIMIT_MAX as locked until window_start +
    RATE_LIMIT_LOCKOUT_S.
    """
    now = _now()
    row = conn.execute(
        "SELECT count, window_start FROM rate_limits WHERE scope=? AND key=? AND bucket=?",
        (scope, key, bucket),
    ).fetchone()
    if row is None:
        conn.execute(
            "INSERT INTO rate_limits (scope, key, bucket, count, window_start) "
            "VALUES (?, ?, ?, 1, ?)",
            (scope, key, bucket, _iso(now)),
        )
        return 1
    window_start = datetime.fromisoformat(row["window_start"])
    elapsed = (now - window_start).total_seconds()
    if elapsed >= RATE_LIMIT_WINDOW_S and row["count"] < RATE_LIMIT_MAX:
        # Window expired, no lockout in effect → reset.
        conn.execute(
            "UPDATE rate_limits SET count=1, window_start=? "
            "WHERE scope=? AND key=? AND bucket=?",
            (_iso(now), scope, key, bucket),
        )
        return 1
    new_count = row["count"] + 1
    conn.execute(
        "UPDATE rate_limits SET count=? WHERE scope=? AND key=? AND bucket=?",
        (new_count, scope, key, bucket),
    )
    return new_count


def _is_locked_out(
    conn: sqlite3.Connection, scope: str, key: str, bucket: str
) -> bool:
    row = conn.execute(
        "SELECT count, window_start FROM rate_limits WHERE scope=? AND key=? AND bucket=?",
        (scope, key, bucket),
    ).fetchone()
    if row is None:
        return False
    if row["count"] < RATE_LIMIT_MAX:
        return False
    window_start = datetime.fromisoformat(row["window_start"])
    elapsed = (_now() - window_start).total_seconds()
    return elapsed < RATE_LIMIT_LOCKOUT_S


def check_login_allowed(
    conn: sqlite3.Connection, ip: str, handle: Optional[str]
) -> bool:
    """Return False if either the IP or the handle is currently locked out."""
    if _is_locked_out(conn, "ip", ip, "login_fail"):
        return False
    if handle is not None and _is_locked_out(conn, "handle", handle, "login_fail"):
        return False
    return True


def record_login_failure(
    conn: sqlite3.Connection, ip: str, attempted_handle: Optional[str]
) -> None:
    """Increment per-IP and (if known) per-handle login_fail counters."""
    _bump_rate_limit(conn, "ip", ip, "login_fail")
    if attempted_handle is not None:
        _bump_rate_limit(conn, "handle", attempted_handle, "login_fail")
    _record_event(
        conn,
        ip=ip,
        handle=attempted_handle,
        event_type="login_fail",
        detail={"attempted_handle": attempted_handle},
    )


# ----------------------------------------------------------------------------
# User lookup / tombstone
# ----------------------------------------------------------------------------

def get_user(conn: sqlite3.Connection, handle: str) -> Optional[sqlite3.Row]:
    return conn.execute(
        "SELECT handle, display_name, tombstoned_at FROM users WHERE handle=?",
        (handle,),
    ).fetchone()


def is_active_user(row: Optional[sqlite3.Row]) -> bool:
    return row is not None and row["tombstoned_at"] is None


def tombstone_user(conn: sqlite3.Connection, handle: str) -> None:
    """Mark a user tombstoned (I-DELETE-1) and revoke all their sessions."""
    now_iso = _iso(_now())
    conn.execute(
        "UPDATE users SET tombstoned_at=? WHERE handle=? AND tombstoned_at IS NULL",
        (now_iso, handle),
    )
    conn.execute("DELETE FROM sessions WHERE handle=?", (handle,))
