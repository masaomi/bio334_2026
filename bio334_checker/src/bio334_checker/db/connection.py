"""SQLite connection helper with WAL mode and busy_timeout configured."""

from __future__ import annotations

import os
import sqlite3
from contextlib import contextmanager
from importlib import resources
from pathlib import Path
from typing import Iterator


DEFAULT_DB_PATH = Path(os.getenv("BIO334_DB", "bio334_checker.db"))


def connect(db_path: Path | None = None) -> sqlite3.Connection:
    """Return a configured SQLite connection.

    PRAGMAs are also re-applied per-connection (some are connection-scoped).
    """
    path = db_path if db_path is not None else DEFAULT_DB_PATH
    # check_same_thread=False so a connection can move between starlette
    # threadpool workers within a single request (FastAPI sometimes
    # dispatches dependency vs handler on different threads when an async
    # route shares a router with sync ones). Per SQLite docs this is safe
    # as long as a single connection is not used concurrently from two
    # threads, which is true here: each request has its own connection.
    conn = sqlite3.connect(
        path, isolation_level=None, timeout=5.0, check_same_thread=False
    )
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode = WAL")
    conn.execute("PRAGMA synchronous = NORMAL")
    conn.execute("PRAGMA busy_timeout = 5000")
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def schema_sql() -> str:
    """Return the bundled schema.sql contents."""
    return resources.files("bio334_checker.db").joinpath("schema.sql").read_text(encoding="utf-8")


def init_db(db_path: Path | None = None) -> Path:
    """Create / migrate the SQLite database. Idempotent."""
    path = db_path if db_path is not None else DEFAULT_DB_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = connect(path)
    try:
        conn.executescript(schema_sql())
        _apply_migrations(conn)
    finally:
        conn.close()
    return path


def _apply_migrations(conn: sqlite3.Connection) -> None:
    """Idempotent ALTER TABLE migrations for fields added after v0.3.
    Each block uses pragma_table_info to check before adding."""
    cols = {r["name"] for r in conn.execute("PRAGMA table_info(exercises)")}
    if "visible_to_students" not in cols:
        conn.execute(
            "ALTER TABLE exercises ADD COLUMN "
            "visible_to_students INTEGER NOT NULL DEFAULT 1"
        )
        conn.commit()


@contextmanager
def transaction(conn: sqlite3.Connection) -> Iterator[sqlite3.Connection]:
    """Short-lived BEGIN IMMEDIATE block. Use for multi-statement writes."""
    conn.execute("BEGIN IMMEDIATE")
    try:
        yield conn
    except Exception:
        conn.execute("ROLLBACK")
        raise
    else:
        conn.execute("COMMIT")
