# bio334-checker

LLM-augmented exercise checker for **BIO334 Practical Bioinformatics**
(University of Zurich, 2026-05-20 – 2026-05-22).

> **Language**: English (default) · [日本語](README_ja.md)

Status: feature-complete for the 2026 offering. 133/133 tests pass. 9
exercises registered (Day 1 P1–3, Day 2 P1–5, Day 3 final). Admin can
toggle per-exercise visibility to pace the lecture.

## What the system does

Students submit Python solutions to course exercises and receive:

- **Sandbox execution** with output comparison (deterministic stage).
- **LLM rubric grading** with a provisional verdict and at most three
  progressive, *gated* hints (concept → approach → code shape; never
  literal Python).
- **Anonymous class-wide progress** (personal status + cohort median;
  median suppressed below 5 distinct submitters; leaderboard with
  breadth-rewarding medals).
- **Disagreement surfacing** when the canonical-output check and the
  LLM rubric disagree — treated as a first-class teaching signal
  about LLM limits, not a UX glitch.
- **Per-exercise visibility control** so the instructor can hide
  later-day exercises until they have been taught.

Behind the scenes, every passing submission is recorded on a KairosChain
instance as an immutable attestation. The chain bridge runs as a
singleton in-process worker with idempotency keys; chain failures never
block the student-facing flow (SQLite is the source of truth).

## Stack

- Python 3.10+, FastAPI + Jinja2 + vanilla JS
- SQLite (single file, WAL mode) — one file per course offering
- LLM backends (toggled by `BIO334_LLM_BACKEND`):
  - `api` — Anthropic SDK direct (default; needs `ANTHROPIC_API_KEY`)
  - `bedrock` — Anthropic SDK via AWS Bedrock (recommended for AWS deploys)
  - `claude-code` — `claude` CLI subprocess (dev / rehearsal only, **not for class** — serialized per invocation)
- KairosChain via a `KCClient` abstraction; the default `LogKCClient`
  appends a JSONL audit log that the post-course reconciliation script
  replays onto the actual chain

## Quick start (local dev)

### 1. Install

```bash
cd bio334_checker
pip install -e .
```

### 2. Create `.env`

Copy `.env.example` (at the repo root, **not** inside `bio334_checker/`)
to `.env` and edit. Minimal dev config:

```bash
BIO334_DB=/tmp/bio334_dryrun.db
BIO334_INSECURE_COOKIE=1
BIO334_ADMIN_USER=instructor
BIO334_ADMIN_PASS=tunnel
BIO334_LLM_BACKEND=claude-code
BIO334_CHAIN_LOG=/tmp/bio334_dryrun_chain.jsonl
BIO334_EXERCISE_FILES_DIR=/Users/<you>/.../bio334_2026_/bio334_checker/src/bio334_checker/data/exercise_files
```

`.env` is loaded at CLI startup; lookup order is
`$BIO334_ENV_FILE` > `.env.local` > `.env`. Shell-exported variables
always override file values.

### 3. Initialize the DB and load exercises

```bash
bio334-checker init-db --db /tmp/bio334_dryrun.db
bio334-checker import-exercises \
  --db /tmp/bio334_dryrun.db \
  --data-dir src/bio334_checker/data/exercises
```

The loader is **idempotent**: re-running it leaves untouched exercises
as `[unchanged]` and only writes a new `exercise_revisions` row when
the rubric, expected output, or threshold changes.

### 4. Serve

```bash
bio334-checker serve --db /tmp/bio334_dryrun.db --port 8334 --log-level warning
```

Visit `http://127.0.0.1:8334/`. Admin lives at `/admin` with basic
auth from `BIO334_ADMIN_USER` / `BIO334_ADMIN_PASS`.

## Operating cheatsheet

### Start / stop / restart

```bash
# foreground
bio334-checker serve --db /tmp/bio334_dryrun.db --port 8334 --log-level warning

# background
bio334-checker serve --db /tmp/bio334_dryrun.db --port 8334 --log-level warning &

# stop
kill $(lsof -i :8334 -t)
```

### Re-import exercises (refresh rubric / add new yamls)

Safe to run anytime; idempotent.

```bash
bio334-checker import-exercises \
  --db /tmp/bio334_dryrun.db \
  --data-dir src/bio334_checker/data/exercises
```

### Reset the exercises table (full wipe, reload from yaml)

If the DB diverges from the on-disk yamls and you want a clean start
**without losing students and submissions**:

```bash
sqlite3 /tmp/bio334_dryrun.db \
  "DELETE FROM exercise_revisions; DELETE FROM exercises;"
bio334-checker import-exercises \
  --db /tmp/bio334_dryrun.db \
  --data-dir src/bio334_checker/data/exercises
```

If you want to wipe **everything** (start from zero — clears
students, submissions, chain log, etc.):

```bash
rm -f /tmp/bio334_dryrun.db /tmp/bio334_dryrun_chain.jsonl
bio334-checker init-db --db /tmp/bio334_dryrun.db
bio334-checker import-exercises \
  --db /tmp/bio334_dryrun.db \
  --data-dir src/bio334_checker/data/exercises
```

### Reset visibility (show everything again)

Either click "Show all" at `/admin/exercises`, or:

```bash
sqlite3 /tmp/bio334_dryrun.db "UPDATE exercises SET visible_to_students = 1;"
```

### Quick health check

```bash
curl -sS -w "code=%{http_code}\n" -o /dev/null http://127.0.0.1:8334/
sqlite3 /tmp/bio334_dryrun.db "SELECT COUNT(*) AS exercises, \
  SUM(visible_to_students) AS visible FROM exercises;"
```

### Export the chain log + DB (instructor handoff)

```bash
curl -u "$BIO334_ADMIN_USER:$BIO334_ADMIN_PASS" \
  http://127.0.0.1:8334/admin/export > bio334_2026_export.tar.gz
```

### Post-course chain reconciliation

```bash
bio334-checker chain-replay
# drain: retried=N graded=N still_pending=N failed=N
# chain: records_written=N attestations_written=N transient=N permanent=N
```

## LLM backends

| Backend | When to use | Auth | Notes |
|---|---|---|---|
| `claude-code` | local dev, single-user rehearsal | logged-in `claude` CLI | Each grade spawns a subprocess (5–15s). Serialized; do NOT use for class. |
| `api` | production, non-AWS host | `ANTHROPIC_API_KEY` | Default model `claude-sonnet-4-6`. Override via `BIO334_LLM_MODEL`. |
| `bedrock` | production on AWS (recommended) | AWS credential chain (IAM role on EC2; otherwise `AWS_ACCESS_KEY_ID`+`AWS_SECRET_ACCESS_KEY` or `AWS_BEARER_TOKEN_BEDROCK`) | Default model `us.anthropic.claude-sonnet-4-20250514-v1:0`. Override via `BIO334_BEDROCK_MODEL`. Region via `AWS_REGION`. |

### Why not `claude-code` for class

The 20-student peak (≈120 grades/hour during a submission spike) hits
Claude account rate limits well before it hits compute, and each
grade pays a 1–3 s subprocess-startup overhead. The code comment in
`llm_call.py:255` says it explicitly: *"Use for offline dev only; not
for class."*

## Deploying to AWS EC2

This section assumes you already have a running EC2 instance and want
to add `bio334-checker` to it. Adapt to your OS / nginx / domain.

### A. EC2 + IAM role for Bedrock (recommended)

1. **IAM**: create a role with `bedrock:InvokeModel` permission,
   trust relationship `ec2.amazonaws.com`, and attach it to the
   instance (EC2 → Instance → Security → Modify IAM role). With the
   role attached, the app gets credentials from the instance metadata
   service automatically — no keys in env.
2. **Enable Bedrock models**: Bedrock Console → Model access → request
   access to the Claude models you want, in the region matching
   `AWS_REGION`.

### B. Application setup on the instance

```bash
# 1. Code
sudo mkdir -p /srv/bio334 && sudo chown $USER /srv/bio334
cd /srv/bio334
git clone https://github.com/<your-org>/bio334_2026_ .
cd bio334_checker
python3 -m venv .venv
.venv/bin/pip install -e .

# 2. Dedicated service user + data dir
sudo useradd -r -s /usr/sbin/nologin bio334
sudo mkdir -p /var/lib/bio334
sudo chown bio334:bio334 /var/lib/bio334

# 3. Production env file (root:bio334, mode 0640)
sudo install -m 0750 -o root -g bio334 -d /etc/bio334
sudo tee /etc/bio334/checker.env > /dev/null <<'EOF'
BIO334_DB=/var/lib/bio334/checker.db
BIO334_ADMIN_USER=instructor
BIO334_ADMIN_PASS=<generate: openssl rand -base64 24>
BIO334_LLM_BACKEND=bedrock
AWS_REGION=us-east-1
BIO334_BEDROCK_MODEL=us.anthropic.claude-sonnet-4-20250514-v1:0
BIO334_CHAIN_LOG=/var/lib/bio334/chain.jsonl
BIO334_EXERCISE_FILES_DIR=/srv/bio334/bio334_checker/src/bio334_checker/data/exercise_files
# Do NOT set BIO334_INSECURE_COOKIE — HTTPS is mandatory in production.
EOF
sudo chown root:bio334 /etc/bio334/checker.env
sudo chmod 0640 /etc/bio334/checker.env

# 4. Initialize DB and load exercises (under the service user)
sudo -u bio334 /srv/bio334/bio334_checker/.venv/bin/bio334-checker \
  init-db --db /var/lib/bio334/checker.db
sudo -u bio334 /srv/bio334/bio334_checker/.venv/bin/bio334-checker \
  import-exercises --db /var/lib/bio334/checker.db \
  --data-dir /srv/bio334/bio334_checker/src/bio334_checker/data/exercises
```

### C. systemd unit

`/etc/systemd/system/bio334-checker.service`:

```ini
[Unit]
Description=bio334 exercise checker
After=network.target

[Service]
Type=simple
User=bio334
Group=bio334
WorkingDirectory=/srv/bio334/bio334_checker
EnvironmentFile=/etc/bio334/checker.env
ExecStart=/srv/bio334/bio334_checker/.venv/bin/bio334-checker serve \
  --db /var/lib/bio334/checker.db --port 8334 --log-level info
Restart=on-failure
RestartSec=5

NoNewPrivileges=true
ProtectSystem=strict
ProtectHome=true
PrivateTmp=true
ReadWritePaths=/var/lib/bio334

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now bio334-checker
sudo journalctl -u bio334-checker -f
```

### D. nginx + HTTPS

`/etc/nginx/sites-available/bio334`:

```nginx
server {
    listen 80;
    server_name bio334.example.uzh.ch;
    location / { return 301 https://$host$request_uri; }
}

server {
    listen 443 ssl http2;
    server_name bio334.example.uzh.ch;

    ssl_certificate     /etc/letsencrypt/live/bio334.example.uzh.ch/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/bio334.example.uzh.ch/privkey.pem;

    location /admin {
        # Keep /admin on UZH networks only; adjust to your CIDRs.
        allow 130.60.0.0/16;
        deny all;
        proxy_pass http://127.0.0.1:8334;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto https;
    }

    location / {
        proxy_pass http://127.0.0.1:8334;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto https;
    }

    client_max_body_size 256k;
}
```

```bash
sudo ln -s /etc/nginx/sites-available/bio334 /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl reload nginx
sudo certbot --nginx -d bio334.example.uzh.ch
```

### E. EC2 Security Group

- Inbound: 22 (SSH, restricted), 80, 443. Nothing else.
- 8334 is **not** opened to the public; nginx talks to it from
  localhost only.

### F. Post-course shutdown (recommended)

Once the course is over and the chain has been replayed and the
tarball exported, the checker has no reason to stay reachable from the
internet. Two simple steps:

1. **Disable GitHub Pages**: repo Settings → Pages → Source: **None**.
   The static registration page disappears. Bookmarked FastAPI URLs
   still work, but the wider discoverability path is closed.
2. **Stop the FastAPI service**:
   ```bash
   ssh ec2
   sudo systemctl stop bio334-checker
   sudo systemctl disable bio334-checker   # optional: don't auto-start on reboot
   ```
   The on-disk SQLite + chain JSONL stay put under `/var/lib/bio334/`
   for any later reconciliation or audit work.

Why this matters: `POST /register` is intentionally token-less (no
CSRF protection — out of scope for a class-internal tool) and the
GitHub Pages page exposes the FastAPI hostname publicly, so anyone
who finds the URL can hit it. The course-window-only public exposure
is the simplest defense.

To bring it back later (e.g., next year's offering): re-enable Pages
and `systemctl start bio334-checker`. The DB carries forward unless
you explicitly reset it.

### G. Update workflow

```bash
ssh ec2
cd /srv/bio334
sudo systemctl stop bio334-checker
sudo systemctl enable bio334-checker
git pull origin main
sudo -u bio334 bio334_checker/.venv/bin/pip install -e bio334_checker --upgrade
# init-db is idempotent and runs schema migrations onto an existing DB.
sudo -u bio334 bio334_checker/.venv/bin/bio334-checker init-db \
  --db /var/lib/bio334/checker.db
sudo -u bio334 bio334_checker/.venv/bin/bio334-checker import-exercises \
  --db /var/lib/bio334/checker.db \
  --data-dir bio334_checker/src/bio334_checker/data/exercises
sudo systemctl start bio334-checker
```

## GitHub Pages registration page (optional)

`docs/index.html` at the repo root is a self-contained static
registration page that can be hosted on GitHub Pages so students can
register from a stable URL even if the FastAPI host changes.

### How it works
- The static page contains two HTML forms (Register / Already have a
  handle?) whose `action` is hardcoded to the production FastAPI host.
- On submit, the browser performs a normal top-level navigation to
  the FastAPI host. The session cookie is set on that host's domain,
  and from then on every link / page / API call lives on FastAPI.
  GitHub Pages owns only this one page.
- No CORS, no AJAX, no JS-driven fetch — just plain HTML form POST.
  The cookie config `SameSite=Lax` permits cross-site POST navigation
  to set the cookie on the FastAPI domain.

### Enabling
1. Settings → Pages → Source: **main / docs**. The page becomes
   reachable at `https://<user>.github.io/<repo>/`.
2. Edit **one line** in `docs/index.html` — the `BACKEND_URL`
   constant near the bottom of the file — to point at the production
   FastAPI hostname. Both forms read from that single constant via JS.
   If the placeholder is left in place a red warning surfaces above
   the form so you cannot miss it.
3. Commit + push. GitHub Pages picks it up automatically (~30 s).

### Note
The static page does not auto-detect the FastAPI host. There is no
server-side templating on GitHub Pages — `BACKEND_URL` is a literal
string in the HTML file and must be edited manually when the
deployment host changes.

### Local dev is unaffected
The static page is for GitHub Pages only. Locally you still hit
`http://127.0.0.1:8334/` which serves the FastAPI `landing.html`. The
two entry points coexist; they share the same `POST /register` and
`GET /?u=<handle>` backend handlers.

## Environment variables

| Variable | Required | Default | Notes |
|---|---|---|---|
| `BIO334_DB` | no | `./bio334_checker.db` | SQLite path; absolute path recommended |
| `BIO334_ADMIN_USER` | yes (admin) | — | basic-auth user for `/admin*` |
| `BIO334_ADMIN_PASS` | yes (admin) | — | rotated by editing the env file + restart |
| `BIO334_LLM_BACKEND` | no | `api` | `api` / `bedrock` / `claude-code` |
| `BIO334_LLM_MODEL` | no | `claude-sonnet-4-6` | api backend model id |
| `BIO334_BEDROCK_MODEL` | no | `us.anthropic.claude-sonnet-4-20250514-v1:0` | bedrock backend model id |
| `ANTHROPIC_API_KEY` | yes (api backend) | — | |
| `AWS_REGION` | yes (bedrock) | `us-east-1` | also reads `AWS_DEFAULT_REGION` |
| `AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY` | no | — | only off-EC2; on EC2 use an IAM role |
| `AWS_BEARER_TOKEN_BEDROCK` | no | — | Bedrock API key (2025+) |
| `BIO334_CHAIN_LOG` | no | `./chain.jsonl` | JSONL audit log path |
| `BIO334_CHAIN_BACKEND` | no | `log` | `log` / `null` |
| `BIO334_EXERCISE_FILES_DIR` | no | `./data/exercise_files` | per-exercise data files |
| `BIO334_INSECURE_COOKIE` | no | unset | set to `1` for plain-HTTP dev; **never in production** |
| `BIO334_ENV_FILE` | no | — | explicit `.env` override path |

## Layout

```
bio334_checker/
├── README.md                           (this file)
├── README_ja.md                        (Japanese version)
├── docs/
│   └── ARCHITECTURE.md                 v0.3 — accepted design
├── pyproject.toml
├── src/bio334_checker/
│   ├── core/                           pure logic (no I/O surfaces)
│   ├── chain/                          KairosChain bridge + worker
│   ├── db/                             schema + migration
│   ├── interfaces/web/                 FastAPI app + Jinja2 templates
│   ├── data/exercises/                 YAML exercise definitions (9)
│   ├── data/exercise_files/            per-exercise data (input.fa etc.)
│   └── cli.py                          init-db / import-exercises / serve / chain-replay
└── tests/                              17 test files, 133 tests
```

## Testing

```bash
pytest tests/ -q
# 133 passed
```

## Pedagogy hooks (deliberate)

- **Provisional verdict banner** on every LLM result: *may be wrong; investigate.*
- **Disagreement banner** when canonical-output and LLM rubric
  disagree — students are explicitly invited to figure out which side
  is right. Suppressed when `expected_stdout` is null (rubric-only grading).
- **Typo-trap rescue**: when a submission passes AND matches the
  canonical exactly, a "read the canonical once more, slowly"
  callout appears, so the Day 1 Part 2 deliberate typo is still
  visible to fast students.
- **Hints are gated**: ≥ 2 failed submissions OR ≥ 5 minutes of think
  time. Three progressive levels (concept → approach → code shape);
  never literal compilable Python.
- **Cognitive-debt copy** on hint-gate page explains *why* the gate
  exists, not just *that* it exists.
- **Cohort median is suppressed** for exercises with fewer than 5
  submitters (avoids identifying tail students).
- **`display_name` never on chain.** Admin sees `display_name (handle)`
  for the in-person help loop; everyone else, including the chain,
  sees only the handle.
- **Per-exercise visibility**: lecturer reveals exercises as the
  lecture proceeds (Hide all → Reveal up to Day N).

## License

MIT (matches surrounding course materials).
