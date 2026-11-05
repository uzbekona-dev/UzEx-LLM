"""Analytics reports: every figure must equal an independent SQL count; no LLM involved."""

from __future__ import annotations

import os
from types import SimpleNamespace

import pytest

from app import analytics as an
from app.render import format_number
from app.sql_guard import open_db

DB = os.environ.get("DB_PATH", "data/uzex.db")
pytestmark = pytest.mark.skipif(not os.path.exists(DB), reason="data/uzex.db not built")


@pytest.fixture(scope="module")
def con():
    return open_db(DB)


def _one(con, sql: str, *args):
    return con.execute(sql, args).fetchone()[0]


def test_product_report_figures(con) -> None:
    text = an.product_report(con, "520100", "uz")
    total = _one(con, "SELECT COUNT(*) FROM deals WHERE tnved = '520100' AND year = 2024")
    cancelled = _one(con, "SELECT COUNT(*) FROM deals WHERE tnved = '520100' AND year = 2024 AND is_cancelled = 1")
    volume = _one(con, "SELECT SUM(volume) FROM deals WHERE tnved = '520100' AND year = 2024 AND is_cancelled = 0")
    assert f"2024: **{format_number(total)}** bitim (bekor {format_number(cancelled)}) · {format_number(volume)} kg" in text
    top = con.execute("SELECT seller_inn, SUM(amount_uzs) s FROM deals WHERE tnved = '520100' AND is_cancelled = 0 "
                      "GROUP BY seller_inn ORDER BY s DESC LIMIT 1").fetchone()
    assert f"({top[0]}) — **{format_number(round(top[1]))}** so'm" in text  # ranked by amount, whole so'm
    assert text.startswith("📊 **Paxta xomashyosi** (TN VED 520100)")


def test_company_report_figures(con) -> None:
    text = an.company_report(con, "915861525", "ru")
    total = _one(con, "SELECT COUNT(*) FROM deals WHERE seller_inn = '915861525' OR buyer_inn = '915861525'")
    per_year = con.execute("SELECT year, COUNT(*) FROM deals WHERE seller_inn = '915861525' OR buyer_inn = '915861525' "
                           "GROUP BY year").fetchall()
    assert sum(n for _, n in per_year) == total == 72
    for year, n in per_year:
        assert f"{year}: **{format_number(n)}** сделок" in text
    assert "(ИНН 915861525)" in text


def test_broker_report_counts_each_deal_once(con) -> None:
    text = an.broker_report(con, "BK045", "uz")
    for year, n in con.execute("SELECT year, COUNT(*) FROM deals WHERE seller_broker = 'BK045' OR buyer_broker = 'BK045' "
                               "GROUP BY year").fetchall():
        assert f"{year}: **{format_number(n)}** bitim" in text
    assert "(BK045)" in text


def test_overview_totals(con) -> None:
    text = an.overview_report(DB, "uz")
    assert f"Jami: **{format_number(_one(con, 'SELECT COUNT(*) FROM deals'))}** bitim" in text
    cancelled_2026 = _one(con, "SELECT COUNT(*) FROM deals WHERE year = 2026 AND is_cancelled = 1")
    assert f"(bekor {format_number(cancelled_2026)})" in text


def test_cyrillic_labels_keep_data_values(con) -> None:
    text = an.broker_report(con, "BK045", "uz_cyr")
    assert "__Йиллар бўйича:__" in text and "битим" in text and "BK045" in text


def test_unknown_entities_say_so(con) -> None:
    assert an.product_report(con, "000000", "uz") == "Bu bo'yicha bitimlar topilmadi."
    assert an.company_report(con, "000000000", "ru") == "По этому объекту сделок не найдено."
    assert an.broker_report(con, "BK999", "uz") == "Bu bo'yicha bitimlar topilmadi."


def test_callback_roundtrip_and_size() -> None:
    t = an.Target("c", "915861525", "x")
    data = t.callback("uz_cyr")
    assert len(data.encode()) <= 64
    assert an.parse_callback(data) == ("uz_cyr", an.Target("c", "915861525", ""))
    assert an.parse_callback("an|uz|x|1") is None and an.parse_callback("other") is None


def test_pick_targets_only_confident() -> None:
    P = SimpleNamespace
    res = P(companies=[P(inn="915861525", name="Qojo Invest")], brokers=["BK045"],
            products=[P(tnved="520100", name_uz="Paxta", score=95), P(tnved="110100", name_uz="Un", score=80)], inns=[])
    kinds = [(t.kind, t.key) for t in an.pick_targets(res)]
    assert kinds == [("c", "915861525"), ("b", "BK045"), ("p", "520100")]
    weak = P(companies=[], brokers=[], products=[P(tnved="110100", name_uz="Un", score=80)], inns=[])
    assert an.pick_targets(weak) == []


def test_button_titles_follow_language() -> None:
    P = SimpleNamespace
    res = P(companies=[], brokers=[], inns=[], products=[P(tnved="520100", name_uz="Paxta xomashyosi", name_ru="Хлопок-сырец", score=100)])
    assert an.pick_targets(res, "ru")[0].title == "Хлопок-сырец"
    assert an.pick_targets(res, "uz_cyr")[0].title == "Пахта хомашёси"
    assert an.pick_targets(res, "uz")[0].title == "Paxta xomashyosi"


def test_multi_unit_product_never_adds_units(con) -> None:
    text = an.product_report(con, "271019", "uz")  # diesel: kilograms and tonnes
    line_2024 = next(l for l in text.splitlines() if l.startswith("2024:"))
    assert " kg + " in line_2024 or " tonna + " in line_2024
    assert "o'rtacha" not in line_2024  # no average price across two units
    total = _one(con, "SELECT COUNT(*) FROM deals WHERE tnved = '271019' AND year = 2024")
    assert line_2024.startswith(f"2024: **{format_number(total)}** bitim")
    assert sum(1 for l in text.splitlines() if l.startswith("2024:")) == 1


def test_sums_are_whole_and_cyrillic_header(con) -> None:
    text = an.overview_report(DB, "uz")
    assert not any(ch == "." for l in text.splitlines() if "so'm" in l for ch in l.split("so'm")[0][-4:])
    assert "(СТИР 915861525)" in an.company_report(con, "915861525", "uz_cyr")
    assert "(ТН ВЭД 520100)" in an.product_report(con, "520100", "uz_cyr")
