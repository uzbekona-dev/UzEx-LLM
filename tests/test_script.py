"""Answers mirror the script of an Uzbek question: Cyrillic in -> Cyrillic out, data values untouched."""

from __future__ import annotations

import json
import os

import pytest

from app.agent import Agent, _guess_language
from app.format import render as render_html
from app.render import RenderSpec, render, render_generic
from app.script import UZ_CYR, is_cyrillic, lat_to_cyr

DB = os.environ.get("DB_PATH", "data/uzex.db")


@pytest.fixture(autouse=True)
def no_critic(monkeypatch: pytest.MonkeyPatch) -> None:
    from app import agent as agent_mod
    monkeypatch.setattr(agent_mod, "SQL_CRITIC", False)  # scripted replies carry no critic verdict


@pytest.mark.parametrize(("latin", "cyrillic"), [
    ("paxta xomashyosi sotilgan", "пахта хомашёси сотилган"),
    ("O'rtacha narx, g'alla, ma'lumot", "Ўртача нарх, ғалла, маълумот"),
    ("javob yo'q", "жавоб йўқ"),
    ("Eksport, Yetkazib berish, yanvar, iyun", "Экспорт, Етказиб бериш, январ, июн"),
    ("Toshkent shahri, Farg'ona viloyati", "Тошкент шаҳри, Фарғона вилояти"),
    ("STIR, QQS, SQL, BK045, DAP, 2024-yilda", "СТИР, ҚҚС, SQL, BK045, DAP, 2024-йилда"),
    ("**{deal_count} ta** bitim, {total_volume:t} tonna", "**{deal_count} та** битим, {total_volume:t} тонна"),
])
def test_lat_to_cyr(latin: str, cyrillic: str) -> None:
    assert lat_to_cyr(latin) == cyrillic


def test_template_converted_but_data_values_untouched() -> None:
    spec = RenderSpec(headline="Sotuvchi **{seller_name}**, summa {amount} {currency}, holati {status}.")
    cols = ["seller_name", "amount", "currency", "status"]
    rows = [("RUKUSHO‘ FERMER MCHJ", 304547938.4, "Узбекский сум", "Исполнен")]
    out = render(spec, cols, rows, UZ_CYR, "q").text
    assert out == "Сотувчи **RUKUSHO‘ FERMER MCHJ**, сумма 304 547 938.4 сўм, ҳолати Бажарилган."


def test_generic_fallback_in_cyrillic() -> None:
    out = render_generic(["code", "name", "deal_count"], [("BK111", '"Gucham Broker" MChJ', 6692),
                                                          ("BK005", "NAXON BROKER AJ", 5690)], UZ_CYR)
    assert out.splitlines()[0] == "__Натижа (маълумотлардан тўғридан-тўғри):__"
    assert "1. BK111 — \"Gucham Broker\" MChJ · Битимлар сони: **6 692**" in out


def test_language_guess_for_timeouts() -> None:
    assert _guess_language("Ун бўйича энг кўп битим қайси вилоятда?") == UZ_CYR
    assert _guess_language("Сколько сделок в 2024 году?") == "ru"
    assert _guess_language("2024-yilda qancha paxta sotilgan?") == "uz"
    assert is_cyrillic("2024 йил 17 июнь куни нечта битим тузилган?")


@pytest.mark.skipif(not os.path.exists(DB), reason="data/uzex.db not built")
def test_cyrillic_question_gets_cyrillic_answer_and_basis() -> None:
    from tests.test_agent import ScriptedLlm

    plan = {"language": "uz", "answerable": True, "interpretation": "Paxta xomashyosi, 2024-yil, bekor qilinganlarsiz",
            "sql": "SELECT unit, SUM(volume) AS total_volume, COUNT(*) AS deals_total FROM deals "
                   "WHERE tnved = '520100' AND year = 2024 GROUP BY unit",
            "render": {"headline": "2024-yilda jami **{deals_total} ta** bitim, hajmi {total_volume} {unit}."}}
    ans = Agent(None, ScriptedLlm([json.dumps(plan)]), db_path=DB).ask("2024 йилда нечта пахта битими бўлган?")
    assert ans.language == UZ_CYR
    assert ans.answer == "2024-йилда жами **30 037 та** битим, ҳажми 1 789 727 901 кг."
    assert ans.interpretation == "Пахта хомашёси, 2024-йил, бекор қилинганларсиз"
    html = render_html(ans)
    assert "Маълумотлар асосида" in html and "Талқин" in html


@pytest.mark.skipif(not os.path.exists(DB), reason="data/uzex.db not built")
def test_unanswerable_cyrillic_message() -> None:
    from tests.test_agent import ScriptedLlm

    plan = {"language": "uz", "answerable": False, "reason": "Direktorlar haqida ma'lumot yo'q.", "interpretation": "x", "sql": ""}
    ans = Agent(None, ScriptedLlm([json.dumps(plan)]), db_path=DB).ask("Директори ким?")
    assert ans.answer == "Маълумотларда бу саволга жавоб йўқ. Директорлар ҳақида маълумот йўқ."


@pytest.mark.skipif(not os.path.exists(DB), reason="data/uzex.db not built")
def test_latin_question_with_cyrillic_template_is_sent_back() -> None:
    from tests.test_agent import ScriptedLlm

    sql = "SELECT COUNT(*) AS contracts_total FROM contracts WHERE contract_form = 'Фьючерс'"
    cyr = {"language": "uz", "answerable": True, "interpretation": "x", "sql": sql,
           "render": {"headline": "Фьючерс шартномалар сони **{contracts_total} та**."}}
    lat = {**cyr, "render": {"headline": "Fyuchers shartnomalar soni **{contracts_total} ta**."}}
    llm = ScriptedLlm([json.dumps(cyr), json.dumps(lat)])
    ans = Agent(None, llm, db_path=DB).ask("fyuchers kontrakt nechta")
    assert ans.answer == "Fyuchers shartnomalar soni **79 ta**." and "LATIN" in llm.calls[1]
