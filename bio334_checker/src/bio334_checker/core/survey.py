"""End-of-course survey: anonymous student feedback.

User direction (2026-05-13):
- Completely anonymous: NO ``user_handle`` column on responses.
- Admin toggles availability via a row in ``settings``; the student-facing
  link only renders when the flag is on.
- Mostly single-choice + a few Likert items; one optional free-text at
  the end. Aggregate as pie (single-choice) and bar (Likert).

This module owns the (hardcoded) question schema, the on-off flag, and
the aggregation queries. Routes in ``interfaces/web/routes_survey.py``
+ admin route handle HTTP.
"""

from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from typing import Optional


SETTINGS_SURVEY_ENABLED = "survey_enabled"


# Question schema. ``key`` is stable string (don't rename mid-course).
# ``type`` is one of: 'single' (radio, pie chart), 'likert' (1..5, bar),
# 'text' (textarea, listed as raw responses).
SURVEY_QUESTIONS: list[dict] = [
    {
        "key": "prior_python",
        "type": "single",
        "prompt": "Prior Python experience before this course",
        "options": [
            ("never", "I had never written Python before"),
            ("under_10h", "Less than 10 hours total"),
            ("10_50h", "10–50 hours"),
            ("over_50h", "More than 50 hours"),
        ],
    },
    {
        "key": "comfort_now",
        "type": "likert",
        "prompt": "How comfortable do you feel with Python now?",
        "low_label": "Not at all comfortable",
        "high_label": "Very comfortable",
    },
    {
        "key": "checker_helped",
        "type": "likert",
        "prompt": "The exercise checker helped me learn.",
        "low_label": "Strongly disagree",
        "high_label": "Strongly agree",
    },
    {
        "key": "llm_feedback_useful",
        "type": "likert",
        "prompt": "The LLM grader's feedback was useful.",
        "low_label": "Strongly disagree",
        "high_label": "Strongly agree",
    },
    {
        "key": "disagreement_helped",
        "type": "likert",
        "prompt": "When the canonical-output check and the LLM grader "
                  "disagreed, that disagreement helped me think.",
        "low_label": "Strongly disagree",
        "high_label": "Strongly agree",
    },
    {
        "key": "hint_timing",
        "type": "single",
        "prompt": "Hints unlocked at the right time?",
        "options": [
            ("too_early", "Too early — I would have figured it out"),
            ("right", "About right"),
            ("too_late", "Too late — I was already very stuck"),
            ("never_used", "I never used hints"),
        ],
    },
    {
        "key": "external_llm_use",
        "type": "single",
        "prompt": "Did you use external LLMs (ChatGPT, Claude, etc.) "
                  "on the course exercises?",
        "options": [
            ("none", "Not at all"),
            ("once_twice", "Once or twice"),
            ("several", "Several times"),
            ("almost_always", "Almost always"),
        ],
    },
    {
        "key": "philosophy_correct",
        "type": "likert",
        "prompt": "The course philosophy — 'LLM optional, manual typing "
                  "primary' — is correct for an introductory course.",
        "low_label": "Strongly disagree",
        "high_label": "Strongly agree",
    },
    {
        "key": "pace",
        "type": "single",
        "prompt": "Course pace",
        "options": [
            ("too_slow", "Too slow"),
            ("right", "About right"),
            ("too_fast", "Too fast"),
        ],
    },
    {
        "key": "valuable_day",
        "type": "single",
        "prompt": "Which day was most valuable to you?",
        "options": [
            ("day1", "Day 1"),
            ("day2", "Day 2"),
            ("day3", "Day 3"),
            ("equal", "All equal"),
        ],
    },
    {
        "key": "difficult_day",
        "type": "single",
        "prompt": "Which day was most difficult?",
        "options": [
            ("day1", "Day 1"),
            ("day2", "Day 2"),
            ("day3", "Day 3"),
            ("equal", "All equal"),
        ],
    },
    {
        "key": "free_comment",
        "type": "text",
        "prompt": "Anything else? (optional)",
    },
]


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


# ---------------------------------------------------------------------------
# Flag
# ---------------------------------------------------------------------------

def is_enabled(conn: sqlite3.Connection) -> bool:
    row = conn.execute(
        "SELECT value FROM settings WHERE key = ?", (SETTINGS_SURVEY_ENABLED,)
    ).fetchone()
    return row is not None and row["value"] == "true"


def set_enabled(conn: sqlite3.Connection, value: bool) -> None:
    now = _now_iso()
    conn.execute(
        "INSERT INTO settings (key, value, updated_at) VALUES (?, ?, ?) "
        "ON CONFLICT(key) DO UPDATE SET value = excluded.value, "
        "updated_at = excluded.updated_at",
        (SETTINGS_SURVEY_ENABLED, "true" if value else "false", now),
    )


# ---------------------------------------------------------------------------
# Validation / write
# ---------------------------------------------------------------------------

def _allowed_values(q: dict) -> Optional[set[str]]:
    if q["type"] == "single":
        return {opt[0] for opt in q["options"]}
    if q["type"] == "likert":
        return {"1", "2", "3", "4", "5"}
    return None  # free text: anything allowed


def submit_responses(
    conn: sqlite3.Connection, answers: dict[str, str]
) -> int:
    """Insert one row per question that received an answer.

    Validates: single-choice / likert answers must be in the allowed
    set. Free-text answers are stripped; an empty free-text is skipped
    (the field is optional). Returns the number of rows inserted.
    """
    by_key = {q["key"]: q for q in SURVEY_QUESTIONS}
    inserted = 0
    now = _now_iso()
    for q_key, value in answers.items():
        q = by_key.get(q_key)
        if q is None:
            continue
        v = (value or "").strip()
        if q["type"] == "text":
            if not v:
                continue
            v = v[:5000]  # generous cap
        else:
            allowed = _allowed_values(q)
            if allowed is not None and v not in allowed:
                continue  # silently drop bad inputs
        conn.execute(
            "INSERT INTO survey_responses (q_key, answer, created_at) "
            "VALUES (?, ?, ?)",
            (q_key, v, now),
        )
        inserted += 1
    return inserted


# ---------------------------------------------------------------------------
# Aggregation
# ---------------------------------------------------------------------------

def aggregate_choice(
    conn: sqlite3.Connection, q_key: str
) -> list[tuple[str, str, int]]:
    """For single / likert questions: returns [(value, label, count)]
    in the question's option order. Likert is rendered as 1..5 with
    the question's low/high labels.
    """
    q = next((q for q in SURVEY_QUESTIONS if q["key"] == q_key), None)
    if q is None or q["type"] == "text":
        return []
    rows = conn.execute(
        "SELECT answer, COUNT(*) AS c FROM survey_responses "
        "WHERE q_key = ? GROUP BY answer",
        (q_key,),
    ).fetchall()
    counts = {r["answer"]: int(r["c"]) for r in rows}

    if q["type"] == "single":
        return [
            (val, label, counts.get(val, 0)) for (val, label) in q["options"]
        ]
    # likert
    return [
        (str(i), _likert_label(q, i), counts.get(str(i), 0))
        for i in range(1, 6)
    ]


def _likert_label(q: dict, i: int) -> str:
    if i == 1:
        return f"1 ({q['low_label']})"
    if i == 5:
        return f"5 ({q['high_label']})"
    return str(i)


def aggregate_text(conn: sqlite3.Connection, q_key: str) -> list[str]:
    rows = conn.execute(
        "SELECT answer FROM survey_responses WHERE q_key = ? ORDER BY id",
        (q_key,),
    ).fetchall()
    return [r["answer"] for r in rows]


def total_submissions(conn: sqlite3.Connection) -> int:
    """Approximate count of distinct submissions (one survey form post).

    Counts the most frequent single-choice question's responses — that
    column is mandatory so it equals the number of submissions. (Anonymous,
    so we can't COUNT(DISTINCT user).)
    """
    keys = [q["key"] for q in SURVEY_QUESTIONS if q["type"] != "text"]
    if not keys:
        return 0
    placeholders = ",".join("?" * len(keys))
    rows = conn.execute(
        f"SELECT q_key, COUNT(*) AS c FROM survey_responses "
        f"WHERE q_key IN ({placeholders}) GROUP BY q_key",
        keys,
    ).fetchall()
    return max((int(r["c"]) for r in rows), default=0)
