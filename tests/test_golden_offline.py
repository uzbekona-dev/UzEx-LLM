"""Offline consistency check for tests/golden.jsonl: the ground-truth SQL must still produce the
expected numbers/strings against data/uzex.db. No LLM needed. Run: python -m pytest tests/test_golden_offline.py -q"""

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
GOLDEN = os.path.join(ROOT, "tests", "golden.jsonl")
ENTRIES = load_golden(GOLDEN)
REL_TOL = 1e-9


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


def test_golden_file_shape() -> None:
    assert len(ENTRIES) == 40
    assert len({e.id for e in ENTRIES}) == 40
    with open(GOLDEN, encoding="utf-8") as fh:
        for line in fh:
            if line.strip():
                raw = json.loads(line)
                assert set(raw) == {"id", "q", "sql", "expect", "unanswerable", "tags"}, raw["id"]
    assert sum(1 for e in ENTRIES if e.unanswerable) == 6
    assert sum(1 for e in ENTRIES if "uz" in e.tags) == sum(1 for e in ENTRIES if "ru" in e.tags) == 20


@pytest.mark.parametrize("entry", [e for e in ENTRIES if e.sql], ids=lambda e: e.id)
def test_golden_sql_matches_expectations(con, entry: GoldenEntry) -> None:
    result = run_query(con, entry.sql)
    assert result.ok, f"{entry.id}: {result.error}"
    if entry.unanswerable:
        assert result.rows == [], f"{entry.id}: unanswerable entry must return no rows"
        return
    assert result.rows, f"{entry.id}: SQL returned no rows"
    values = _row_numbers(result.rows)
    for expected in entry.numbers:
        assert any(abs(v - expected) <= REL_TOL * max(1.0, abs(expected)) for v in values), \
            f"{entry.id}: number {expected} not in rows {result.rows[:5]}"
    text = _row_text(result.rows)
    for expected in entry.strings:
        assert translit(expected) in text, f"{entry.id}: string {expected!r} not in rows"
