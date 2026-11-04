"""Mode B guarantees: identities are masked before the LLM, templates cannot carry values, rendering is local."""

from __future__ import annotations

import os

import pytest

from app.entities import EntityResolver
from app.pseudonym import Pseudonymizer
from app.render import RenderSpec, check_template, format_value, render
from app.sql_guard import open_db

DB = os.environ.get("DB_PATH", "data/uzex.db")
pytestmark = pytest.mark.skipif(not os.path.exists(DB), reason="data/uzex.db not built")


@pytest.fixture(scope="module")
def pseudo() -> tuple[EntityResolver, Pseudonymizer]:
    resolver = EntityResolver(open_db(DB))
    return resolver, Pseudonymizer(resolver)


def _mask(pseudo, question: str):
    resolver, p = pseudo
    return p.mask(question, resolver.resolve(question))


def test_company_name_and_inns_do_not_leave(pseudo) -> None:
    m = _mask(pseudo, "Сколько сделок у компании Qojo Invest?")
    assert m.question == "Сколько сделок у компании {C1}?"
    assert "Qojo" not in m.entity_block and "915861525" not in m.entity_block
    assert sorted(m.inns["{C1}"]) == ["912004930", "915861525"]
    assert m.substitute_sql("WHERE p.inn IN ({C1_INNS})") == "WHERE p.inn IN ('912004930', '915861525')"
    assert m.unmask("Сделки {C1}: {row_count}") == "Сделки Qojo Invest: {row_count}"


def test_explicit_inn_and_broker_code_masked(pseudo) -> None:
    m = _mask(pseudo, "BK045 brokeri va STIR 953758401 kompaniyasi")
    assert "953758401" not in m.question and "BK045" not in m.question
    assert m.substitute_sql("inn = {INN1} AND b = '{B1}'") == "inn = '953758401' AND b = 'BK045'"


def test_non_name_phrase_is_left_alone(pseudo) -> None:
    m = _mask(pseudo, "2025-yil top-5 broker")
    assert m.question == "2025-yil top-5 broker" and m.mapping == {}
    assert "top-5" in m.entity_block  # planner is told it is not a known name


def test_template_guard_rejects_values() -> None:
    cols = ["name", "inn", "total"]
    assert check_template(RenderSpec(headline="{name} ({inn}) — **{total}** ta"), cols, "q") == []
    probs = check_template(RenderSpec(headline="Qojo Invest 915861525 — {total}"), cols, "q")
    assert any("literal number" in p for p in probs)
    assert check_template(RenderSpec(headline="{amount}"), cols, "q") == ["unknown column {amount}"]
    assert check_template(RenderSpec(headline="2024-yilda {total}"), cols, "2024-yilda qancha?") == []


def test_render_formats_and_translates_locally() -> None:
    cols = ["deal_no", "deal_date", "volume", "unit", "amount", "currency", "status"]
    rows = [(100003, "2022-01-03", 23.0, "тонна", 505863932.0, "Узбекский сум", "Исполнен")]
    spec = RenderSpec(headline="{deal_no}-bitim ({deal_date:date}): {volume} {unit}, {amount} {currency}, holati {status}.")
    out = render(spec, cols, rows, "uz", "100003").text
    assert out == "100003-bitim (03.01.2022): 23 tonna, 505 863 932 so'm, holati Bajarilgan."
    assert render(spec, cols, rows, "ru", "100003").text.endswith("23 т, 505 863 932 сум, holati Исполнен.")


def test_render_list_and_empty() -> None:
    spec = RenderSpec(headline="Top brokerlar ({row_count} ta):", line="{code}: **{n} ta**", empty="Hech narsa yo'q.")
    out = render(spec, ["code", "n"], [("BK1", 5), ("BK2", 3)], "uz", "q").text
    assert out == "Top brokerlar (2 ta):\nBK1: **5 ta**\nBK2: **3 ta**"
    assert render(spec, ["code", "n"], [], "uz", "q").text == "Hech narsa yo'q."


def test_id_columns_are_not_thousand_grouped() -> None:
    assert format_value(100003, None, "ru", "deal_no") == "100003"
    assert format_value(2024, None, "uz", "year") == "2024"
    assert format_value(100003, None, "ru", "amount") == "100 003"


def test_generic_fallback_is_readable_and_verifiable() -> None:
    from app.verify import verify_answer
    cols = ["code", "name", "deal_count"]
    rows = [("BK111", '"Gucham Broker" MChJ', 6692), ("BK005", "NAXON BROKER AJ", 5690)]
    from app.render import render_generic
    out = render_generic(cols, rows, "uz")
    assert "1. BK111 — \"Gucham Broker\" MChJ · Bitimlar soni: **6 692**" in out
    assert verify_answer(out, rows, "q").ok
    one = render_generic(["deal_no", "deal_date", "volume", "unit"], [(100003, "2022-01-03", 23.0, "тонна")], "uz")
    assert "Bitim №: **100003**" in one and "Sana: **03.01.2022**" in one and "Hajm: **23 tonna**" in one


def test_uzbek_apostrophes_are_not_company_quotes() -> None:
    from app.verify import verify_answer
    text = "Ma'lumotlardan to'g'ridan-to'g'ri: Bo'juk ta'minot — **5 ta**"
    assert verify_answer(text, [(5,)], "q").ok
