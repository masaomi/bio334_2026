-- bio334-checker SQLite schema (v0.3, ARCHITECTURE.md §4)
-- Idempotent: safe to re-run.

PRAGMA journal_mode = WAL;
PRAGMA synchronous = NORMAL;
PRAGMA busy_timeout = 5000;
PRAGMA foreign_keys = ON;

-- ---------------------------------------------------------------------------
-- users: 4-char handle (§5.1), display_name local-only (I-PRIV-2)
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS users (
    handle         TEXT PRIMARY KEY,
    display_name   TEXT NOT NULL,
    created_at     TEXT NOT NULL,
    last_seen_at   TEXT NOT NULL,
    tombstoned_at  TEXT NULL
);

-- ---------------------------------------------------------------------------
-- exercises: mutable pointer to latest revision
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS exercises (
    slug                  TEXT PRIMARY KEY,
    version               INTEGER NOT NULL DEFAULT 1,
    title                 TEXT NOT NULL,
    day                   INTEGER NOT NULL,
    part                  INTEGER NOT NULL,
    order_index           INTEGER NOT NULL,
    source_gist_url       TEXT NULL,
    visible_to_students   INTEGER NOT NULL DEFAULT 1
);

-- ---------------------------------------------------------------------------
-- exercise_revisions: immutable rubric history (I-VERSION-1)
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS exercise_revisions (
    slug              TEXT NOT NULL REFERENCES exercises(slug),
    version           INTEGER NOT NULL,
    description_md    TEXT NOT NULL,
    expected_stdout   TEXT NULL,
    argv              TEXT NULL,    -- JSON array
    files_provided    TEXT NULL,    -- JSON array
    rubric_md         TEXT NOT NULL,
    max_score         INTEGER NOT NULL DEFAULT 100,
    pass_threshold    INTEGER NOT NULL DEFAULT 70,
    llm_floor         INTEGER NOT NULL DEFAULT 40,
    allow_nonzero_rc  INTEGER NOT NULL DEFAULT 0,
    timeout_s         INTEGER NOT NULL DEFAULT 10,
    created_at        TEXT NOT NULL,
    PRIMARY KEY (slug, version)
);

-- ---------------------------------------------------------------------------
-- submissions: grader writes grading fields, chain bridge writes chain fields
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS submissions (
    id                     INTEGER PRIMARY KEY AUTOINCREMENT,
    user_handle            TEXT NOT NULL REFERENCES users(handle),
    exercise_slug          TEXT NOT NULL REFERENCES exercises(slug),
    exercise_version       INTEGER NOT NULL,
    source_code            TEXT NOT NULL,
    sandbox_stdout         TEXT NULL,
    sandbox_stderr         TEXT NULL,
    sandbox_rc             INTEGER NULL,
    exact_match            INTEGER NOT NULL DEFAULT 0,
    llm_score              INTEGER NULL,
    llm_feedback_md        TEXT NULL,
    llm_raw_response_json  TEXT NULL,
    passed                 INTEGER NOT NULL DEFAULT 0,
    status                 TEXT NOT NULL DEFAULT 'pending',  -- pending|graded|failed
    chain_block_ref        TEXT NULL,
    attestation_id         TEXT NULL,
    grader_version         TEXT NOT NULL,
    model_id               TEXT NOT NULL,
    created_at             TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_submissions_user_exercise
    ON submissions(user_handle, exercise_slug);
CREATE INDEX IF NOT EXISTS idx_submissions_exercise_passed
    ON submissions(exercise_slug, passed);
CREATE INDEX IF NOT EXISTS idx_submissions_chain_pending
    ON submissions(chain_block_ref, status)
    WHERE chain_block_ref IS NULL;

-- ---------------------------------------------------------------------------
-- events: rate-limit / audit log
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS events (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    ip          TEXT NOT NULL,
    handle      TEXT NULL,
    event_type  TEXT NOT NULL,
    detail_json TEXT NULL,
    created_at  TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_events_created_at ON events(created_at);

-- ---------------------------------------------------------------------------
-- rate_limits: per-IP and per-handle counters (I-RATE-1)
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS rate_limits (
    scope         TEXT NOT NULL,            -- 'ip' | 'handle'
    key           TEXT NOT NULL,            -- the IP or the handle
    bucket        TEXT NOT NULL,            -- 'login_fail' | 'submit' | ...
    count         INTEGER NOT NULL,
    window_start  TEXT NOT NULL,
    PRIMARY KEY (scope, key, bucket)
);

-- ---------------------------------------------------------------------------
-- sessions: server-set HttpOnly cookie store, 24h sliding TTL (v0.3 R-7/R-8)
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS sessions (
    cookie_id     TEXT PRIMARY KEY,
    handle        TEXT NOT NULL REFERENCES users(handle) ON DELETE CASCADE,
    created_at    TEXT NOT NULL,
    expires_at    TEXT NOT NULL,
    last_seen_at  TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_sessions_handle ON sessions(handle);
CREATE INDEX IF NOT EXISTS idx_sessions_expires_at ON sessions(expires_at);

-- ---------------------------------------------------------------------------
-- settings: feature flags & runtime knobs (admin toggleable)
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS settings (
    key         TEXT PRIMARY KEY,
    value       TEXT NOT NULL,
    updated_at  TEXT NOT NULL
);

-- ---------------------------------------------------------------------------
-- survey_responses: fully anonymous student feedback. No FK to users on
-- purpose — there is no link back to the responder, by design. Each row
-- is ONE answer to ONE question; a single submission produces N rows.
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS survey_responses (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    q_key       TEXT NOT NULL,
    answer      TEXT NOT NULL,
    created_at  TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_survey_responses_q_key ON survey_responses(q_key);
