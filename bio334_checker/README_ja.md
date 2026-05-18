# bio334-checker

**BIO334 Practical Bioinformatics** (チューリッヒ大学 2026-05-20 〜
2026-05-22) 用の LLM 補助つき演習チェッカー。

> **言語**: [English](README.md)（既定）· 日本語

ステータス: 2026 年版として feature complete。テスト 133/133 PASS。
演習 9 件登録済（Day 1 P1–3、Day 2 P1–5、Day 3 final）。admin が演習
ごとの公開可否を切替できるので、講義の進度に合わせて段階的に解放できる。

## 概要

学生は Python の解答を提出し、以下を受け取ります:

- **サンドボックス実行 + 出力比較**（決定論的な一段目）
- **LLM ルーブリック採点** + 暫定判定 + 段階的・ゲート付きヒント
  最大 3 段（concept → approach → code shape — リテラルな Python
  コードは絶対に出さない）
- **匿名のクラス進捗**（個人 + cohort median、5 名未満は中央値を抑制、
  メダル付き leaderboard はバランスを評価）
- **LLM 不一致の可視化**: 正解出力チェックと LLM ルーブリックが食い違う
  ときは UX バグではなく「LLM は間違える」という一級の教育シグナルとして
  表示
- **演習公開コントロール**: 講義が終わるまで該当の演習を学生から隠せる

裏側では、合格した提出ごとに KairosChain の不変アテステーションが
記録されます。チェーンブリッジは in-process のシングルトン worker と
冪等キーで動作し、チェーン障害は学生フローを絶対に止めません（SQLite
が source of truth）。

## スタック

- Python 3.10+、FastAPI + Jinja2 + 素 JS
- SQLite（1 ファイル、WAL モード）— コース 1 開催あたり 1 ファイル
- LLM バックエンド（`BIO334_LLM_BACKEND` で切替）:
  - `api` — Anthropic SDK 直接呼び出し（既定。`ANTHROPIC_API_KEY` 必要）
  - `bedrock` — Anthropic SDK を AWS Bedrock 経由で呼ぶ（AWS デプロイ推奨）
  - `claude-code` — `claude` CLI サブプロセス（dev / リハーサル専用。
    **本番講義では使わない** — 1 件ずつ直列化される）
- KairosChain は `KCClient` 抽象経由。既定の `LogKCClient` は JSONL の
  監査ログを追記し、コース後に reconciliation スクリプトで実チェーンに
  リプレイ

## クイックスタート（ローカル開発）

### 1. インストール

```bash
cd bio334_checker
pip install -e .
```

### 2. `.env` を作成

リポジトリルート（`bio334_checker/` の中ではなく**外側**）の
`.env.example` を `.env` にコピーして編集。最小 dev 構成:

```bash
BIO334_DB=/tmp/bio334_dryrun.db
BIO334_INSECURE_COOKIE=1
BIO334_ADMIN_USER=instructor
BIO334_ADMIN_PASS=tunnel
BIO334_LLM_BACKEND=claude-code
BIO334_CHAIN_LOG=/tmp/bio334_dryrun_chain.jsonl
BIO334_EXERCISE_FILES_DIR=/Users/<あなた>/.../bio334_2026_/bio334_checker/src/bio334_checker/data/exercise_files
```

`.env` は CLI 起動時にロードされます。読込順は `$BIO334_ENV_FILE` >
`.env.local` > `.env`。シェルで export された変数は常にファイル値より
優先されます。

### 3. DB 初期化と演習 import

```bash
bio334-checker init-db --db /tmp/bio334_dryrun.db
bio334-checker import-exercises \
  --db /tmp/bio334_dryrun.db \
  --data-dir src/bio334_checker/data/exercises
```

ローダーは**冪等**: 再実行しても変更のない演習は `[unchanged]`、
ルーブリック・正解出力・しきい値が変わったときだけ
`exercise_revisions` に新規行が書かれます。

### 4. サーバ起動

```bash
bio334-checker serve --db /tmp/bio334_dryrun.db --port 8334 --log-level warning
```

ブラウザで `http://127.0.0.1:8334/` にアクセス。`/admin` は
`BIO334_ADMIN_USER` / `BIO334_ADMIN_PASS` の basic auth です。

## 運用チートシート

### 起動 / 停止 / 再起動

```bash
# フォアグラウンド
bio334-checker serve --db /tmp/bio334_dryrun.db --port 8334 --log-level warning

# バックグラウンド
bio334-checker serve --db /tmp/bio334_dryrun.db --port 8334 --log-level warning &

# 停止
kill $(lsof -i :8334 -t)
```

### 演習を再 import（ルーブリック更新や新 yaml 追加時）

いつでも安全に実行可能（冪等）:

```bash
bio334-checker import-exercises \
  --db /tmp/bio334_dryrun.db \
  --data-dir src/bio334_checker/data/exercises
```

### 演習テーブルだけリセット（yaml から再構築、**学生と提出は残す**）

DB と yaml がズレてしまったので演習だけクリーンに作り直したいとき:

```bash
sqlite3 /tmp/bio334_dryrun.db \
  "DELETE FROM exercise_revisions; DELETE FROM exercises;"
bio334-checker import-exercises \
  --db /tmp/bio334_dryrun.db \
  --data-dir src/bio334_checker/data/exercises
```

### **全部**リセット（学生・提出・チェーン履歴ごと消す、完全初期化）

```bash
rm -f /tmp/bio334_dryrun.db /tmp/bio334_dryrun_chain.jsonl
bio334-checker init-db --db /tmp/bio334_dryrun.db
bio334-checker import-exercises \
  --db /tmp/bio334_dryrun.db \
  --data-dir src/bio334_checker/data/exercises
```

### 可視性を全部リセット（全演習を再公開）

`/admin/exercises` で「Show all」を押すか、SQL で直接:

```bash
sqlite3 /tmp/bio334_dryrun.db "UPDATE exercises SET visible_to_students = 1;"
```

### ヘルスチェック

```bash
curl -sS -w "code=%{http_code}\n" -o /dev/null http://127.0.0.1:8334/
sqlite3 /tmp/bio334_dryrun.db "SELECT COUNT(*) AS exercises, \
  SUM(visible_to_students) AS visible FROM exercises;"
```

### チェーン JSONL + DB をエクスポート（講師引き継ぎ用）

```bash
curl -u "$BIO334_ADMIN_USER:$BIO334_ADMIN_PASS" \
  http://127.0.0.1:8334/admin/export > bio334_2026_export.tar.gz
```

### コース後のチェーン reconciliation

```bash
bio334-checker chain-replay
# drain: retried=N graded=N still_pending=N failed=N
# chain: records_written=N attestations_written=N transient=N permanent=N
```

## LLM バックエンド

| バックエンド | 用途 | 認証 | 備考 |
|---|---|---|---|
| `claude-code` | ローカル開発、1 人のリハーサル | ログイン済 `claude` CLI | 1 grade あたりサブプロセス 5〜15s。直列化されるので**講義本番では使わない**。 |
| `api` | 本番（AWS 以外のホスト） | `ANTHROPIC_API_KEY` | 既定モデル `claude-sonnet-4-6`。`BIO334_LLM_MODEL` で上書き。 |
| `bedrock` | AWS 本番（推奨） | AWS 認証チェーン（EC2 上は IAM role、それ以外は `AWS_ACCESS_KEY_ID`+`AWS_SECRET_ACCESS_KEY` または `AWS_BEARER_TOKEN_BEDROCK`） | 既定モデル `us.anthropic.claude-sonnet-4-20250514-v1:0`。`BIO334_BEDROCK_MODEL` で上書き、`AWS_REGION` でリージョン指定。 |

### なぜ講義本番で `claude-code` を使わないか

20 名のピーク（提出スパイク時 ≈120 grades/hour）は CPU より先に
Claude アカウントの rate limit を踏みます。さらに 1 grade あたり
1〜3 秒のサブプロセス起動コストが乗ります。`llm_call.py:255` の
コメントに明記: *"Use for offline dev only; not for class."*

## AWS EC2 へのデプロイ

既存 EC2 インスタンスに `bio334-checker` を追加する想定。OS・nginx・
ドメインに合わせて適宜変更してください。

### A. EC2 + Bedrock 用 IAM role（推奨）

1. **IAM**: `bedrock:InvokeModel` 権限を持つ role を作成、信頼関係を
   `ec2.amazonaws.com` に、対象インスタンスへ Attach（EC2 →
   Instance → Security → Modify IAM role）。role が attach されると
   アプリは instance metadata service から自動で認証情報を取得します。
   環境変数にキーを書く必要はありません。
2. **Bedrock モデルアクセス有効化**: Bedrock Console → Model access
   → 使いたい Claude モデルを `AWS_REGION` のリージョンで request
   access。

### B. インスタンス側のアプリ設定

```bash
# 1. コード
sudo mkdir -p /srv/bio334 && sudo chown $USER /srv/bio334
cd /srv/bio334
git clone https://github.com/<your-org>/bio334_2026_ .
cd bio334_checker
python3 -m venv .venv
.venv/bin/pip install -e .

# 2. 専用サービスユーザとデータディレクトリ
sudo useradd -r -s /usr/sbin/nologin bio334
sudo mkdir -p /var/lib/bio334
sudo chown bio334:bio334 /var/lib/bio334

# 3. 本番 env file（root:bio334、mode 0640）
sudo install -m 0750 -o root -g bio334 -d /etc/bio334
sudo tee /etc/bio334/checker.env > /dev/null <<'EOF'
BIO334_DB=/var/lib/bio334/checker.db
BIO334_ADMIN_USER=instructor
BIO334_ADMIN_PASS=<生成: openssl rand -base64 24>
BIO334_LLM_BACKEND=bedrock
AWS_REGION=us-east-1
BIO334_BEDROCK_MODEL=us.anthropic.claude-sonnet-4-20250514-v1:0
BIO334_CHAIN_LOG=/var/lib/bio334/chain.jsonl
BIO334_EXERCISE_FILES_DIR=/srv/bio334/bio334_checker/src/bio334_checker/data/exercise_files
# BIO334_INSECURE_COOKIE は絶対に設定しない（本番は HTTPS 必須）
EOF
sudo chown root:bio334 /etc/bio334/checker.env
sudo chmod 0640 /etc/bio334/checker.env

# 4. DB 初期化と演習 import（サービスユーザで）
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
        # /admin は UZH ネットワークからのみ。実際の CIDR に置換してください。
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

### E. EC2 セキュリティグループ

- Inbound: 22 (SSH 制限つき)、80、443 のみ
- 8334 は**インターネット公開しない**。nginx が localhost からのみ
  プロキシ

### F. コース後のシャットダウン手順（推奨）

コースが終わり、チェーン replay + tarball エクスポートが済んだら、
checker をインターネット公開し続ける理由はありません。2 ステップ:

1. **GitHub Pages を停止**: リポジトリ Settings → Pages → Source を
   **None** に。静的登録ページが消えます。bookmark 済の FastAPI URL
   は引き続き動きますが、広い発見経路は閉じます。
2. **FastAPI サービスを停止**:
   ```bash
   ssh ec2
   sudo systemctl stop bio334-checker
   sudo systemctl disable bio334-checker   # 再起動時の自動起動を止める（任意）
   ```
   `/var/lib/bio334/` 配下の SQLite と chain JSONL は残るので、後日の
   reconciliation や監査作業はそのままできます。

**なぜこれが必要か**: `POST /register` は意図的に token なし（CSRF
保護はクラス内ツールなので scope 外）で、GitHub Pages ページに
FastAPI ホスト名がリテラル公開されるため、URL を見つけた誰でも叩け
ます。「コース期間中だけ public」がいちばん簡単な防御です。

再公開（来年度の開催など）するときは Pages を再有効化 + `systemctl
start bio334-checker` で復帰します。明示的にリセットしない限り DB
は持ち越されます。

### G. アップデート手順

```bash
ssh ec2
cd /srv/bio334
sudo systemctl stop bio334-checker
sudo systemctl enable bio334-checker
git pull origin main
sudo -u bio334 bio334_checker/.venv/bin/pip install -e bio334_checker --upgrade
# init-db は冪等で、既存 DB に schema migration を適用します。
sudo -u bio334 bio334_checker/.venv/bin/bio334-checker init-db \
  --db /var/lib/bio334/checker.db
sudo -u bio334 bio334_checker/.venv/bin/bio334-checker import-exercises \
  --db /var/lib/bio334/checker.db \
  --data-dir bio334_checker/src/bio334_checker/data/exercises
sudo systemctl start bio334-checker
```

## GitHub Pages 上の登録ページ（任意）

リポジトリルートの `docs/index.html` は単独で動く静的登録ページです。
GitHub Pages で公開すれば、FastAPI のホスト名が変わっても学生は安定
した URL から登録できます。

### 仕組み
- 静的ページにはフォームが 2 つ（Register / Already have a handle?）。
  どちらの `action` も本番 FastAPI ホストにハードコード。
- 学生が submit すると、ブラウザは通常のトップレベルナビゲーションで
  FastAPI ホストに POST します。セッション cookie は FastAPI ドメイン
  にセットされ、その後のリンク・ページ・API 呼び出しはすべて FastAPI
  上で完結します。GitHub Pages はこの 1 ページだけを所有します。
- CORS なし・AJAX なし・JS fetch なし — 素の HTML form POST のみ。
  cookie 設定が `SameSite=Lax` なので cross-site POST ナビゲーション
  でも FastAPI ドメインに cookie がセットされます。

### 有効化手順
1. リポジトリの Settings → Pages → Source を **main / docs** に。
   ページは `https://<user>.github.io/<repo>/` で公開されます。
2. `docs/index.html` の **1 行**（ファイル末尾近くの `BACKEND_URL`
   定数）を本番 FastAPI ホスト名に書き換える。両方のフォームは JS
   経由でこの 1 定数から `action` を構築するので、編集箇所はここだけ。
   プレースホルダのままだとフォーム上部に赤い警告が出るので見落とし
   にくくなっています。
3. commit + push。GitHub Pages が自動で取り込みます（〜30 秒）。

### 注意
静的ページは FastAPI のホスト名を**自動検知しません**。GitHub Pages
にはサーバーサイドテンプレートがないため、`BACKEND_URL` は HTML
ファイル中のリテラル文字列であり、デプロイ先が変わったら手で書き
換える必要があります。

### ローカル開発は無影響
静的ページは GitHub Pages 専用です。ローカルでは従来どおり
`http://127.0.0.1:8334/` にアクセスすると FastAPI の `landing.html`
が出ます。両方の入口は共存し、`POST /register` と `GET /?u=<handle>`
という同じバックエンドハンドラを共有します。

## 環境変数一覧

| 変数 | 必須 | 既定値 | 備考 |
|---|---|---|---|
| `BIO334_DB` | no | `./bio334_checker.db` | SQLite パス。本番は絶対パス推奨 |
| `BIO334_ADMIN_USER` | yes (admin) | — | `/admin*` の basic-auth ユーザ |
| `BIO334_ADMIN_PASS` | yes (admin) | — | env file 編集 + 再起動でローテ |
| `BIO334_LLM_BACKEND` | no | `api` | `api` / `bedrock` / `claude-code` |
| `BIO334_LLM_MODEL` | no | `claude-sonnet-4-6` | api バックエンドのモデル ID |
| `BIO334_BEDROCK_MODEL` | no | `us.anthropic.claude-sonnet-4-20250514-v1:0` | bedrock バックエンドのモデル ID |
| `ANTHROPIC_API_KEY` | yes (api) | — | |
| `AWS_REGION` | yes (bedrock) | `us-east-1` | `AWS_DEFAULT_REGION` も参照 |
| `AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY` | no | — | EC2 以外。EC2 上は IAM role 利用 |
| `AWS_BEARER_TOKEN_BEDROCK` | no | — | Bedrock API key (2025〜) |
| `BIO334_CHAIN_LOG` | no | `./chain.jsonl` | JSONL 監査ログのパス |
| `BIO334_CHAIN_BACKEND` | no | `log` | `log` / `null` |
| `BIO334_EXERCISE_FILES_DIR` | no | `./data/exercise_files` | 演習ごとのデータファイル |
| `BIO334_INSECURE_COOKIE` | no | unset | 平文 HTTP 開発時のみ `1`、**本番では絶対に設定しない** |
| `BIO334_ENV_FILE` | no | — | `.env` の明示的な上書きパス |

## ディレクトリ構成

```
bio334_checker/
├── README.md                           （英語版）
├── README_ja.md                        （このファイル）
├── docs/
│   └── ARCHITECTURE.md                 v0.3 — accepted design
├── pyproject.toml
├── src/bio334_checker/
│   ├── core/                           純粋ロジック（I/O 面なし）
│   ├── chain/                          KairosChain bridge + worker
│   ├── db/                             schema + migration
│   ├── interfaces/web/                 FastAPI app + Jinja2 templates
│   ├── data/exercises/                 演習 YAML 定義（9 件）
│   ├── data/exercise_files/            演習ごとのデータ（input.fa 等）
│   └── cli.py                          init-db / import-exercises / serve / chain-replay
└── tests/                              テスト 17 ファイル、133 件
```

## テスト

```bash
pytest tests/ -q
# 133 passed
```

## 教育的な仕掛け（意図的）

- **暫定判定バナー**: LLM の判定はすべて「間違えるかも、検証して」と
  毎回表示
- **不一致バナー**: 正解出力チェックと LLM ルーブリックが食い違うとき、
  どちらが正しいかは学生が考える。`expected_stdout` が null の演習では
  自動的に抑制（ルーブリックのみ採点）
- **typo-trap rescue**: passed かつ exact_match のときは「正解出力を
  もう一度ゆっくり読もう」 callout を表示。Day 1 Part 2 の意図的な
  typo が、速い学生にも見えるように
- **ヒントはゲート式**: 失敗 2 回 または 5 分以上の think time。
  3 段階（concept → approach → code shape）、**リテラル Python は
  絶対に出さない**
- **cognitive-debt のコピー**: hint-gate のページで「なぜゲートが
  あるか」を理由まで説明（ルールではなく rationale）
- **cohort median 抑制**: 5 名未満の演習では中央値を出さない（小規模
  cohort で個別特定を防ぐ）
- **display_name は絶対にチェーンに乗らない**: admin だけは
  `display_name (handle)` の対応を見て対面サポートできるが、それ以外
  （チェーン含む）は handle のみ
- **演習可視性**: 講義の進度に合わせて lecturer が解放（Hide all →
  Reveal up to Day N）

## ライセンス

MIT（コース教材全体に合わせて）。
