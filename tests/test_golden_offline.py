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


REQUIRED_KEYS = {"id", "q", "sql", "expect", "unanswerable", "tags"}
OPTIONAL_KEYS = {"forbidden"}


def test_golden_file_shape() -> None:
    assert len(ENTRIES) == 100
    assert [e.id for e in ENTRIES] == [f"g{i:02d}" for i in range(1, 101)]
    with open(GOLDEN, encoding="utf-8") as fh:
        for line in fh:
            if line.strip():
                raw = json.loads(line)
                assert REQUIRED_KEYS <= set(raw) <= REQUIRED_KEYS | OPTIONAL_KEYS, raw["id"]
                assert set(raw["expect"]) == {"numbers", "strings"}, raw["id"]
                assert raw["tags"], raw["id"]
                if "forbidden" in raw:
                    assert raw["forbidden"] and all(isinstance(n, (int, float)) for n in raw["forbidden"]), raw["id"]
                    assert "injection" in raw["tags"], raw["id"]
    original = [e for e in ENTRIES if int(e.id[1:]) <= 40]
    assert sum(1 for e in original if e.unanswerable) == 6
    assert sum(1 for e in original if "uz" in e.tags) == sum(1 for e in original if "ru" in e.tags) == 20
    # g41-g100: jury-style mix (approximate minimums, see the task description)
    new = [e for e in ENTRIES if int(e.id[1:]) > 40]
    assert sum(1 for e in new if "cyr" in e.tags) >= 10
    assert sum(1 for e in new if "colloq" in e.tags) >= 8
    assert sum(1 for e in new if "date" in e.tags) >= 8
    assert sum(1 for e in new if "region-buyer" in e.tags) >= 3
    assert sum(1 for e in new if "dual" in e.tags) >= 7
    assert sum(1 for e in new if "multi" in e.tags) >= 7
    assert sum(1 for e in new if "trap" in e.tags) >= 10
    assert sum(1 for e in new if e.forbidden) >= 3


def test_forbidden_numbers_are_not_expected() -> None:
    """A forbidden number can never also be an expected number, and the bait must be absent from the SQL rows."""
    for e in ENTRIES:
        for bad in e.forbidden:
            assert bad not in e.numbers, e.id


def test_golden_check_honours_forbidden() -> None:
    from golden_check import forbidden_present

    entry = next(e for e in ENTRIES if e.forbidden)
    bait = f"{entry.forbidden[0]:g}"
    assert forbidden_present(entry, f"Javob: {bait}.") == [f"forbidden number {bait} present"]
    assert forbidden_present(entry, "Ma'lumotlarda bunday savolga javob yo'q.") == []


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
    for bad in entry.forbidden:
        assert not any(abs(v - bad) <= REL_TOL * max(1.0, abs(bad)) for v in values), \
            f"{entry.id}: forbidden number {bad} is a real value in the rows"


def test_language_check_in_golden_checker() -> None:
    import sys
    sys.path.insert(0, "scripts")
    from golden_check import GoldenEntry, language_problems

    from app.agent import AgentAnswer

    def entry(q, tags=()):
        return GoldenEntry(id="x", q=q, sql=None, numbers=(), strings=(), unanswerable=False, tags=tuple(tags), forbidden=())

    def ans(text, lang, rows=()):
        return AgentAnswer("q", lang, text, "", "SELECT 1", list(rows), [], True, True, 1.0)

    rows = [("Farg‘ona viloyati", "Исполнен")]
    assert language_problems(entry("Un bo'yicha qaysi viloyat?"), ans("Eng ko'p bitim Farg‘ona viloyatida tuzilgan", "uz", rows)) == []
    assert language_problems(entry("Ун бўйича қайси вилоят?"), ans("Энг кўп битим Farg‘ona viloyati ҳудудида тузилган", "uz_cyr", rows)) == []
    assert language_problems(entry("Сколько сделок по муке?"), ans("Больше всего сделок заключено в регионе", "ru")) == []
    assert language_problems(entry("Ун бўйича қайси вилоят?"), ans("Eng ko'p bitim tuzilgan hudud", "uz"))  # wrong script
    assert language_problems(entry("Сколько сделок по муке?"), ans("Eng ko'p bitim tuzilgan hudud", "uz"))  # wrong language
    assert language_problems(entry("How many deals?", ["en"]), ans("Всего сделок", "ru")) == []
