# bio334-checker — Architecture (Design Draft v0.1)

Status: DRAFT — pending multi-LLM review

## 1. Purpose

A web-based exercise checker for **BIO334 Practical Bioinformatics** (UZH, 2026-05-20 to 2026-05-22). Students submit Python solutions, receive LLM-graded feedback with hints, and progress is recorded immutably on a KairosChain instance for post-course attestation and showcase.

Replaces a 2022-era Rails-based syntax+exact-match checker (`exercise_checker_sushi_rails_base_20220519`) with an LLM-augmented design.

## 2. Design Invariants

The system **must** satisfy the following (review against these):

- **I-AUTH-1**: A returning student is identified by handle alone. No password, no email, no PII required.
- **I-AUTH-2**: Handle issuance is irreversible: handles are not recovered, only re-issued. Lost handle = new identity.
- **I-PRIV-1**: Class-wide progress views expose aggregate counts and (optionally) display_name, never source code or per-handle correctness traces to other students.
- **I-GRADE-1**: Every accepted (passing) submission has executed in the sandbox AND been judged by the LLM rubric. Neither alone qualifies.
- **I-GRADE-2**: Grader output is reproducible enough that the same `(source_code, exercise_definition, grader_version)` produces a stable verdict for the purpose of audit, but is not required to be byte-identical (LLM nondeterminism acknowledged).
- **I-CHAIN-1**: Every passing submission produces exactly one chain record and one attestation. Failures are recorded but do not produce attestations.
- **I-CHAIN-2**: Chain operations are advisory to the user-facing flow: a chain failure must not block grading or block the student's progress in the local DB. Reconciliation runs out of band.
- **I-LLM-1**: Backend selection is runtime-switchable (`api` ↔ `claude-code` subprocess) without code change, only configuration.
- **I-RATE-1**: Handle-guessing is bounded by IP rate limit. The bound is independent of handle length.
- **I-OFFLINE-1**: The system runs without external network for Anthropic API mode if a local Claude Code subprocess is available; for KairosChain, all writes are local-first.
- **I-DELETE-1**: A student can request deletion of their submissions. Chain records are immutable but their handle can be tombstoned (handle → `deleted` marker, all submissions unlinked).

## 3. Component Boundaries

```
                    ┌────────────────────────────────────────┐
                    │              Browser (Student)         │
                    │  - Register form                       │
                    │  - Exercise list / detail              │
                    │  - Submit + view result + hints        │
                    │  - Class progress dashboard (anon)     │
                    └──────────────┬─────────────────────────┘
                                   │ HTTPS / cookies (handle in localStorage)
                                   ▼
        ┌──────────────────────────────────────────────────────┐
        │              FastAPI app (bio334_checker)            │
        │                                                      │
        │  routes/      auth/      grader/      progress/      │
        │  (HTTP)       (handle)   (2-stage)    (aggregate)    │
        │                                                      │
        │       ▼                ▼                ▼            │
        │   sandbox.py       chat.py          chain/            │
        │   (subprocess)     (LLM call)       (KC bridge)       │
        └────────┬──────────────┬───────────────┬───────────────┘
                 │              │               │
                 ▼              ▼               ▼
            python3        Claude API /    KairosChain MCP
            subprocess     Claude Code     (chain_record,
            (sandboxed)    subprocess      attestation_issue)
                                              ▲
                 ┌────────────────┐            │
                 │   SQLite DB    │            │
                 │   (local fs)   │            │
                 └────────────────┘    KairosChain instance
                                       (separate process,
                                        same host or remote)
```

Component contracts:

- `auth`: pure functions on (handle ↔ user_row). No I/O outside DB.
- `grader`: pure-by-value given (source, exercise_def, llm_response). Side effects pushed to caller.
- `chain/`: all KairosChain calls go through this module. Failures are caught and logged; never propagated as user-facing errors.
- `sandbox`: subprocess-isolated, time/memory/output capped. Imported from `bio334-teaching` reference (or vendored copy).

## 4. Data Model

SQLite. Schema (DDL-equivalent, normative):

```
users(
  handle          TEXT PRIMARY KEY,        -- 4 chars, alphabet pool below
  display_name    TEXT NOT NULL,           -- not used for auth, free-form
  created_at      TEXT NOT NULL,
  last_seen_at    TEXT NOT NULL,
  tombstoned_at   TEXT NULL                -- for I-DELETE-1
)

exercises(
  slug            TEXT PRIMARY KEY,        -- e.g. "day1_p1_ex1"
  title           TEXT NOT NULL,
  day             INTEGER NOT NULL,        -- 1, 2, 3
  part            INTEGER NOT NULL,
  order_index     INTEGER NOT NULL,
  description_md  TEXT NOT NULL,           -- shown to student
  expected_stdout TEXT NULL,               -- for exact-match stage
  argv            TEXT NULL,               -- JSON array
  files_provided  TEXT NULL,               -- JSON array of input file paths
  rubric_md       TEXT NOT NULL,           -- for LLM grading stage
  max_score       INTEGER NOT NULL DEFAULT 100,
  pass_threshold  INTEGER NOT NULL DEFAULT 70,
  source_gist_url TEXT NULL                -- audit trail
)

submissions(
  id              INTEGER PRIMARY KEY AUTOINCREMENT,
  user_handle     TEXT NOT NULL REFERENCES users(handle),
  exercise_slug   TEXT NOT NULL REFERENCES exercises(slug),
  source_code     TEXT NOT NULL,
  sandbox_stdout  TEXT NULL,
  sandbox_stderr  TEXT NULL,
  sandbox_rc      INTEGER NULL,
  exact_match     INTEGER NOT NULL,        -- 0/1 for stage-1 result
  llm_score       INTEGER NULL,            -- 0..max_score, stage-2 result
  llm_feedback_md TEXT NULL,
  passed          INTEGER NOT NULL,        -- 0/1, derived from both stages
  chain_block_ref TEXT NULL,               -- KairosChain block id, NULL if write pending/failed
  attestation_id  TEXT NULL,               -- NULL until attestation issued
  created_at      TEXT NOT NULL,
  grader_version  TEXT NOT NULL            -- for I-GRADE-2 reproducibility
)

events(
  id              INTEGER PRIMARY KEY AUTOINCREMENT,
  ip              TEXT NOT NULL,
  handle          TEXT NULL,               -- nullable; pre-auth events have no handle
  event_type      TEXT NOT NULL,           -- register, login_fail, submit, rate_limited, ...
  detail_json     TEXT NULL,
  created_at      TEXT NOT NULL
)

rate_limits(
  ip              TEXT NOT NULL,
  bucket          TEXT NOT NULL,           -- "login_fail", "submit", ...
  count           INTEGER NOT NULL,
  window_start    TEXT NOT NULL,
  PRIMARY KEY (ip, bucket)
)
```

Indexes: `submissions(user_handle, exercise_slug)`, `submissions(exercise_slug, passed)`, `events(created_at)`.

## 5. Handle Issuance

Alphabet pool (31 chars, ambiguous chars excluded):
```
a b c d e f g h j k m n p q r s t u v w x y z 2 3 4 5 6 7 8 9
```

Length: 4. Pool size 31⁴ ≈ 924,000. For ≤30 active users, collision probability per registration < 0.005% (with retry-on-collision: zero).

Registration flow:
1. Student submits `display_name` (free text, ≤32 chars, sanitized).
2. Server generates random handle from alphabet pool.
3. If handle collides in `users`, regenerate (loop bounded at 8 attempts; fail closed if exhausted — should never happen for class size ≤30).
4. Insert row, return handle to client.
5. Client renders: handle text + QR code (data URL of `https://<host>/?u=<handle>`) + clickable link.
6. Client stores handle in `localStorage` under key `bio334_handle`.

Login flow:
1. Client sends handle (from URL `?u=` or localStorage or manual entry).
2. Server validates handle exists and is not tombstoned.
3. On valid: set `last_seen_at`, return user row. On invalid: increment `rate_limits` for `login_fail`, log event, return 401.
4. Rate limit: `login_fail` bucket — 5 attempts per IP per 60s, then 600s lockout.

## 6. Grading Pipeline

Two-stage grader. Pseudocode:

```
def grade(submission, exercise) -> GradeResult:
    # Stage 1: sandbox exec + exact match (cheap, deterministic)
    exec_result = sandbox.run(submission.source_code, argv=exercise.argv,
                              files=exercise.files_provided,
                              timeout=10s, mem_cap=256MB)
    exact_match = (exercise.expected_stdout is not None
                   and exec_result.stdout.strip() == exercise.expected_stdout.strip())

    # Early reject: code did not run cleanly
    if exec_result.return_code != 0 and not exercise.allow_nonzero_rc:
        return GradeResult(passed=False, llm_score=None,
                           feedback="Code did not execute cleanly. " + stderr_excerpt)

    # Stage 2: LLM rubric grading
    llm_response = llm.grade(
        rubric_md=exercise.rubric_md,
        student_code=submission.source_code,
        sandbox_output=exec_result.stdout,
        expected_output=exercise.expected_stdout,
    )
    # llm_response: { score: int, feedback_md: str, hints: list[str] }

    passed = (exact_match or llm_response.score >= exercise.pass_threshold)

    return GradeResult(
        exact_match=exact_match,
        llm_score=llm_response.score,
        feedback=llm_response.feedback_md,
        passed=passed,
        grader_version=GRADER_VERSION,
    )
```

LLM grading prompt is templated (`grader/prompts/rubric_v1.md`) and version-stamped via `grader_version` for reproducibility (I-GRADE-2).

The grader is the sole writer of `submissions` rows. The chain bridge subscribes to "submission inserted" events and performs `chain_record` / `attestation_issue` asynchronously.

## 7. KairosChain Integration

All writes via the `chain/` module, which wraps the kairos-chain MCP tools. Events:

| Trigger | KC tool | Payload (essentials) |
|---|---|---|
| User registered | `chain_record` | `{type: "user_register", handle, display_name, ts}` |
| Submission stored (any) | `chain_record` | `{type: "submission", handle, exercise_slug, passed, llm_score, grader_version, ts}` |
| Submission passed | `attestation_issue` | `{subject: handle, claim: "completed", exercise_slug, score, ts}` |
| Course end (manual) | `chain_export` | full history snapshot |
| Grader prompt set updated | `formalization_record` | rubric and prompt template changes |

Asynchrony: chain writes happen in a background worker (asyncio task) reading from a local queue. Worker retries on transient failure. `chain_block_ref` and `attestation_id` columns are populated when writes succeed; remain NULL otherwise. Reconciliation script can replay queued items.

Failure mode: if KairosChain is unreachable for the entire session, the local SQLite is the source of truth and no student-facing functionality is degraded (I-CHAIN-2). Post-hoc replay populates the chain.

## 8. LLM Backend Switching

`llm.py` exports a single `grade()` function with two implementations selected by config:

| Config | Backend | Use case |
|---|---|---|
| `BIO334_LLM_BACKEND=api` | Anthropic SDK direct call, model `claude-opus-4-7` | Production (live class) |
| `BIO334_LLM_BACKEND=claude-code` | Subprocess `claude -p '<prompt>' --output-format json` | Local testing without API key |

Both implementations conform to the same input/output shape. Existing `bio334-teaching/core/chat.py` already implements this pattern; we vendor or import the relevant code.

Concurrency: Anthropic API mode supports concurrent requests up to provider rate limits. Claude Code subprocess is serialized per invocation; for class-scale (30 students × ~12 exercises = up to ~30 concurrent submissions in worst case), API mode is required for production.

## 9. Web UI

Minimal FastAPI + Jinja2 + vanilla JS (no SPA framework). Routes:

| Route | Method | Auth | Purpose |
|---|---|---|---|
| `/` | GET | none | Landing: register or enter handle |
| `/register` | POST | none | Issue handle |
| `/me` | GET | handle | Student's own progress |
| `/exercises` | GET | handle | List, filtered by day |
| `/exercises/{slug}` | GET | handle | Detail + submission form |
| `/submit` | POST | handle | Submit code, grade, return result |
| `/dashboard` | GET | handle | Anonymized class progress |
| `/admin` | GET | basic-auth (instructor) | Live heat map, per-exercise stats |
| `/admin/export` | GET | basic-auth | Dump SQLite + chain export |

Instructor admin auth is a separate environment-variable-set credential (single instructor user), out of scope for the handle system.

## 10. Concurrency & Performance Targets

- Concurrent students: 30
- Concurrent submissions: ≤30 (one per student, peak)
- p95 grading latency: ≤8s (Anthropic API mode, single LLM call per submission)
- Sandbox exec timeout: 10s (hard cap)
- Total LLM cost per session per student: ≤$0.50 estimated (≈12 submissions × Opus 4.7 grading prompt)

If costs are a concern, Sonnet 4.6 can be used for grading with a config switch. Grader prompt is model-agnostic.

## 11. Out of Scope (this phase)

- Public deployment / multi-tenant. Single instance, single course.
- Plagiarism detection. (Class is small; instructor reviews exports manually if needed.)
- Cross-course reuse. Exercise definitions are BIO334-specific YAML.
- Real-time collaboration / pair programming.
- Mobile-first UI. (Desktop browser primary; mobile must work for QR scan and read-only views.)

## 12. Open Questions for Multi-LLM Review

Reviewers, please pressure-test the following:

- **Q1**: Is the handle scheme (4 chars, 31-char pool, no password, IP rate limit) appropriate for a 30-student 3-day course? Where does it break? Threat model: a student wants to (a) impersonate another student to mark exercises as complete, (b) flood the system, (c) extract another student's code.
- **Q2**: Is the grader two-stage design (exact match OR LLM score ≥ threshold → passed) coherent? Should both be required, or is OR sufficient? What happens for exercises where there is no canonical expected output (e.g., creative tasks)?
- **Q3**: Are the chain integration boundaries (I-CHAIN-1/2) drawn at the right place? Is async-with-reconciliation the right pattern, or should chain writes be synchronous-but-allow-failure?
- **Q4**: Is the LLM backend abstraction sound for swapping API ↔ Claude Code at runtime? Are there hidden incompatibilities (streaming, tool use, system prompts)?
- **Q5**: Reproducibility (I-GRADE-2): is `grader_version` + prompt template + LLM model ID enough to audit a verdict, given LLM nondeterminism? Should we also store the LLM raw response?
- **Q6**: Is the data model normalization appropriate, or should we denormalize for read-heavy dashboard queries? What's the indexing strategy for the per-exercise heat map?
- **Q7**: For the showcase / publish goal, what additional KairosChain features (`skills_evolve`, `dream_propose`, `multi_llm_review`) should be threaded through to make this a richer demonstration, vs. keeping the system simple?
- **Q8**: Privacy — is the design tight enough that a student cannot enumerate other handles, see other students' code, or correlate display_name with submission patterns?

## 13. Phasing (proposed, subject to review)

| Phase | Deliverable | Days |
|---|---|---|
| 0 | Repo skeleton, pyproject, SQLite schema, vendored sandbox | 0.5 |
| 1 | Auth (handle issuance, QR/link, rate limit), `/register` `/login` | 0.5 |
| 2 | Exercise YAML loader, problems fetched from gist URLs, list/detail views | 0.5 |
| 3 | Two-stage grader, `/submit`, LLM backend abstraction | 1.5 |
| 4 | Student progress + class dashboard (anon) | 1.0 |
| 5 | KairosChain integration (chain_record, attestation_issue, async worker) | 1.0 |
| 6 | Instructor admin, integration tests, all 12 day1 exercises wired | 1.0 |
| 7 | Day2/3 exercises, README, ARCHITECTURE update, demo dry-run | 0.5 |

Total: 6.0 working days. MVP after Phase 3, showcase-complete after Phase 5.
