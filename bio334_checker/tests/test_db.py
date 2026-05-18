"""Schema smoke test: init_db creates all expected tables."""

from __future__ import annotations

from pathlib import Path

from bio334_checker.db.connection import connect, init_db


def test_init_db_creates_all_tables(tmp_path: Path) -> None:
    db = tmp_path / "test.db"
    init_db(db)
    assert db.exists()

    conn = connect(db)
    try:
        rows = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        ).fetchall()
    finally:
        conn.close()

    names = {r["name"] for r in rows}
    expected = {
        "users",
        "exercises",
        "exercise_revisions",
        "submissions",
        "events",
        "rate_limits",
        "sessions",
    }
    assert expected.issubset(names), f"missing tables: {expected - names}"


def test_init_db_is_idempotent(tmp_path: Path) -> None:
    db = tmp_path / "test.db"
    init_db(db)
    # Re-running should not raise.
    init_db(db)


def test_wal_mode_active(tmp_path: Path) -> None:
    db = tmp_path / "test.db"
    init_db(db)
    conn = connect(db)
    try:
        mode = conn.execute("PRAGMA journal_mode").fetchone()[0]
        busy = conn.execute("PRAGMA busy_timeout").fetchone()[0]
    finally:
        conn.close()
    assert mode.lower() == "wal"
    assert busy >= 5000
