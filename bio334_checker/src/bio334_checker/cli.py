"""bio334-checker CLI entry point.

Phase 0 wires only ``init-db`` and ``version``. Other subcommands
(``serve``, ``import-exercises``, ``chain-replay``) land in later phases.
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from bio334_checker import __version__
from bio334_checker.db.connection import DEFAULT_DB_PATH, connect, init_db


def _load_dotenv(path: Path) -> int:
    """Minimal .env loader. Reads KEY=VALUE lines (with optional `export `
    prefix and surrounding single/double quotes); skips blank lines and
    `#` comments. Does NOT overwrite variables already present in the
    environment, so an explicit shell export always wins. Returns the
    number of variables newly set."""
    if not path.is_file():
        return 0
    set_count = 0
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[len("export "):].lstrip()
        if "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in ("'", '"'):
            value = value[1:-1]
        if not key or key in os.environ:
            continue
        os.environ[key] = value
        set_count += 1
    return set_count


def _cmd_init_db(args: argparse.Namespace) -> int:
    path = init_db(Path(args.db) if args.db else None)
    print(f"Initialized SQLite schema at {path}")
    return 0


def _cmd_import_exercises(args: argparse.Namespace) -> int:
    """Load YAML exercise definitions and upsert into DB (idempotent).

    A new ``exercise_revisions`` row is created only when content changes
    (I-VERSION-1 / I-VERSION-2).
    """
    from bio334_checker.core import exercises as ex_mod

    data_dir = Path(args.data_dir)
    if not data_dir.is_dir():
        print(f"data dir not found: {data_dir}", file=sys.stderr)
        return 2
    db_path = Path(args.db) if args.db else None
    init_db(db_path)
    conn = connect(db_path)
    try:
        specs = ex_mod.load_dir(data_dir)
        new = unchanged = 0
        for spec in specs:
            version, created = ex_mod.upsert_exercise(conn, spec)
            tag = "NEW REVISION" if created else "unchanged"
            print(f"  {spec.slug} v{version}  [{tag}]")
            if created:
                new += 1
            else:
                unchanged += 1
    finally:
        conn.close()
    print(f"Imported {len(specs)} exercises ({new} new revisions, {unchanged} unchanged).")
    return 0


def _cmd_version(_args: argparse.Namespace) -> int:
    print(f"bio334-checker {__version__}")
    return 0


def _cmd_serve(args: argparse.Namespace) -> int:
    import uvicorn

    from bio334_checker.interfaces.web.app import create_app

    db_path = Path(args.db) if args.db else None
    app = create_app(db_path=db_path, host=args.host, enable_worker=not args.no_worker)
    uvicorn.run(app, host=args.host, port=args.port, log_level=args.log_level)
    return 0


def _cmd_chain_replay(args: argparse.Namespace) -> int:
    """One-shot drain of pending submissions + chain bridge writes.

    Useful for the post-course reconciliation step (ARCHITECTURE.md §7.3).
    """
    from bio334_checker.chain.bridge import chain_drain_once
    from bio334_checker.chain.client import default_client
    from bio334_checker.core import drain as drain_mod

    db_path = Path(args.db) if args.db else None
    init_db(db_path)
    conn = connect(db_path)
    try:
        d = drain_mod.drain_once(conn)
        c = chain_drain_once(conn, default_client())
    finally:
        conn.close()
    print(
        f"drain: retried={d['retried']} graded={d['graded']} "
        f"still_pending={d['still_pending']} failed={d['failed']}"
    )
    print(
        f"chain: records_written={c.records_written} "
        f"attestations_written={c.attestations_written} "
        f"transient={c.transient_errors} permanent={c.permanent_errors}"
    )
    return 0


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="bio334-checker",
        description="LLM-augmented exercise checker for BIO334.",
    )
    sub = p.add_subparsers(dest="cmd", required=True)

    p_init = sub.add_parser("init-db", help="Create / migrate the SQLite schema.")
    p_init.add_argument("--db", default=str(DEFAULT_DB_PATH), help="Path to SQLite file.")
    p_init.set_defaults(func=_cmd_init_db)

    p_imp = sub.add_parser(
        "import-exercises",
        help="Load YAML exercise definitions and upsert into the DB.",
    )
    p_imp.add_argument("--db", default=str(DEFAULT_DB_PATH), help="Path to SQLite file.")
    p_imp.add_argument(
        "--data-dir",
        required=True,
        help="Directory containing *.yaml/*.yml exercise definitions.",
    )
    p_imp.set_defaults(func=_cmd_import_exercises)

    p_serve = sub.add_parser("serve", help="Start the web server.")
    p_serve.add_argument("--db", default=str(DEFAULT_DB_PATH), help="Path to SQLite file.")
    p_serve.add_argument(
        "--host",
        default="127.0.0.1",
        help="Bind interface. /admin* enforces 127.0.0.1; remote access via SSH tunnel.",
    )
    p_serve.add_argument("--port", type=int, default=8334)
    p_serve.add_argument("--log-level", default="info")
    p_serve.add_argument(
        "--no-worker",
        action="store_true",
        help="Disable the singleton background worker (drain + chain).",
    )
    p_serve.set_defaults(func=_cmd_serve)

    p_replay = sub.add_parser(
        "chain-replay",
        help="One-shot reconciliation: drain pending + write chain records.",
    )
    p_replay.add_argument("--db", default=str(DEFAULT_DB_PATH))
    p_replay.set_defaults(func=_cmd_chain_replay)

    p_ver = sub.add_parser("version", help="Show version.")
    p_ver.set_defaults(func=_cmd_version)

    return p


def main(argv: list[str] | None = None) -> int:
    # Load .env before argparse so flag defaults can still come from env
    # vars when convenient. Lookup order (first match wins; existing env
    # vars always take precedence over file contents):
    #   1. $BIO334_ENV_FILE (explicit override)
    #   2. ./.env.local  (developer-local secrets, gitignored)
    #   3. ./.env        (project defaults, gitignored)
    explicit = os.environ.get("BIO334_ENV_FILE")
    candidates = [Path(explicit)] if explicit else [Path(".env.local"), Path(".env")]
    for cand in candidates:
        if _load_dotenv(cand):
            break

    parser = _build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
