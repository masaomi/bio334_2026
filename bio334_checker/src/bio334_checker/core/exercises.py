"""Exercise definitions: YAML schema, loader, version-bumping upsert.

Per ARCHITECTURE.md §4 + I-VERSION-1 / I-VERSION-2:

- ``exercises`` is a mutable pointer to the latest version.
- ``exercise_revisions`` is an append-only history; one row per (slug, version).
- On import, if the YAML matches the latest revision, do nothing. Otherwise
  insert a new revision and bump ``exercises.version``.
- Submissions reference both ``exercise_slug`` and ``exercise_version`` so
  past submissions remain reproducible after a rubric edit.

YAML schema (per file, one exercise):

```yaml
slug: day1_p1_ex1                 # str, primary key
title: First Python program       # str
day: 1                            # int, 1..3
part: 1                           # int
order_index: 1                    # int, sort order within (day, part)
source_gist_url: null             # str | null
description_md: |
  # Exercise 1
  Write a program that prints "Hello, world!".
expected_stdout: "Hello, world!\n"  # str | null  (null = no canonical answer)
argv: []                          # list[str]
files_provided: []                # list[str]  paths relative to data dir
rubric_md: |
  Score 100 if the program prints "Hello, world!" exactly.
  Subtract 50 if there are unused imports.
max_score: 100
pass_threshold: 70
llm_floor: 40
allow_nonzero_rc: false
timeout_s: 10
```
"""

from __future__ import annotations

import json
import sqlite3
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import yaml


# Set of fields that participate in the content hash. A change in any of
# these fields constitutes a new revision.
_CONTENT_FIELDS = (
    "description_md",
    "expected_stdout",
    "argv",
    "files_provided",
    "rubric_md",
    "max_score",
    "pass_threshold",
    "llm_floor",
    "allow_nonzero_rc",
    "timeout_s",
)


@dataclass
class ExerciseSpec:
    slug: str
    title: str
    day: int
    part: int
    order_index: int
    description_md: str
    rubric_md: str
    expected_stdout: Optional[str] = None
    argv: list[str] = field(default_factory=list)
    files_provided: list[str] = field(default_factory=list)
    max_score: int = 100
    pass_threshold: int = 70
    llm_floor: int = 40
    allow_nonzero_rc: bool = False
    timeout_s: int = 10
    source_gist_url: Optional[str] = None

    def content_signature(self) -> str:
        """Stable JSON of the content fields, used for change detection."""
        d = {f: getattr(self, f) for f in _CONTENT_FIELDS}
        return json.dumps(d, sort_keys=True, ensure_ascii=False)


def load_yaml(path: Path) -> ExerciseSpec:
    """Parse a single YAML file into an :class:`ExerciseSpec`."""
    with path.open("r", encoding="utf-8") as f:
        raw = yaml.safe_load(f)
    if not isinstance(raw, dict):
        raise ValueError(f"{path}: top-level must be a mapping, got {type(raw).__name__}")

    required = {"slug", "title", "day", "part", "order_index", "description_md", "rubric_md"}
    missing = required - raw.keys()
    if missing:
        raise ValueError(f"{path}: missing required fields: {sorted(missing)}")

    return ExerciseSpec(
        slug=str(raw["slug"]),
        title=str(raw["title"]),
        day=int(raw["day"]),
        part=int(raw["part"]),
        order_index=int(raw["order_index"]),
        description_md=str(raw["description_md"]),
        rubric_md=str(raw["rubric_md"]),
        expected_stdout=raw.get("expected_stdout"),
        argv=list(raw.get("argv") or []),
        files_provided=list(raw.get("files_provided") or []),
        max_score=int(raw.get("max_score", 100)),
        pass_threshold=int(raw.get("pass_threshold", 70)),
        llm_floor=int(raw.get("llm_floor", 40)),
        allow_nonzero_rc=bool(raw.get("allow_nonzero_rc", False)),
        timeout_s=int(raw.get("timeout_s", 10)),
        source_gist_url=raw.get("source_gist_url"),
    )


def load_dir(directory: Path) -> list[ExerciseSpec]:
    """Load every ``*.yaml`` / ``*.yml`` file in a directory.

    Files matching ``*.example.yaml`` / ``*.example.yml`` are skipped so
    that templates kept in the repo do not pollute a real import. Use a
    plain ``*.yaml`` extension to opt in.
    """
    paths = sorted(
        list(directory.glob("*.yaml")) + list(directory.glob("*.yml"))
    )
    paths = [p for p in paths if not p.name.endswith((".example.yaml", ".example.yml"))]
    return [load_yaml(p) for p in paths]


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def upsert_exercise(conn: sqlite3.Connection, ex: ExerciseSpec) -> tuple[int, bool]:
    """Idempotent upsert. Returns ``(version, created_new_revision)``.

    - If the slug is unknown, insert version 1.
    - If the slug exists and the latest revision matches the YAML's content
      signature, no new revision is written; ``exercises`` row metadata
      (title, day, part, order_index, source_gist_url) is still refreshed.
    - Otherwise, insert a new revision row and bump ``exercises.version``.
    """
    row = conn.execute(
        "SELECT version FROM exercises WHERE slug = ?", (ex.slug,)
    ).fetchone()
    now = _now_iso()

    if row is None:
        conn.execute(
            "INSERT INTO exercises (slug, version, title, day, part, order_index, "
            "source_gist_url) VALUES (?, 1, ?, ?, ?, ?, ?)",
            (ex.slug, ex.title, ex.day, ex.part, ex.order_index, ex.source_gist_url),
        )
        _insert_revision(conn, ex, version=1, created_at=now)
        return (1, True)

    current_version = int(row["version"])
    rev = conn.execute(
        "SELECT * FROM exercise_revisions WHERE slug = ? AND version = ?",
        (ex.slug, current_version),
    ).fetchone()
    same = rev is not None and _revision_matches(rev, ex)

    # Always refresh mutable pointer metadata (these are not content fields).
    conn.execute(
        "UPDATE exercises SET title = ?, day = ?, part = ?, order_index = ?, "
        "source_gist_url = ? WHERE slug = ?",
        (ex.title, ex.day, ex.part, ex.order_index, ex.source_gist_url, ex.slug),
    )

    if same:
        return (current_version, False)

    new_version = current_version + 1
    conn.execute(
        "UPDATE exercises SET version = ? WHERE slug = ?", (new_version, ex.slug)
    )
    _insert_revision(conn, ex, version=new_version, created_at=now)
    return (new_version, True)


def _insert_revision(
    conn: sqlite3.Connection, ex: ExerciseSpec, *, version: int, created_at: str
) -> None:
    conn.execute(
        """INSERT INTO exercise_revisions (
              slug, version, description_md, expected_stdout, argv, files_provided,
              rubric_md, max_score, pass_threshold, llm_floor, allow_nonzero_rc,
              timeout_s, created_at
           ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            ex.slug,
            version,
            ex.description_md,
            ex.expected_stdout,
            json.dumps(ex.argv),
            json.dumps(ex.files_provided),
            ex.rubric_md,
            ex.max_score,
            ex.pass_threshold,
            ex.llm_floor,
            int(ex.allow_nonzero_rc),
            ex.timeout_s,
            created_at,
        ),
    )


def _revision_matches(rev: sqlite3.Row, ex: ExerciseSpec) -> bool:
    return (
        rev["description_md"] == ex.description_md
        and rev["expected_stdout"] == ex.expected_stdout
        and rev["argv"] == json.dumps(ex.argv)
        and rev["files_provided"] == json.dumps(ex.files_provided)
        and rev["rubric_md"] == ex.rubric_md
        and int(rev["max_score"]) == ex.max_score
        and int(rev["pass_threshold"]) == ex.pass_threshold
        and int(rev["llm_floor"]) == ex.llm_floor
        and bool(rev["allow_nonzero_rc"]) == ex.allow_nonzero_rc
        and int(rev["timeout_s"]) == ex.timeout_s
    )


# ----------------------------------------------------------------------------
# Read-side helpers (for routes)
# ----------------------------------------------------------------------------

@dataclass
class ExerciseListItem:
    slug: str
    title: str
    day: int
    part: int
    order_index: int
    version: int
    visible_to_students: bool = True


@dataclass
class ExerciseDetail:
    slug: str
    title: str
    day: int
    part: int
    order_index: int
    version: int
    description_md: str
    rubric_md: str
    expected_stdout: Optional[str]
    argv: list[str]
    files_provided: list[str]
    max_score: int
    pass_threshold: int
    llm_floor: int
    allow_nonzero_rc: bool
    timeout_s: int
    source_gist_url: Optional[str]


def list_exercises(
    conn: sqlite3.Connection,
    *,
    day: Optional[int] = None,
    student_view: bool = False,
) -> list[ExerciseListItem]:
    """List exercises. ``student_view=True`` filters out exercises whose
    admin-controlled visibility flag is off, used by all student-facing
    routes so the lecturer can pace exercise reveal per day."""
    cols = "slug, title, day, part, order_index, version, visible_to_students"
    clauses = []
    params: list = []
    if day is not None:
        clauses.append("day = ?")
        params.append(day)
    if student_view:
        clauses.append("visible_to_students = 1")
    where = (" WHERE " + " AND ".join(clauses)) if clauses else ""
    rows = conn.execute(
        f"SELECT {cols} FROM exercises{where} ORDER BY day, part, order_index",
        params,
    ).fetchall()
    out: list[ExerciseListItem] = []
    for r in rows:
        d = dict(r)
        d["visible_to_students"] = bool(d.get("visible_to_students", 1))
        out.append(ExerciseListItem(**d))
    return out


def is_visible_to_students(conn: sqlite3.Connection, slug: str) -> bool:
    """Whether the given exercise is currently revealed to students."""
    row = conn.execute(
        "SELECT visible_to_students FROM exercises WHERE slug = ?", (slug,)
    ).fetchone()
    if row is None:
        return False
    return bool(row["visible_to_students"])


def set_visibility(conn: sqlite3.Connection, slug: str, visible: bool) -> None:
    conn.execute(
        "UPDATE exercises SET visible_to_students = ? WHERE slug = ?",
        (1 if visible else 0, slug),
    )
    conn.commit()


def bulk_set_visibility(
    conn: sqlite3.Connection, visible_slugs: list[str]
) -> None:
    """Set the given slugs visible and ALL OTHERS hidden, atomically.
    Used by the admin checkbox-form POST: every checked slug arrives in
    ``visible_slugs``, every unchecked slug is implicitly hidden."""
    conn.execute("BEGIN IMMEDIATE")
    try:
        conn.execute("UPDATE exercises SET visible_to_students = 0")
        if visible_slugs:
            placeholders = ",".join(["?"] * len(visible_slugs))
            conn.execute(
                f"UPDATE exercises SET visible_to_students = 1 "
                f"WHERE slug IN ({placeholders})",
                visible_slugs,
            )
        conn.execute("COMMIT")
    except Exception:
        conn.execute("ROLLBACK")
        raise


def get_exercise_detail(
    conn: sqlite3.Connection, slug: str, version: Optional[int] = None
) -> Optional[ExerciseDetail]:
    """Return a fully resolved exercise. ``version=None`` means latest pointer."""
    head = conn.execute(
        "SELECT slug, title, day, part, order_index, version, source_gist_url "
        "FROM exercises WHERE slug = ?",
        (slug,),
    ).fetchone()
    if head is None:
        return None
    target_version = version if version is not None else int(head["version"])
    rev = conn.execute(
        "SELECT * FROM exercise_revisions WHERE slug = ? AND version = ?",
        (slug, target_version),
    ).fetchone()
    if rev is None:
        return None
    return ExerciseDetail(
        slug=head["slug"],
        title=head["title"],
        day=int(head["day"]),
        part=int(head["part"]),
        order_index=int(head["order_index"]),
        version=int(rev["version"]),
        description_md=rev["description_md"],
        rubric_md=rev["rubric_md"],
        expected_stdout=rev["expected_stdout"],
        argv=json.loads(rev["argv"] or "[]"),
        files_provided=json.loads(rev["files_provided"] or "[]"),
        max_score=int(rev["max_score"]),
        pass_threshold=int(rev["pass_threshold"]),
        llm_floor=int(rev["llm_floor"]),
        allow_nonzero_rc=bool(rev["allow_nonzero_rc"]),
        timeout_s=int(rev["timeout_s"]),
        source_gist_url=head["source_gist_url"],
    )
