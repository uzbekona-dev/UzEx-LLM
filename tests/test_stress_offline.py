"""Offline consistency check for tests/stress.jsonl (new question types beyond golden.jsonl): the
ground-truth SQL must still produce the expected numbers/strings against data/uzex.db. No LLM needed.
Run: python -m pytest tests/test_stress_offline.py -q"""

from __future__ import annotations

import json
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts"))

from app.normalize import translit  # noqa: E402
from app.sql_guard import open_db, run_query  # noqa: E402
from golden_check import GoldenEntry, load_golden  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB = os.environ.get("DB_PATH", os.path.join(ROOT, "data", "uzex.db"))
STRESS = os.path.join(ROOT, "tests", "stress.jsonl")
ENTRIES = load_golden(STRESS)
REL_TOL = 1e-9
EXPECTED_COUNT = 50
LONG_QUESTION_MIN_CHARS = 300

REQUIRED_KEYS = {"id", "q", "sql", "expect", "unanswerable", "tags"}
OPTIONAL_KEYS = {"forbidden"}


def _row_numbers(rows: list[tuple]) -> list[float]:
    out = [float(len(rows))]
    for row in rows:
        for cell in row:
            if isinstance(cell, (int, float)):
                out.append(float(cell))
            elif isinstance(cell, str) and cell.strip().lstrip("-").isdigit():
                out.append(float(cell))
    return out


def _row_text(rows: list[tuple]) -> str:
    return translit(" | ".join(str(c) for row in rows for c in row if c is not None))


@pytest.fixture(scope="module")
def con():
    if not os.path.exists(DB):
        pytest.skip("database not built")
    return open_db(DB)


def test_stress_file_shape() -> None:
    assert len(ENTRIES) == EXPECTED_COUNT
    assert [e.id for e in ENTRIES] == [f"s{i:02d}" for i in range(1, EXPECTED_COUNT + 1)]
    with open(STRESS, encoding="utf-8") as fh:
        for line in fh:
            if line.strip():
                raw = json.loads(line)
                assert REQUIRED_KEYS <= set(raw) <= REQUIRED_KEYS | OPTIONAL_KEYS, raw["id"]
                assert set(raw["expect"]) == {"numbers", "strings"}, raw["id"]
                assert raw["tags"], raw["id"]
    # language split: half uz / half ru, plus one English question
    assert sum(1 for e in ENTRIES if "uz" in e.tags) == 25
    assert sum(1 for e in ENTRIES if "ru" in e.tags) == 24
    assert sum(1 for e in ENTRIES if "en" in e.tags) == 1
    assert all(("uz" in e.tags) + ("ru" in e.tags) + ("en" in e.tags) == 1 for e in ENTRIES)
    # every unanswerable entry has no SQL and no expectations; every answerable one has SQL
    for e in ENTRIES:
        if e.unanswerable:
            assert e.sql is None and not e.numbers and not e.strings, e.id
        else:
            assert e.sql and (e.numbers or e.strings), e.id
    assert sum(1 for e in ENTRIES if e.unanswerable) == 5
    assert sum(1 for e in ENTRIES if "trap" in e.tags) == 5
    assert sum(1 for e in ENTRIES if "multi" in e.tags) >= 12
    assert sum(1 for e in ENTRIES if "max-group" in e.tags) >= 4
    assert sum(1 for e in ENTRIES if "distinct" in e.tags) >= 5
    assert any(len(e.q) >= LONG_QUESTION_MIN_CHARS for e in ENTRIES if "long" in e.tags)


@pytest.mark.parametrize("entry", [e for e in ENTRIES if e.sql], ids=lambda e: e.id)
def test_stress_sql_matches_expectations(con, entry: GoldenEntry) -> None:
    result = run_query(con, entry.sql)
    assert result.ok, f"{entry.id}: {result.error}"
    assert result.rows, f"{entry.id}: SQL returned no rows"
    values = _row_numbers(result.rows)
    for expected in entry.numbers:
        assert any(abs(v - expected) <= REL_TOL * max(1.0, abs(expected)) for v in values), \
            f"{entry.id}: number {expected} not in rows {result.rows[:5]}"
    text = _row_text(result.rows)
    for expected in entry.strings:
        assert translit(expected) in text, f"{entry.id}: string {expected!r} not in rows"
