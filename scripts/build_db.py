"""Load the raw CSV files into a normalized SQLite database.

Usage: python scripts/build_db.py [raw_dir] [db_path]
"""

from __future__ import annotations

import csv
import glob
import os
import sqlite3
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.dictionaries import PRODUCTS, REGION_RU_TO_UZ  # noqa: E402
from app.normalize import (  # noqa: E402
    company_key,
    parse_date,
    parse_grade_class,
    parse_number,
    parse_percent,
    translit,
)

SCHEMA = """
DROP TABLE IF EXISTS deals; DROP TABLE IF EXISTS contracts; DROP TABLE IF EXISTS participants;
DROP TABLE IF EXISTS brokers; DROP TABLE IF EXISTS usd_rates; DROP TABLE IF EXISTS products;

CREATE TABLE products (
  tnved TEXT PRIMARY KEY, name_ru TEXT, name_uz TEXT, aliases TEXT
);
CREATE TABLE brokers (
  code TEXT PRIMARY KEY, name TEXT, inn TEXT, region TEXT, name_key TEXT
);
CREATE TABLE participants (
  inn TEXT PRIMARY KEY, name TEXT, region TEXT, activity TEXT, role TEXT, vat_payer INTEGER, name_key TEXT
);
CREATE TABLE usd_rates (date TEXT PRIMARY KEY, rate REAL);
CREATE TABLE contracts (
  contract_no TEXT PRIMARY KEY, product_name TEXT, brand TEXT, size TEXT, sort TEXT, kind TEXT, klass TEXT,
  tnved TEXT, product_group TEXT, category TEXT, industry TEXT, unit TEXT, lot REAL, currency TEXT,
  base_price REAL, deposit_pct REAL, delivery_basis TEXT, region_ru TEXT, region TEXT, warehouse TEXT,
  trade_type TEXT, contract_type TEXT, contract_form TEXT, payment_days INTEGER, delivery_days INTEGER,
  packaging TEXT, seller_inn TEXT, reg_date TEXT, valid_until TEXT,
  product_canon_ru TEXT, product_canon_uz TEXT, product_key TEXT
);
CREATE TABLE deals (
  deal_no INTEGER PRIMARY KEY, deal_date TEXT, deal_time TEXT, year INTEGER, month INTEGER,
  trade_type TEXT, quantity REAL, amount REAL, start_price REAL, contract_no TEXT, product TEXT,
  lot REAL, unit TEXT, region TEXT, contract_type TEXT, contract_form TEXT, status TEXT,
  seller_inn TEXT, buyer_inn TEXT, seller_broker TEXT, buyer_broker TEXT,
  payment_date TEXT, delivery_date TEXT, delivered_lots REAL,
  -- derived
  volume REAL, unit_price REAL, currency TEXT, usd_rate REAL, amount_uzs REAL,
  tnved TEXT, product_canon_ru TEXT, product_canon_uz TEXT, product_key TEXT, sort_no INTEGER, class_no INTEGER,
  delivered_volume REAL, is_cancelled INTEGER, payment_delay_days INTEGER, delivery_delay_days INTEGER
);
"""

INDEXES = """
CREATE INDEX ix_deals_date ON deals(deal_date);
CREATE INDEX ix_deals_year_month ON deals(year, month);
CREATE INDEX ix_deals_contract ON deals(contract_no);
CREATE INDEX ix_deals_tnved ON deals(tnved);
CREATE INDEX ix_deals_seller ON deals(seller_inn);
CREATE INDEX ix_deals_buyer ON deals(buyer_inn);
CREATE INDEX ix_deals_sbroker ON deals(seller_broker);
CREATE INDEX ix_deals_bbroker ON deals(buyer_broker);
CREATE INDEX ix_deals_status ON deals(status);
CREATE INDEX ix_deals_region ON deals(region);
CREATE INDEX ix_deals_product_key ON deals(product_key);
CREATE INDEX ix_contracts_tnved ON contracts(tnved);
CREATE INDEX ix_contracts_seller ON contracts(seller_inn);
CREATE INDEX ix_participants_key ON participants(name_key);
"""


def read_csv(path: str):
    with open(path, encoding="utf-8", newline="") as fh:
        yield from csv.DictReader(fh)


def load_products(cur: sqlite3.Cursor) -> None:
    cur.executemany(
        "INSERT INTO products VALUES (?,?,?,?)",
        [(code, ru, uz, "|".join(al)) for code, (ru, uz, al) in PRODUCTS.items()],
    )


def load_brokers(cur: sqlite3.Cursor, raw: str) -> None:
    cur.executemany(
        "INSERT INTO brokers VALUES (?,?,?,?,?)",
        [(r["Код брокера"], r["Наименование"], r["ИНН"], r["Регион"], company_key(r["Наименование"]))
         for r in read_csv(f"{raw}/brokers.csv")],
    )


def load_participants(cur: sqlite3.Cursor, raw: str) -> None:
    cur.executemany(
        "INSERT INTO participants VALUES (?,?,?,?,?,?,?)",
        [(r["ИНН"], r["Наименование"], r["Регион"], r["Вид деятельности"], r["Роль"],
          1 if r["Плательщик НДС"] == "Да" else 0, company_key(r["Наименование"]))
         for r in read_csv(f"{raw}/participants.csv")],
    )


def load_rates(cur: sqlite3.Cursor, raw: str) -> dict[str, float]:
    rates = {parse_date(r["Дата"]): float(r["Курс"]) for r in read_csv(f"{raw}/usd_rates.csv")}
    cur.executemany("INSERT INTO usd_rates VALUES (?,?)", rates.items())
    return rates


def load_contracts(cur: sqlite3.Cursor, raw: str) -> dict[str, dict]:
    contracts: dict[str, dict] = {}
    rows = []
    for r in read_csv(f"{raw}/contracts.csv"):
        code = r["Код ТН ВЭД"]
        canon = PRODUCTS.get(code, (r["Наименование продукта"], r["Наименование продукта"], []))
        row = (
            r["Номер контракта"], r["Наименование продукта"], r["Марка товара"], r["Размер товара"],
            r["Сорт товара"], r["Тип товара"], r["Класс товара"], code, r["Группа товара"],
            r["Категория товара"], r["Отрасль промышленности"], r["Единица измерения"], parse_number(r["Лот"]),
            r["Валюта"], parse_number(r["Базисная цена"]), parse_percent(r["Сумма залога"]), r["Базис поставки"],
            r["Регион"], REGION_RU_TO_UZ.get(r["Регион"], r["Регион"]), r["Адрес склада"], r["Тип торгов"],
            r["Тип контракта"], r["Форма контракта"], int(r["Срок оплаты"]), int(r["Срок поставки"]),
            r["Упаковка"], r["ИНН продавца"], parse_date(r["Дата регистрации"]), parse_date(r["Действует до"]),
            canon[0], canon[1], translit(canon[0]),
        )
        rows.append(row)
        contracts[r["Номер контракта"]] = {
            "tnved": code, "currency": r["Валюта"], "canon_ru": canon[0], "canon_uz": canon[1],
            "payment_days": int(r["Срок оплаты"]), "delivery_days": int(r["Срок поставки"]),
        }
    cur.executemany(f"INSERT INTO contracts VALUES ({','.join('?' * 32)})", rows)
    return contracts


def _days(a: str | None, b: str | None) -> int | None:
    import datetime as dt
    if not a or not b:
        return None
    return (dt.date.fromisoformat(b) - dt.date.fromisoformat(a)).days


def deal_row(r: dict, c: dict, rates: dict[str, float]) -> tuple:
    date = parse_date(r["Дата сделки"])
    qty = parse_number(r["Количество"])
    amount = parse_number(r["Сумма сделки"])
    lot = parse_number(r["Лот"])
    volume = qty * lot
    delivered = parse_number(r["Поставлено"])
    is_usd = c["currency"] == "Доллар США"
    rate = rates.get(date) if is_usd else None
    pay = parse_date(r["Дата оплаты"])
    dlv = parse_date(r["Дата поставки"])
    sort_no, class_no = parse_grade_class(r["Наименование товара"])
    pay_delay = _days(date, pay)
    dlv_delay = _days(pay, dlv)
    return (
        int(r["Номер сделки"]), date, r["Время сделки"], int(date[:4]), int(date[5:7]),
        r["Тип торгов"], qty, amount, parse_number(r["Стартовая цена"]), r["Номер контракта"],
        r["Наименование товара"], lot, r["Единица измерения"], r["Регион"], r["Тип контракта"],
        r["Форма контракта"], r["Состояние сделки"], r["ИНН продавца"], r["ИНН покупателя"],
        r["Брокер продавца"], r["Брокер покупателя"], pay, dlv, delivered,
        volume, amount / volume if volume else None, c["currency"], rate,
        amount * rate if is_usd else amount,
        c["tnved"], c["canon_ru"], c["canon_uz"], translit(c["canon_ru"]), sort_no, class_no,
        delivered * lot if delivered is not None else None,
        1 if r["Состояние сделки"].startswith("Аннулирован") else 0,
        None if pay_delay is None else pay_delay - c["payment_days"],
        None if dlv_delay is None else dlv_delay - c["delivery_days"],
    )


def load_deals(cur: sqlite3.Cursor, raw: str, contracts: dict, rates: dict) -> int:
    total = 0
    for path in sorted(glob.glob(f"{raw}/deals_*.csv")):
        batch = [deal_row(r, contracts[r["Номер контракта"]], rates) for r in read_csv(path)]
        cur.executemany(f"INSERT INTO deals VALUES ({','.join('?' * 39)})", batch)
        total += len(batch)
        print(f"  {os.path.basename(path)}: {len(batch)}")
    return total


def main(raw: str, db_path: str) -> None:
    if os.path.exists(db_path):
        os.remove(db_path)
    con = sqlite3.connect(db_path)
    cur = con.cursor()
    cur.executescript(SCHEMA)
    load_products(cur)
    load_brokers(cur, raw)
    load_participants(cur, raw)
    rates = load_rates(cur, raw)
    contracts = load_contracts(cur, raw)
    print("contracts:", len(contracts))
    total = load_deals(cur, raw, contracts, rates)
    print("deals:", total)
    cur.executescript(INDEXES)
    con.commit()
    con.execute("VACUUM")
    con.close()
    print("done ->", db_path, f"{os.path.getsize(db_path) / 1e6:.1f} MB")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "data/raw/uzex_spot_data",
         sys.argv[2] if len(sys.argv) > 2 else "data/uzex.db")
