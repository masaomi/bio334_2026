"""KairosChain client abstraction.

Per ARCHITECTURE.md §7: all chain writes go through this module. The
``KCClient`` protocol decouples the bridge from any specific transport
(MCP, gem subprocess, HTTP API). The default client is the local JSONL
appender (``LogKCClient``) that acts as a durable pre-replay record:
during the course we accumulate JSONL events; the post-course
reconciliation script replays them onto the actual chain.

This is consistent with I-CHAIN-2: chain ops are advisory to the
user-facing flow, and SQLite remains the source of truth.

Two write methods, both with idempotency keys (v0.3 R-4):
- ``record(key, payload)``    -> chain_block_ref string
- ``issue(key, payload)``     -> attestation_id string
"""

from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Protocol


@dataclass
class KCError(Exception):
    """Generic chain error. ``transient=True`` triggers retry, False is fatal."""

    msg: str
    transient: bool = True

    def __str__(self) -> str:  # pragma: no cover (cosmetic)
        return self.msg


class KCClient(Protocol):
    """Contract every chain backend must satisfy."""

    def record(self, idempotency_key: str, payload: dict) -> str:
        """Record an event. Returns a chain_block_ref. Idempotent on key."""

    def issue(self, idempotency_key: str, payload: dict) -> str:
        """Issue an attestation. Returns an attestation_id. Idempotent on key."""

    def health(self) -> bool:
        """Quick liveness check. Used by the worker for poll cadence."""


# ---------------------------------------------------------------------------
# Default: local JSONL appender (pre-replay durable log)
# ---------------------------------------------------------------------------

DEFAULT_LOG_PATH = Path(os.getenv("BIO334_CHAIN_LOG", "bio334_chain.jsonl"))


class LogKCClient:
    """Append events to a JSONL file with idempotency-key dedup.

    On disk-write success, returns a deterministic id derived from the
    idempotency key, so callers can persist a stable ``chain_block_ref``.
    On a duplicate key the existing id is returned without writing.
    """

    def __init__(self, path: Path | None = None) -> None:
        self._path = Path(path) if path is not None else DEFAULT_LOG_PATH
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._seen: dict[str, str] = {}
        self._load_seen()

    def _load_seen(self) -> None:
        if not self._path.exists():
            return
        try:
            with self._path.open("r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    obj = json.loads(line)
                    key = obj.get("idempotency_key")
                    kind = obj.get("kind")
                    rid = obj.get("id")
                    if isinstance(key, str) and isinstance(rid, str) and isinstance(kind, str):
                        self._seen[f"{kind}:{key}"] = rid
        except (OSError, json.JSONDecodeError):
            # Best-effort. Reconciliation can rebuild on restart.
            pass

    def _id_for(self, kind: str, key: str) -> str:
        h = hashlib.sha256(f"{kind}:{key}".encode("utf-8")).hexdigest()
        return f"{kind}-{h[:16]}"

    def _append(self, kind: str, key: str, payload: dict) -> str:
        dedup_key = f"{kind}:{key}"
        if dedup_key in self._seen:
            return self._seen[dedup_key]
        rid = self._id_for(kind, key)
        entry = {
            "kind": kind,
            "id": rid,
            "idempotency_key": key,
            "ts": datetime.now(timezone.utc).isoformat(),
            "payload": payload,
        }
        with self._path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        self._seen[dedup_key] = rid
        return rid

    def record(self, idempotency_key: str, payload: dict) -> str:
        return self._append("record", idempotency_key, payload)

    def issue(self, idempotency_key: str, payload: dict) -> str:
        return self._append("attestation", idempotency_key, payload)

    def health(self) -> bool:
        return True


# ---------------------------------------------------------------------------
# Stubs for tests
# ---------------------------------------------------------------------------

class NullKCClient:
    """Drops every write. Useful when chain integration is disabled."""

    def record(self, idempotency_key: str, payload: dict) -> str:
        return ""

    def issue(self, idempotency_key: str, payload: dict) -> str:
        return ""

    def health(self) -> bool:
        return False


class FailingKCClient:
    """Always raises a transient KCError. For testing the queue retry path."""

    def record(self, idempotency_key: str, payload: dict) -> str:
        raise KCError("simulated chain outage", transient=True)

    def issue(self, idempotency_key: str, payload: dict) -> str:
        raise KCError("simulated chain outage", transient=True)

    def health(self) -> bool:
        return False


def default_client() -> KCClient:
    """Pick the client based on env. Override via tests by passing explicit clients."""
    backend = os.getenv("BIO334_CHAIN_BACKEND", "log").strip().lower()
    if backend == "null":
        return NullKCClient()
    if backend == "log":
        return LogKCClient()
    raise ValueError(f"unknown BIO334_CHAIN_BACKEND: {backend!r}")
