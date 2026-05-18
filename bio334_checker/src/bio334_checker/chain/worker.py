"""Singleton background worker.

Per ARCHITECTURE.md §7.2: a single in-process FastAPI background task
started at app ``lifespan`` startup handles both:

1. Re-grading ``status='pending'`` submissions (Phase 3 ``drain_once``).
2. Writing chain records and attestations for graded submissions
   (Phase 5 ``chain_drain_once``).

Cadence:
- 2 seconds when there is work in either queue.
- 10 seconds idle.

The worker is intentionally a single coroutine so the I-CHAIN-1
"exactly one" guarantee holds without coordination across processes.
"""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path
from typing import Optional

from bio334_checker.chain.bridge import chain_drain_once
from bio334_checker.chain.client import KCClient, default_client
from bio334_checker.core import drain as drain_mod
from bio334_checker.db.connection import connect


_BUSY_INTERVAL_S = 2.0
_IDLE_INTERVAL_S = 10.0


log = logging.getLogger("bio334_checker.worker")


class BackgroundWorker:
    """Wraps the asyncio task lifecycle. Stateless beyond the task handle."""

    def __init__(
        self,
        *,
        db_path: Path,
        kc_client: Optional[KCClient] = None,
    ) -> None:
        self._db_path = db_path
        self._client: KCClient = kc_client or default_client()
        self._task: Optional[asyncio.Task] = None
        self._stop = asyncio.Event()

    async def start(self) -> None:
        if self._task is not None:
            return
        self._stop.clear()
        self._task = asyncio.create_task(self._run(), name="bio334-bg-worker")

    async def stop(self) -> None:
        if self._task is None:
            return
        self._stop.set()
        try:
            await asyncio.wait_for(self._task, timeout=5.0)
        except asyncio.TimeoutError:
            self._task.cancel()
        finally:
            self._task = None

    async def _run(self) -> None:
        log.info("worker started")
        while not self._stop.is_set():
            had_work = await asyncio.to_thread(self._tick_sync)
            interval = _BUSY_INTERVAL_S if had_work else _IDLE_INTERVAL_S
            try:
                await asyncio.wait_for(self._stop.wait(), timeout=interval)
            except asyncio.TimeoutError:
                continue
        log.info("worker stopped")

    def _tick_sync(self) -> bool:
        """Synchronous one-tick: open a fresh connection, drain both queues."""
        conn = connect(self._db_path)
        had_work = False
        try:
            d = drain_mod.drain_once(conn)
            if any(d.values()):
                had_work = True
            c = chain_drain_once(conn, self._client)
            if (
                c.records_written
                + c.attestations_written
                + c.transient_errors
                + c.permanent_errors
            ) > 0:
                had_work = True
        except Exception:  # pragma: no cover (defensive)
            log.exception("worker tick failed")
        finally:
            conn.close()
        return had_work
