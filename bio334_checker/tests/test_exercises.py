"""Exercise YAML loader + version-bumping upsert (I-VERSION-1/I-VERSION-2)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from bio334_checker.core import exercises as ex_mod
from bio334_checker.db.connection import connect, init_db


SAMPLE_YAML = """\
slug: day1_p1_test
title: Test exercise
day: 1
part: 1
order_index: 1
description_md: |
  Print hello.
rubric_md: |
  100 if prints hello.
expected_stdout: "hello\\n"
argv: []
files_provided: []
max_score: 100
pass_threshold: 70
llm_floor: 40
allow_nonzero_rc: false
timeout_s: 10
"""


@pytest.fixture()
def db(tmp_path):
    p = tmp_path / "ex.db"
    init_db(p)
    conn = connect(p)
    yield conn
    conn.close()


def _write(tmp_path: Path, name: str, content: str) -> Path:
    p = tmp_path / name
    p.write_text(content, encoding="utf-8")
    return p


def test_load_yaml(tmp_path: Path) -> None:
    p = _write(tmp_path, "ex.yaml", SAMPLE_YAML)
    spec = ex_mod.load_yaml(p)
    assert spec.slug == "day1_p1_test"
    assert spec.day == 1
    assert spec.expected_stdout == "hello\n"
    assert spec.allow_nonzero_rc is False
    assert spec.timeout_s == 10


def test_load_yaml_missing_field(tmp_path: Path) -> None:
    p = _write(tmp_path, "ex.yaml", "slug: x\ntitle: y\n")
    with pytest.raises(ValueError, match="missing required fields"):
        ex_mod.load_yaml(p)


def test_load_dir_skips_example_files(tmp_path: Path) -> None:
    _write(tmp_path, "real.yaml", SAMPLE_YAML)
    _write(tmp_path, "skip.example.yaml", SAMPLE_YAML)
    specs = ex_mod.load_dir(tmp_path)
    assert len(specs) == 1


def test_upsert_inserts_v1(db) -> None:
    spec = ex_mod.load_yaml(_make_yaml(db, SAMPLE_YAML))
    version, created = ex_mod.upsert_exercise(db, spec)
    assert (version, created) == (1, True)

    rows = db.execute(
        "SELECT version FROM exercise_revisions WHERE slug=? ORDER BY version", (spec.slug,)
    ).fetchall()
    assert [r["version"] for r in rows] == [1]


def test_upsert_idempotent_when_unchanged(db) -> None:
    spec = ex_mod.load_yaml(_make_yaml(db, SAMPLE_YAML))
    ex_mod.upsert_exercise(db, spec)
    version, created = ex_mod.upsert_exercise(db, spec)
    assert (version, created) == (1, False)
    count = db.execute(
        "SELECT COUNT(*) AS c FROM exercise_revisions WHERE slug=?", (spec.slug,)
    ).fetchone()["c"]
    assert count == 1


def test_upsert_bumps_on_content_change(db) -> None:
    spec = ex_mod.load_yaml(_make_yaml(db, SAMPLE_YAML))
    ex_mod.upsert_exercise(db, spec)

    spec2 = ex_mod.load_yaml(_make_yaml(db, SAMPLE_YAML.replace("100 if prints hello.", "120 if prints hello.")))
    version, created = ex_mod.upsert_exercise(db, spec2)
    assert (version, created) == (2, True)

    versions = [
        r["version"]
        for r in db.execute(
            "SELECT version FROM exercise_revisions WHERE slug=? ORDER BY version",
            (spec.slug,),
        )
    ]
    assert versions == [1, 2]

    pointer = db.execute("SELECT version FROM exercises WHERE slug=?", (spec.slug,)).fetchone()
    assert pointer["version"] == 2


def test_upsert_refreshes_metadata_without_revision(db) -> None:
    """Title-only change updates the pointer row but does NOT create a new revision."""
    spec = ex_mod.load_yaml(_make_yaml(db, SAMPLE_YAML))
    ex_mod.upsert_exercise(db, spec)

    spec2 = ex_mod.load_yaml(_make_yaml(db, SAMPLE_YAML.replace("Test exercise", "Test exercise (renamed)")))
    version, created = ex_mod.upsert_exercise(db, spec2)
    assert created is False
    assert version == 1
    title = db.execute("SELECT title FROM exercises WHERE slug=?", (spec.slug,)).fetchone()["title"]
    assert title == "Test exercise (renamed)"


def test_get_detail_returns_latest_version(db) -> None:
    spec = ex_mod.load_yaml(_make_yaml(db, SAMPLE_YAML))
    ex_mod.upsert_exercise(db, spec)
    spec2 = ex_mod.load_yaml(_make_yaml(db, SAMPLE_YAML.replace("100 if prints hello.", "200 if prints hello.")))
    ex_mod.upsert_exercise(db, spec2)

    detail = ex_mod.get_exercise_detail(db, "day1_p1_test")
    assert detail is not None
    assert detail.version == 2
    assert "200" in detail.rubric_md


def test_get_detail_pinned_to_old_version(db) -> None:
    """I-VERSION-1: past submissions can resolve their pinned revision."""
    spec = ex_mod.load_yaml(_make_yaml(db, SAMPLE_YAML))
    ex_mod.upsert_exercise(db, spec)
    spec2 = ex_mod.load_yaml(_make_yaml(db, SAMPLE_YAML.replace("100 if prints hello.", "200 if prints hello.")))
    ex_mod.upsert_exercise(db, spec2)

    detail_v1 = ex_mod.get_exercise_detail(db, "day1_p1_test", version=1)
    assert detail_v1 is not None
    assert detail_v1.version == 1
    assert "100" in detail_v1.rubric_md


def test_list_exercises_orders_and_filters(db) -> None:
    yaml_a = SAMPLE_YAML  # day 1 part 1
    yaml_b = SAMPLE_YAML.replace("day1_p1_test", "day2_p1_test").replace("day: 1", "day: 2")
    ex_mod.upsert_exercise(db, ex_mod.load_yaml(_make_yaml(db, yaml_a, "a.yaml")))
    ex_mod.upsert_exercise(db, ex_mod.load_yaml(_make_yaml(db, yaml_b, "b.yaml")))

    all_items = ex_mod.list_exercises(db)
    assert [it.slug for it in all_items] == ["day1_p1_test", "day2_p1_test"]
    day2 = ex_mod.list_exercises(db, day=2)
    assert [it.slug for it in day2] == ["day2_p1_test"]


# helpers ---------------------------------------------------------------------

def _make_yaml(db, content: str, name: str = "ex.yaml") -> Path:
    """Write YAML to a tmp path the test's pytest tmp_path fixture provides."""
    # We piggy-back on the connection's DB file directory.
    # (Each db fixture lives in its own tmp dir.)
    p = Path(db.execute("PRAGMA database_list").fetchone()[2]).parent / name
    p.write_text(content, encoding="utf-8")
    return p
