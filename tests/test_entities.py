"""Offline tests for app.entities (deterministic entity resolution). Needs data/uzex.db."""

from __future__ import annotations

import os
import time

import pytest

from app.entities import EntityResolver, Resolution, resolve_products
from app.sql_guard import open_db

DB = os.environ.get("DB_PATH", "data/uzex.db")
pytestmark = pytest.mark.skipif(not os.path.exists(DB), reason="data/uzex.db not built")


@pytest.fixture(scope="module")
def resolver() -> EntityResolver:
    return EntityResolver(open_db(DB))


# --------------------------------------------------------------------------- products
@pytest.mark.parametrize("question,tnved", [
    ("2024 yilda qancha paxta sotilgan?", "520100"),      # UZ Latin
    ("Сколько хлопка продано в 2023?", "520100"),          # RU inflected
    ("пахта нархи", "520100"),                            # UZ Cyrillic alias
    ("шакар qancha sotilgan", "170199"),                  # UZ Cyrillic
    ("sement narxi", "252329"),                           # UZ Latin
    ("Сколько цемента продано", "252329"),                # RU inflected
    ("Портландцемент hajmi", "252329"),                   # full RU canonical
    ("un qancha sotilgan", "110100"),                     # 2-letter UZ alias, exact
    ("Сколько муки купили", "110100"),                    # RU inflected 'мука'
    ("bug'doy narxi", "100199"),                          # apostrophe form
    ("буғдой", "100199"),                                 # UZ Cyrillic with ғ
])
def test_product_resolved(question: str, tnved: str) -> None:
    hits = resolve_products(question)
    assert hits, question
    assert hits[0].tnved == tnved
    assert hits[0].score >= 80


@pytest.mark.parametrize("question", [
    "Qancha tovar sotilgan?", "mahsulot", "Сколько товаров продано?",
    "Qaysi kompaniya eng ko'p bitim tuzgan?", "Сколько сделок было в 2024 году?",
])
def test_generic_words_do_not_match_products(question: str) -> None:
    assert resolve_products(question) == []


def test_products_capped_and_best_first() -> None:
    hits = resolve_products("paxta, sement, shakar va un")
    assert len(hits) <= 3
    assert [h.score for h in hits] == sorted((h.score for h in hits), reverse=True)


# --------------------------------------------------------------------------- companies
def test_company_exact_finds_both_homonyms(resolver: EntityResolver) -> None:
    res = resolver.resolve("Qojo Invest kompaniyasi 2024 yilda qancha paxta sotgan?")
    assert {c.inn for c in res.companies} >= {"915861525", "912004930"}
    assert all(c.score == 100 for c in res.companies if c.inn in {"915861525", "912004930"})
    assert res.unmatched_phrases == []


def test_company_typo_tolerated(resolver: EntityResolver) -> None:
    res = resolver.resolve('"Qojo Invets" MChJ nechta bitim tuzgan?')
    assert {c.inn for c in res.companies} == {"915861525", "912004930"}
    assert all(85 <= c.score < 100 for c in res.companies)


def test_company_quoted_russian_form(resolver: EntityResolver) -> None:
    res = resolver.resolve("Сколько цемента продала ООО «Qojo Invest» в 2023?")
    assert {c.inn for c in res.companies} >= {"915861525", "912004930"}
    assert res.products[0].tnved == "252329"


def test_company_phrase_without_match_is_reported(resolver: EntityResolver) -> None:
    res = resolver.resolve('"Zzqxw Vvbbnn" MChJ qancha sotgan?')
    assert res.companies == []
    assert res.unmatched_phrases == ["Zzqxw Vvbbnn"]
    assert "company phrase 'Zzqxw Vvbbnn' matched no participant" in res.prompt_block()


def test_question_words_are_not_company_phrases(resolver: EntityResolver) -> None:
    res = resolver.resolve("Qancha paxta sotilgan? Toshkent shahrida nechta bitim bor?")
    assert res.companies == [] and res.unmatched_phrases == []


# --------------------------------------------------------------------------- inn / brokers / deals
def test_inn_extracted(resolver: EntityResolver) -> None:
    res = resolver.resolve("INN 915861525 kompaniya nechta bitim tuzgan?")
    assert res.inns == ["915861525"]
    assert res.deal_nos == []
    assert "915861525" in res.prompt_block()


def test_broker_code(resolver: EntityResolver) -> None:
    res = resolver.resolve("Broker BK045 nechta bitim tuzgan?")
    assert res.brokers == ["BK045"]
    assert res.unmatched_phrases == []


def test_broker_by_name(resolver: EntityResolver) -> None:
    assert resolver.resolve("Kahir broker qancha bitim tuzgan?").brokers == ["BK002"]
    assert resolver.resolve("Сколько сделок у брокера Кекухо").brokers == ["BK001"]


def test_deal_number_vs_inn(resolver: EntityResolver) -> None:
    res = resolver.resolve("Bitim 100001 va 915861525 haqida")
    assert res.deal_nos == [100001]
    assert res.inns == ["915861525"]
    assert "100001" in res.prompt_block() and "deal OR contract" in res.prompt_block()


# --------------------------------------------------------------------------- prompt block / perf
def test_empty_resolution_gives_empty_block(resolver: EntityResolver) -> None:
    assert Resolution([], [], [], [], []).prompt_block() == ""
    assert resolver.resolve("Qancha bitim tuzilgan?").prompt_block() == ""


def test_prompt_block_format(resolver: EntityResolver) -> None:
    block = resolver.resolve("Qojo Invest 2024 yilda qancha paxta sotgan? Broker BK045").prompt_block()
    assert block.startswith("RESOLVED ENTITIES")
    assert "- products: 520100 Хлопок-сырец / Paxta xomashyosi (matched 'paxta', 100)" in block
    assert '915861525 "Qojo Invest" MChJ (Buxoro viloyati)' in block
    assert "- brokers: BK045" in block


def test_resolve_is_fast(resolver: EntityResolver) -> None:
    q = 'Сколько муки купила «Qojo Invest» у "Dojo Invest" в 2024?'
    resolver.resolve(q)  # warm-up
    started = time.perf_counter()
    resolver.resolve(q)
    assert (time.perf_counter() - started) < 0.05
