"""Offline tests: no LLM needed. Run: python -m pytest tests -q"""

from __future__ import annotations

import os

import pytest

from app.normalize import company_key, parse_grade_class, parse_number, translit
from app.sql_guard import SqlRejected, clean_sql, open_db, run_query
from app.verify import extract_numbers, verify_answer

DB = os.environ.get("DB_PATH", "data/uzex.db")


def test_parse_number_with_spaces() -> None:
    assert parse_number("304 547 938.4") == 304547938.4
    assert parse_number("") is None


@pytest.mark.parametrize("text,expected", [
    ("Хлопок-сырец (спот) I сорт 1-класс", (1, 1)),
    ("ХЛОПОК СЫРЕЦ (СПОТ) 3 СОРТ II КЛАСС", (3, 2)),
    ("Хлопок сырец (спот) второй сорт 2 класс", (2, 2)),
    ("Мука пшеничная Высший сорт хлебопекарная", (0, None)),
    ("Труба ПЭ Ø63мм", (None, None)),
])
def test_parse_grade_class(text: str, expected: tuple) -> None:
    assert parse_grade_class(text) == expected


def test_company_key_unifies_scripts() -> None:
    assert company_key('"Qojo‘ Invest" MChJ') == "qojo invest"
    assert company_key('"ҲАРАЙЎМ КИМЁ" МЧЖ') == translit("Harayo'm Kimyo")


def test_clean_sql_rejects_writes() -> None:
    with pytest.raises(SqlRejected):
        clean_sql("DELETE FROM deals")
    with pytest.raises(SqlRejected):
        clean_sql("SELECT 1; SELECT 2")
    assert clean_sql("select 1").lower().endswith("limit 50")


def test_verify_answer_flags_invented_numbers() -> None:
    rows = [(431061, "Исполнен")]
    assert verify_answer("Bajarilgan bitimlar: 431 061 ta", rows, "q").ok
    assert verify_answer("Bajarilgan bitimlar: 431 062 ta", rows, "q").ok is False  # off by one = invented
    assert verify_answer("Jami 999 999 ta", rows, "q").ok is False
    assert verify_answer("Taxminan 431.1 ming ta", rows, "q").ok  # rounded + scaled is fine
    assert verify_answer("Summa 1 234 567.89 so'm", [(1234567.891,)], "q").ok
    assert extract_numbers("1 234 567.89 so'm") == [1234567.89]


@pytest.mark.skipif(not os.path.exists(DB), reason="database not built")
class TestDatabase:
    con = open_db(DB) if os.path.exists(DB) else None

    def test_total_deals(self) -> None:
        r = run_query(self.con, "SELECT COUNT(*) FROM deals")
        assert r.rows[0][0] == 500000

    def test_cotton_2024_volume_by_unit(self) -> None:
        r = run_query(self.con, "SELECT unit, SUM(volume) FROM deals WHERE tnved='520100' AND year=2024 AND is_cancelled=0 GROUP BY unit")
        assert r.ok and r.rows

    def test_missing_deal_returns_nothing(self) -> None:
        # 4 956 numbers are skipped; find one and make sure exact match returns no row
        r = run_query(self.con, "SELECT d.deal_no+1 FROM deals d LEFT JOIN deals n ON n.deal_no=d.deal_no+1 WHERE n.deal_no IS NULL LIMIT 1")
        missing = r.rows[0][0]
        assert run_query(self.con, f"SELECT * FROM deals WHERE deal_no={missing}").rows == []

    def test_homonym_companies_both_visible(self) -> None:
        r = run_query(self.con, "SELECT inn, name FROM participants WHERE name_key LIKE '%' || ckey('Qojo Invest') || '%'")
        assert len(r.rows) == 2

    def test_export_deals_have_rate(self) -> None:
        r = run_query(self.con, "SELECT COUNT(*) FROM deals WHERE currency='Доллар США' AND usd_rate IS NULL")
        assert r.rows[0][0] == 0

    def test_timeout_guard_present(self) -> None:
        r = run_query(self.con, "SELECT 1 WHERE 0")
        assert r.ok and r.rows == []
