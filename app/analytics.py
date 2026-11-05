"""Deterministic analytics reports — fixed SQL written by us, no LLM, so nothing can be invented.

Reports: product (TN VED), company (INN), broker (code) and an overview of the whole database.
Text uses **bold** / __italic__ markers (rendered by app.format.answer_html). Volumes, amounts and
prices exclude cancelled deals; deal counts show the cancelled ones separately.
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from functools import lru_cache

from app.render import format_number, format_value
from app.script import UZ_CYR, base_lang, lat_to_cyr

TOP_N = 5
MAX_TARGETS = 3
MIN_PRODUCT_SCORE = 90

_T = {
    "uz": {
        "years": "Yillar bo'yicha", "deals": "bitim", "cancelled": "bekor", "amount": "so'm", "avg": "o'rtacha",
        "top_regions": "Top hududlar (sotuvchi ombori)", "top_sellers": "Top sotuvchilar", "top_buyers": "Top xaridorlar",
        "top_products": "Top tovarlar", "top_brokers": "Brokerlar", "top_clients": "Top mijozlar",
        "as_seller": "sotuvchi", "as_buyer": "xaridor", "region": "Hudud", "role": "Roli", "activity": "Faoliyati",
        "footer": "Manba: birja bitimlari bazasi (03.01.2022–30.10.2026). Hajm, summa va narxga bekor qilingan bitimlar kiritilmagan.",
        "overview": "Birja bitimlari: umumiy statistika", "total": "Jami", "none": "Bu obyekt bo'yicha bitimlar topilmadi.",
        "per": "so'm/",
    },
    "ru": {
        "years": "По годам", "deals": "сделок", "cancelled": "аннул.", "amount": "сум", "avg": "средняя",
        "top_regions": "Топ регионов (склад продавца)", "top_sellers": "Топ продавцов", "top_buyers": "Топ покупателей",
        "top_products": "Топ товаров", "top_brokers": "Брокеры", "top_clients": "Топ клиентов",
        "as_seller": "продавец", "as_buyer": "покупатель", "region": "Регион", "role": "Роль", "activity": "Деятельность",
        "footer": "Источник: база биржевых сделок (03.01.2022–30.10.2026). Объём, сумма и цена — без аннулированных сделок.",
        "overview": "Биржевые сделки: общая статистика", "total": "Всего", "none": "По этому объекту сделок не найдено.",
        "per": "сум/",
    },
}


def _labels(lang: str) -> dict[str, str]:
    if lang == UZ_CYR:
        return {k: lat_to_cyr(v) for k, v in _T["uz"].items()}
    return _T[base_lang(lang) if base_lang(lang) in _T else "ru"]


def _n(value: float | int | None) -> str:
    return "—" if value is None else format_number(value)


def _unit(unit: str, lang: str) -> str:
    return format_value(unit, None, lang, "unit")


@dataclass(frozen=True)
class Target:
    kind: str   # "p" product, "c" company, "b" broker
    key: str    # TN VED code, INN or broker code
    title: str  # button caption

    def callback(self, lang: str) -> str:
        return f"an|{lang}|{self.kind}|{self.key}"  # Telegram limit: 64 bytes


def parse_callback(data: str) -> tuple[str, Target] | None:
    parts = data.split("|")
    if len(parts) != 4 or parts[0] != "an" or parts[2] not in ("p", "c", "b"):
        return None
    return parts[1], Target(parts[2], parts[3], "")


def pick_targets(resolution, lang: str = "uz") -> list[Target]:
    """Only confidently resolved entities get a button; nothing resolved -> no button."""
    targets: list[Target] = []
    for c in resolution.companies[:MAX_TARGETS]:
        targets.append(Target("c", c.inn, c.name))
    for code in resolution.brokers:
        targets.append(Target("b", code, code))
    products = [p for p in resolution.products if p.score >= MIN_PRODUCT_SCORE]
    if products:
        p = products[0]
        name = getattr(p, "name_ru", p.name_uz) if base_lang(lang) == "ru" else _own_text(p.name_uz, lang)
        targets.append(Target("p", p.tnved, name))
    for inn in resolution.inns:
        if all(t.key != inn for t in targets):
            targets.append(Target("c", inn, f"ИНН {inn}" if base_lang(lang) == "ru" else _own_text(f"STIR {inn}", lang)))
    return targets[:MAX_TARGETS]


# ----------------------------------------------------------------------------- reports
def report(con: sqlite3.Connection, target: Target, lang: str) -> str:
    if target.kind == "p":
        return product_report(con, target.key, lang)
    if target.kind == "c":
        return company_report(con, target.key, lang)
    return broker_report(con, target.key, lang)


def _year_lines(rows: list[tuple], lang: str, L: dict[str, str]) -> list[str]:
    """rows: year, unit, deals_total, cancelled, volume, amount_uzs."""
    out = []
    for year, unit, total, cancelled, volume, amount in rows:
        line = f"{year}: **{_n(total)}** {L['deals']} ({L['cancelled']} {_n(cancelled)})"
        if volume:
            line += f" · {_n(volume)} {_unit(unit, lang)}"
            if amount:
                line += f" · {_n(amount)} {L['amount']} · {L['avg']} {_n(amount / volume)} {L['per']}{_unit(unit, lang)}"
        out.append(line)
    return out


def product_report(con: sqlite3.Connection, tnved: str, lang: str) -> str:
    L = _labels(lang)
    row = con.execute("SELECT name_ru, name_uz FROM products WHERE tnved = ?", (tnved,)).fetchone()
    if not row:
        return L["none"]
    name = row[0] if base_lang(lang) == "ru" else (lat_to_cyr(row[1]) if lang == UZ_CYR else row[1])
    years = con.execute(
        "SELECT year, unit, COUNT(*), SUM(is_cancelled), SUM(CASE WHEN is_cancelled = 0 THEN volume END), "
        "SUM(CASE WHEN is_cancelled = 0 THEN amount_uzs END) FROM deals WHERE tnved = ? GROUP BY year, unit ORDER BY year, unit",
        (tnved,)).fetchall()
    if not years:
        return L["none"]
    regions = con.execute(
        "SELECT region, unit, SUM(volume) v FROM deals WHERE tnved = ? AND is_cancelled = 0 GROUP BY region, unit "
        "ORDER BY v DESC LIMIT ?", (tnved, TOP_N)).fetchall()
    parts = [f"📊 **{name}** (TN VED {tnved})", "", f"__{L['years']}:__", *_year_lines(years, lang, L)]
    parts += ["", f"__{L['top_regions']}:__"]
    parts += [f"{i}. {r} — **{_n(v)}** {_unit(u, lang)}" for i, (r, u, v) in enumerate(regions, 1)]
    for side, label in (("seller_inn", L["top_sellers"]), ("buyer_inn", L["top_buyers"])):
        top = con.execute(
            f"SELECT d.{side}, p.name, d.unit, SUM(d.volume) v FROM deals d LEFT JOIN participants p ON p.inn = d.{side} "
            f"WHERE d.tnved = ? AND d.is_cancelled = 0 GROUP BY d.{side}, d.unit ORDER BY v DESC LIMIT ?",
            (tnved, TOP_N)).fetchall()
        parts += ["", f"__{label}:__"]
        parts += [f"{i}. {nm or inn} ({inn}) — **{_n(v)}** {_unit(u, lang)}" for i, (inn, nm, u, v) in enumerate(top, 1)]
    parts += ["", f"__{L['footer']}__"]
    return "\n".join(parts)


def company_report(con: sqlite3.Connection, inn: str, lang: str) -> str:
    L = _labels(lang)
    info = con.execute("SELECT name, region, role, activity FROM participants WHERE inn = ?", (inn,)).fetchone()
    if not info:
        return L["none"]
    name, region, role, activity = info
    years = con.execute(
        "SELECT year, SUM(seller_inn = :i), SUM(buyer_inn = :i), SUM(is_cancelled), "
        "SUM(CASE WHEN is_cancelled = 0 THEN amount_uzs END), COUNT(*) FROM deals "
        "WHERE seller_inn = :i OR buyer_inn = :i GROUP BY year ORDER BY year", {"i": inn}).fetchall()
    parts = [f"📊 **{name}** (STIR {inn})" if base_lang(lang) == "uz" else f"📊 **{name}** (ИНН {inn})"]
    parts.append(f"{L['region']}: {region or '—'} · {L['role']}: {format_value(role, None, lang, 'role')}"
                 + (f" · {L['activity']}: {activity}" if activity else ""))
    if not years:
        return "\n".join(parts + ["", L["none"]])
    parts += ["", f"__{L['years']}:__"]
    for year, as_seller, as_buyer, cancelled, amount, total in years:
        parts.append(f"{year}: **{_n(total)}** {L['deals']} ({L['as_seller']} {_n(as_seller)}, {L['as_buyer']} {_n(as_buyer)}, "
                     f"{L['cancelled']} {_n(cancelled)}) · {_n(amount or 0)} {L['amount']}")
    products = con.execute(
        "SELECT CASE WHEN :ru THEN product_canon_ru ELSE product_canon_uz END, COUNT(*) c FROM deals "
        "WHERE (seller_inn = :i OR buyer_inn = :i) GROUP BY tnved ORDER BY c DESC LIMIT :n",
        {"i": inn, "ru": base_lang(lang) == "ru", "n": TOP_N}).fetchall()
    parts += ["", f"__{L['top_products']}:__"]
    parts += [f"{i}. {_own_text(p, lang)} — **{_n(c)}** {L['deals']}" for i, (p, c) in enumerate(products, 1)]
    brokers = con.execute(
        "SELECT CASE WHEN seller_inn = :i THEN seller_broker ELSE buyer_broker END b, COUNT(*) c FROM deals "
        "WHERE seller_inn = :i OR buyer_inn = :i GROUP BY b ORDER BY c DESC LIMIT 3", {"i": inn}).fetchall()
    parts += ["", f"__{L['top_brokers']}:__"]
    parts += [f"{b} — **{_n(c)}** {L['deals']}" for b, c in brokers]
    parts += ["", f"__{L['footer']}__"]
    return "\n".join(parts)


def broker_report(con: sqlite3.Connection, code: str, lang: str) -> str:
    L = _labels(lang)
    info = con.execute("SELECT name, region FROM brokers WHERE code = ?", (code,)).fetchone()
    if not info:
        return L["none"]
    name, region = info
    where = "seller_broker = :b OR buyer_broker = :b"  # each deal counted once even if the broker is on both sides
    years = con.execute(
        f"SELECT year, COUNT(*), SUM(is_cancelled), SUM(CASE WHEN is_cancelled = 0 THEN amount_uzs END) FROM deals "
        f"WHERE {where} GROUP BY year ORDER BY year", {"b": code}).fetchall()
    parts = [f"📊 **{name}** ({code})", f"{L['region']}: {region or '—'}"]
    if not years:
        return "\n".join(parts + ["", L["none"]])
    parts += ["", f"__{L['years']}:__"]
    parts += [f"{y}: **{_n(t)}** {L['deals']} ({L['cancelled']} {_n(c)}) · {_n(a or 0)} {L['amount']}" for y, t, c, a in years]
    products = con.execute(
        f"SELECT CASE WHEN :ru THEN product_canon_ru ELSE product_canon_uz END, COUNT(*) c FROM deals WHERE {where} "
        f"GROUP BY tnved ORDER BY c DESC LIMIT :n", {"b": code, "ru": base_lang(lang) == "ru", "n": TOP_N}).fetchall()
    parts += ["", f"__{L['top_products']}:__"]
    parts += [f"{i}. {_own_text(p, lang)} — **{_n(c)}** {L['deals']}" for i, (p, c) in enumerate(products, 1)]
    clients = con.execute(
        "SELECT c.inn, p.name, COUNT(*) n FROM (SELECT seller_inn inn FROM deals WHERE seller_broker = :b "
        "UNION ALL SELECT buyer_inn FROM deals WHERE buyer_broker = :b) c LEFT JOIN participants p ON p.inn = c.inn "
        "GROUP BY c.inn ORDER BY n DESC LIMIT :n", {"b": code, "n": TOP_N}).fetchall()
    parts += ["", f"__{L['top_clients']}:__"]
    parts += [f"{i}. {nm or inn} ({inn}) — **{_n(n)}** {L['deals']}" for i, (inn, nm, n) in enumerate(clients, 1)]
    parts += ["", f"__{L['footer']}__"]
    return "\n".join(parts)


@lru_cache(maxsize=4)
def _overview_rows(db_path: str) -> tuple:
    from app.sql_guard import open_db
    con = open_db(db_path)
    try:
        years = con.execute(
            "SELECT year, COUNT(*), SUM(is_cancelled), SUM(CASE WHEN is_cancelled = 0 THEN amount_uzs END) "
            "FROM deals GROUP BY year ORDER BY year").fetchall()
        products = con.execute(
            "SELECT tnved, product_canon_ru, product_canon_uz, SUM(amount_uzs) s FROM deals WHERE is_cancelled = 0 "
            "GROUP BY tnved ORDER BY s DESC LIMIT 10").fetchall()
        brokers = con.execute(
            "SELECT b.code, b.name, COUNT(*) n FROM (SELECT seller_broker code, deal_no FROM deals "
            "UNION SELECT buyer_broker, deal_no FROM deals) x JOIN brokers b ON b.code = x.code "
            "GROUP BY b.code ORDER BY n DESC LIMIT ?", (TOP_N,)).fetchall()
        regions = con.execute(
            "SELECT region, COUNT(*) n FROM deals GROUP BY region ORDER BY n DESC LIMIT ?", (TOP_N,)).fetchall()
    finally:
        con.close()
    return years, products, brokers, regions


def overview_report(db_path: str, lang: str) -> str:
    L = _labels(lang)
    years, products, brokers, regions = _overview_rows(db_path)
    total = sum(y[1] for y in years)
    parts = [f"📊 **{L['overview']}**", "", f"__{L['years']}:__"]
    parts += [f"{y}: **{_n(t)}** {L['deals']} ({L['cancelled']} {_n(c)}) · {_n(a or 0)} {L['amount']}" for y, t, c, a in years]
    parts.append(f"{L['total']}: **{_n(total)}** {L['deals']}")
    parts += ["", f"__{L['top_products']} ({L['amount']}):__"]
    parts += [f"{i}. {_own_text(ru if base_lang(lang) == 'ru' else uz, lang)} — **{_n(s)}** {L['amount']}"
              for i, (_, ru, uz, s) in enumerate(products, 1)]
    parts += ["", f"__{L['top_brokers']}:__"]
    parts += [f"{i}. {code} — {name}: **{_n(n)}** {L['deals']}" for i, (code, name, n) in enumerate(brokers, 1)]
    parts += ["", f"__{L['top_regions']}:__"]
    parts += [f"{i}. {r} — **{_n(n)}** {L['deals']}" for i, (r, n) in enumerate(regions, 1)]
    parts += ["", f"__{L['footer']}__"]
    return "\n".join(parts)


def _own_text(text: str | None, lang: str) -> str:
    """Canonical product names are ours (dictionary), so they may follow the user's script."""
    if not text:
        return "—"
    return lat_to_cyr(text) if lang == UZ_CYR else text
