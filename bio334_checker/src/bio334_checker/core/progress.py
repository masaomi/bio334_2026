"""Progress aggregation: per-handle and cohort-level (anonymized).

Per ARCHITECTURE.md §9.4 (and v0.3 R-13):

- /me + /dashboard show **personal** progress and a **cohort median**
  per exercise. No heat map; that's instructor-only on /admin.
- Cohort median is **suppressed on exercises with fewer than 5 distinct
  submitters** to avoid identifying tail students in a 30-student cohort.

Definitions used here:

- A student "attempted" an exercise if they have any graded submission.
- Their "best score" is ``max(llm_score)`` across their graded submissions.
- Their "passed" flag is True if any of their graded submissions has
  ``passed=1``.
- "Cohort median" is the median of best-scores per distinct handle.
"""

from __future__ import annotations

import sqlite3
import statistics
from dataclasses import dataclass
from typing import Optional


COHORT_MEDIAN_MIN_SUBMITTERS = 5


# ---------------------------------------------------------------------------
# Per-handle
# ---------------------------------------------------------------------------

@dataclass
class PersonalProgressRow:
    slug: str
    title: str
    day: int
    part: int
    order_index: int
    attempted: bool
    passed: bool
    best_score: Optional[int]
    last_status: Optional[str]   # 'graded' | 'pending' | 'failed' | None
    attempts: int


def personal_progress(
    conn: sqlite3.Connection,
    handle: str,
    *,
    student_view: bool = False,
) -> list[PersonalProgressRow]:
    """Per-exercise personal status for a single handle, ordered by syllabus.

    When ``student_view=True`` (the default for ``/me``, ``/dashboard``,
    ``/exercises`` and the leaderboard), exercises hidden by the admin
    are filtered out so students cannot race ahead before the lecturer
    reveals them. Admin views pass ``student_view=False`` and see all.
    """
    if student_view:
        exercises = conn.execute(
            "SELECT slug, title, day, part, order_index FROM exercises "
            "WHERE visible_to_students = 1 ORDER BY day, part, order_index"
        ).fetchall()
    else:
        exercises = conn.execute(
            "SELECT slug, title, day, part, order_index FROM exercises "
            "ORDER BY day, part, order_index"
        ).fetchall()

    # Pull all the student's submissions in one pass; group by exercise_slug.
    rows = conn.execute(
        "SELECT exercise_slug, llm_score, passed, status, id "
        "FROM submissions WHERE user_handle = ? ORDER BY id ASC",
        (handle,),
    ).fetchall()
    by_slug: dict[str, list[sqlite3.Row]] = {}
    for r in rows:
        by_slug.setdefault(r["exercise_slug"], []).append(r)

    out: list[PersonalProgressRow] = []
    for ex in exercises:
        subs = by_slug.get(ex["slug"], [])
        attempted = bool(subs)
        passed = any(int(s["passed"]) == 1 for s in subs)
        best_score: Optional[int] = None
        for s in subs:
            if s["llm_score"] is not None:
                if best_score is None or int(s["llm_score"]) > best_score:
                    best_score = int(s["llm_score"])
        last_status = subs[-1]["status"] if subs else None
        out.append(
            PersonalProgressRow(
                slug=ex["slug"],
                title=ex["title"],
                day=int(ex["day"]),
                part=int(ex["part"]),
                order_index=int(ex["order_index"]),
                attempted=attempted,
                passed=passed,
                best_score=best_score,
                last_status=last_status,
                attempts=len(subs),
            )
        )
    return out


# ---------------------------------------------------------------------------
# Cohort
# ---------------------------------------------------------------------------

@dataclass
class LeaderboardEntry:
    """One row of the class-wide clear-matrix leaderboard.

    The student-facing template renders ``anon_id`` (``somebody_N``); the
    admin template renders ``display_name (handle)`` instead. The
    ``total_score`` is computed for ranking but is NOT shown on the
    student leaderboard — only on the student's own ``/me`` page and on
    the admin views (user direction, 2026-05-13).
    """

    handle: str
    display_name: str
    anon_id: int               # 1..N, in display order (NOT the rank)
    rank: int                  # dense rank by total_score; 0 if score==0
    medal: str                 # '🥇' / '🥈' / '🥉' / ''
    total_score: int
    cleared_count: int
    cells: dict[str, bool]     # exercise_slug -> passed?


_MEDALS = {1: "🥇", 2: "🥈", 3: "🥉"}


def leaderboard(
    conn: sqlite3.Connection, *, student_view: bool = False
) -> tuple[list[LeaderboardEntry], list[dict]]:
    """Build the clear-matrix leaderboard.

    Returns ``(entries, exercises)`` where ``exercises`` is the column
    schema (one entry per exercise in syllabus order).

    Medal assignment (dense rank on distinct ``total_score``):
    - Rank 1 ⇒ 🥇, rank 2 ⇒ 🥈, rank 3 ⇒ 🥉. Ties at the same score share
      the medal. ``total_score == 0`` is never awarded.

    Display ordering: total_score desc, then cleared_count desc as
    tie-breaker (more breadth wins), then handle (stable).
    """
    users = conn.execute(
        "SELECT handle, display_name FROM users WHERE tombstoned_at IS NULL"
    ).fetchall()
    if student_view:
        exercises = conn.execute(
            "SELECT slug, title, day, part, order_index FROM exercises "
            "WHERE visible_to_students = 1 ORDER BY day, part, order_index"
        ).fetchall()
    else:
        exercises = conn.execute(
            "SELECT slug, title, day, part, order_index FROM exercises "
            "ORDER BY day, part, order_index"
        ).fetchall()

    raw: list[dict] = []
    for u in users:
        cells: dict[str, bool] = {}
        total = 0
        cleared = 0
        for ex in exercises:
            r = conn.execute(
                "SELECT MAX(llm_score) AS s, MAX(passed) AS p "
                "FROM submissions WHERE user_handle = ? AND exercise_slug = ? "
                "  AND status = 'graded'",
                (u["handle"], ex["slug"]),
            ).fetchone()
            score = int(r["s"]) if r and r["s"] is not None else 0
            passed = bool(r["p"]) if r and r["p"] is not None else False
            cells[ex["slug"]] = passed
            total += score
            if passed:
                cleared += 1
        raw.append(
            {
                "handle": u["handle"],
                "display_name": u["display_name"],
                "total_score": total,
                "cleared_count": cleared,
                "cells": cells,
            }
        )

    raw.sort(
        key=lambda e: (-e["total_score"], -e["cleared_count"], e["handle"])
    )

    # Dense rank on distinct non-zero scores.
    distinct_rank: dict[int, int] = {}
    for e in raw:
        if e["total_score"] > 0 and e["total_score"] not in distinct_rank:
            distinct_rank[e["total_score"]] = len(distinct_rank) + 1

    entries: list[LeaderboardEntry] = []
    for i, e in enumerate(raw):
        rank = distinct_rank.get(e["total_score"], 0)
        entries.append(
            LeaderboardEntry(
                handle=e["handle"],
                display_name=e["display_name"],
                anon_id=i + 1,
                rank=rank,
                medal=_MEDALS.get(rank, ""),
                total_score=e["total_score"],
                cleared_count=e["cleared_count"],
                cells=e["cells"],
            )
        )

    exercises_view = [
        {
            "slug": ex["slug"],
            "title": ex["title"],
            "day": int(ex["day"]),
            "part": int(ex["part"]),
            "order_index": int(ex["order_index"]),
        }
        for ex in exercises
    ]
    return entries, exercises_view


@dataclass
class CohortRow:
    slug: str
    title: str
    day: int
    part: int
    order_index: int
    submitters: int
    pass_count: int
    median_best_score: Optional[float]   # None when suppressed
    suppressed: bool


def cohort_progress(
    conn: sqlite3.Connection, *, student_view: bool = False
) -> list[CohortRow]:
    """Anonymized cohort summary; suppresses median when submitters < N."""
    if student_view:
        exercises = conn.execute(
            "SELECT slug, title, day, part, order_index FROM exercises "
            "WHERE visible_to_students = 1 ORDER BY day, part, order_index"
        ).fetchall()
    else:
        exercises = conn.execute(
            "SELECT slug, title, day, part, order_index FROM exercises "
            "ORDER BY day, part, order_index"
        ).fetchall()

    out: list[CohortRow] = []
    for ex in exercises:
        # Per (handle), best LLM score so far on this exercise.
        rows = conn.execute(
            "SELECT user_handle, MAX(llm_score) AS best, MAX(passed) AS any_pass "
            "FROM submissions WHERE exercise_slug = ? AND status = 'graded' "
            "GROUP BY user_handle",
            (ex["slug"],),
        ).fetchall()
        submitters = len(rows)
        pass_count = sum(int(r["any_pass"] or 0) for r in rows)
        scores = [int(r["best"]) for r in rows if r["best"] is not None]

        if submitters < COHORT_MEDIAN_MIN_SUBMITTERS or not scores:
            median = None
            suppressed = True
        else:
            median = float(statistics.median(scores))
            suppressed = False

        out.append(
            CohortRow(
                slug=ex["slug"],
                title=ex["title"],
                day=int(ex["day"]),
                part=int(ex["part"]),
                order_index=int(ex["order_index"]),
                submitters=submitters,
                pass_count=pass_count,
                median_best_score=median,
                suppressed=suppressed,
            )
        )
    return out
