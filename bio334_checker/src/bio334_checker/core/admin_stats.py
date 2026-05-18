"""Aggregations for the instructor admin views.

Per ARCHITECTURE.md §9.4 (R-13): the admin sees the heat map, per-handle
drill-down with ``display_name (handle)`` together, the disagreement log,
and the hint-usage log. Display names stay local — never on chain.
"""

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from typing import Optional


@dataclass
class HeatCell:
    slug: str
    title: str
    day: int
    part: int
    order_index: int
    submitters: int
    pass_count: int
    pending_count: int
    failed_count: int
    median_score: Optional[float]
    avg_attempts: Optional[float]


def heat_map(conn: sqlite3.Connection) -> list[HeatCell]:
    """One cell per exercise. Aggregates over all graded submissions."""
    rows = conn.execute(
        """SELECT slug, title, day, part, order_index FROM exercises
           ORDER BY day, part, order_index"""
    ).fetchall()

    out: list[HeatCell] = []
    for ex in rows:
        agg = conn.execute(
            """SELECT
                  COUNT(DISTINCT user_handle) AS submitters,
                  SUM(CASE WHEN status='graded' AND passed=1 THEN 1 ELSE 0 END) AS pass_count,
                  SUM(CASE WHEN status='pending' THEN 1 ELSE 0 END) AS pending_count,
                  SUM(CASE WHEN status='failed' THEN 1 ELSE 0 END) AS failed_count,
                  COUNT(*) AS total_attempts
                FROM submissions WHERE exercise_slug=?""",
            (ex["slug"],),
        ).fetchone()

        # Median best-score per handle.
        per_handle = conn.execute(
            "SELECT MAX(llm_score) AS best FROM submissions "
            "WHERE exercise_slug=? AND status='graded' AND llm_score IS NOT NULL "
            "GROUP BY user_handle",
            (ex["slug"],),
        ).fetchall()
        scores = sorted(int(r["best"]) for r in per_handle)
        if scores:
            mid = len(scores) // 2
            median = (
                float(scores[mid])
                if len(scores) % 2 == 1
                else (scores[mid - 1] + scores[mid]) / 2.0
            )
        else:
            median = None

        submitters = int(agg["submitters"] or 0)
        avg_attempts = (
            float(agg["total_attempts"]) / submitters if submitters else None
        )

        out.append(
            HeatCell(
                slug=ex["slug"],
                title=ex["title"],
                day=int(ex["day"]),
                part=int(ex["part"]),
                order_index=int(ex["order_index"]),
                submitters=submitters,
                pass_count=int(agg["pass_count"] or 0),
                pending_count=int(agg["pending_count"] or 0),
                failed_count=int(agg["failed_count"] or 0),
                median_score=median,
                avg_attempts=avg_attempts,
            )
        )
    return out


@dataclass
class StudentRow:
    handle: str
    display_name: str
    last_seen_at: str
    tombstoned: bool
    attempts: int
    passed: int
    pending: int
    failed: int


def students_overview(conn: sqlite3.Connection) -> list[StudentRow]:
    """One row per registered student. ``display_name (handle)`` is admin-only."""
    rows = conn.execute(
        """SELECT u.handle, u.display_name, u.last_seen_at, u.tombstoned_at,
                  COUNT(s.id) AS attempts,
                  SUM(CASE WHEN s.status='graded' AND s.passed=1 THEN 1 ELSE 0 END) AS passed,
                  SUM(CASE WHEN s.status='pending' THEN 1 ELSE 0 END) AS pending,
                  SUM(CASE WHEN s.status='failed' THEN 1 ELSE 0 END) AS failed
             FROM users u
        LEFT JOIN submissions s ON s.user_handle = u.handle
         GROUP BY u.handle
         ORDER BY u.last_seen_at DESC"""
    ).fetchall()
    return [
        StudentRow(
            handle=r["handle"],
            display_name=r["display_name"],
            last_seen_at=r["last_seen_at"],
            tombstoned=r["tombstoned_at"] is not None,
            attempts=int(r["attempts"] or 0),
            passed=int(r["passed"] or 0),
            pending=int(r["pending"] or 0),
            failed=int(r["failed"] or 0),
        )
        for r in rows
    ]


@dataclass
class DisagreementRow:
    submission_id: int
    handle: str
    display_name: str
    exercise_slug: str
    kind: str  # 'match_but_grader_failed' | 'grader_passed_but_no_match'
    exact_match: bool
    llm_score: Optional[int]
    created_at: str


def disagreement_log(
    conn: sqlite3.Connection, *, limit: int = 200
) -> list[DisagreementRow]:
    rows = conn.execute(
        """SELECT e.handle, e.detail_json, e.created_at, u.display_name
             FROM events e
        LEFT JOIN users u ON u.handle = e.handle
            WHERE e.event_type = 'grader_disagreement'
         ORDER BY e.id DESC
            LIMIT ?""",
        (limit,),
    ).fetchall()
    out: list[DisagreementRow] = []
    for r in rows:
        try:
            d = json.loads(r["detail_json"] or "{}")
        except json.JSONDecodeError:
            continue
        sub_id = int(d.get("submission_id", 0))
        if sub_id == 0:
            continue
        ex = conn.execute(
            "SELECT exercise_slug FROM submissions WHERE id=?", (sub_id,)
        ).fetchone()
        out.append(
            DisagreementRow(
                submission_id=sub_id,
                handle=r["handle"] or "?",
                display_name=r["display_name"] or "?",
                exercise_slug=ex["exercise_slug"] if ex else "?",
                kind=str(d.get("kind", "?")),
                exact_match=bool(d.get("exact_match", 0)),
                llm_score=d.get("llm_score"),
                created_at=r["created_at"],
            )
        )
    return out


@dataclass
class HintRow:
    handle: str
    display_name: str
    exercise_slug: str
    level: int
    created_at: str


@dataclass
class TokenUsage:
    """Approximate LLM token + cost summary across all grading calls.

    Reads token counts directly from ``submissions.llm_raw_response_json``
    so no schema migration is needed. Both Bedrock and Anthropic-direct
    responses ship the same ``usage.{input,output}_tokens`` shape, so a
    single parser covers both backends. Submissions whose raw_json is
    null or doesn't contain a usage block (e.g. claude-code subprocess
    results) are silently skipped.

    Hint LLM calls are NOT counted — they're cheap nudges and we don't
    store their raw responses. For class-scale budget planning, grading
    calls dominate by orders of magnitude.
    """
    grade_count: int
    input_tokens: int
    output_tokens: int
    cache_read_tokens: int
    cache_creation_tokens: int
    cost_usd_estimate: float
    price_table_note: str


# Defaults are tuned for AWS Bedrock Claude Sonnet 4-6 in eu-central-1
# (USD per million tokens). Override via env if pricing changes:
#   BIO334_TOKEN_PRICE_INPUT_PER_MTOK
#   BIO334_TOKEN_PRICE_OUTPUT_PER_MTOK
#   BIO334_TOKEN_PRICE_CACHE_READ_PER_MTOK
#   BIO334_TOKEN_PRICE_CACHE_WRITE_PER_MTOK
_DEFAULT_PRICE_INPUT = 3.00
_DEFAULT_PRICE_OUTPUT = 15.00
_DEFAULT_PRICE_CACHE_READ = 0.30
_DEFAULT_PRICE_CACHE_WRITE = 3.75


def _price(name: str, fallback: float) -> float:
    import os
    raw = os.getenv(f"BIO334_TOKEN_PRICE_{name}_PER_MTOK")
    if not raw:
        return fallback
    try:
        return float(raw)
    except ValueError:
        return fallback


def token_usage_summary(conn: sqlite3.Connection) -> TokenUsage:
    """Approximate token + cost rollup across all graded submissions."""
    rows = conn.execute(
        "SELECT llm_raw_response_json FROM submissions "
        "WHERE llm_raw_response_json IS NOT NULL AND status = 'graded'"
    ).fetchall()

    n = 0
    in_tok = 0
    out_tok = 0
    cache_read = 0
    cache_write = 0
    for r in rows:
        try:
            payload = json.loads(r["llm_raw_response_json"] or "{}")
        except (json.JSONDecodeError, TypeError):
            continue
        usage = payload.get("usage") if isinstance(payload, dict) else None
        if not isinstance(usage, dict):
            continue
        try:
            in_tok += int(usage.get("input_tokens", 0) or 0)
            out_tok += int(usage.get("output_tokens", 0) or 0)
            cache_read += int(usage.get("cache_read_input_tokens", 0) or 0)
            cache_write += int(usage.get("cache_creation_input_tokens", 0) or 0)
            n += 1
        except (TypeError, ValueError):
            continue

    p_in = _price("INPUT", _DEFAULT_PRICE_INPUT)
    p_out = _price("OUTPUT", _DEFAULT_PRICE_OUTPUT)
    p_cr = _price("CACHE_READ", _DEFAULT_PRICE_CACHE_READ)
    p_cw = _price("CACHE_WRITE", _DEFAULT_PRICE_CACHE_WRITE)
    cost = (
        in_tok * p_in
        + out_tok * p_out
        + cache_read * p_cr
        + cache_write * p_cw
    ) / 1_000_000.0

    note = (
        f"prices (USD per MTok): input={p_in:.2f}, output={p_out:.2f}, "
        f"cache_read={p_cr:.2f}, cache_write={p_cw:.2f}"
    )
    return TokenUsage(
        grade_count=n,
        input_tokens=in_tok,
        output_tokens=out_tok,
        cache_read_tokens=cache_read,
        cache_creation_tokens=cache_write,
        cost_usd_estimate=cost,
        price_table_note=note,
    )


def hint_log(conn: sqlite3.Connection, *, limit: int = 200) -> list[HintRow]:
    rows = conn.execute(
        """SELECT e.handle, e.detail_json, e.created_at, u.display_name
             FROM events e
        LEFT JOIN users u ON u.handle = e.handle
            WHERE e.event_type = 'hint_requested'
         ORDER BY e.id DESC
            LIMIT ?""",
        (limit,),
    ).fetchall()
    out: list[HintRow] = []
    for r in rows:
        try:
            d = json.loads(r["detail_json"] or "{}")
        except json.JSONDecodeError:
            continue
        out.append(
            HintRow(
                handle=r["handle"] or "?",
                display_name=r["display_name"] or "?",
                exercise_slug=str(d.get("slug", "?")),
                level=int(d.get("level", 0)),
                created_at=r["created_at"],
            )
        )
    return out
