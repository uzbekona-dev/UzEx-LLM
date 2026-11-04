"""Schema and rules shown to the LLM. Kept in one place so prompt and DB never drift."""

from app.dictionaries import DATA_MAX_DATE, DATA_MIN_DATE, PRODUCTS, REGIONS

_PRODUCT_LINES = "\n".join(f"  {code}: {ru} / {uz}" for code, (ru, uz, _) in PRODUCTS.items())
_REGION_LINES = "\n".join(f"  '{uz}' (RU: {ru})" for uz, ru, _ in REGIONS)

SCHEMA_DOC = f"""
SQLite database of a commodity exchange (UZEX-like). Data period: {DATA_MIN_DATE} .. {DATA_MAX_DATE} (deals), states as of end of {DATA_MAX_DATE}.
All text values are stored EXACTLY as listed below. Dates are ISO 'YYYY-MM-DD'.

TABLE deals (500 000 rows) — one row per exchange deal
  deal_no INTEGER PK          -- deal number (some numbers are skipped; a missing number means the deal does not exist)
  deal_date TEXT, deal_time TEXT, year INT, month INT
  trade_type TEXT             -- 'Английский аукцион' | 'Обратный аукцион' | 'Двусторонний аукцион'
  quantity REAL               -- number of lots bought
  amount REAL                 -- deal sum in the contract currency (see currency)
  start_price REAL            -- starting price per unit (NOT the final price)
  contract_no TEXT            -- FK contracts.contract_no
  product TEXT                -- product string as written by the seller (free text, inconsistent spelling; do NOT filter on it, use tnved/product_key)
  lot REAL, unit TEXT         -- units per lot; unit in 'тонна','килограмм','литр','штука','куб.метр','кв.метр','метр'
  region TEXT                 -- seller warehouse region, Uzbek-Latin names (list below)
  contract_type TEXT          -- 'Внутренний' | 'Экспортный'
  contract_form TEXT          -- 'Спот' | 'Форвард' | 'Фьючерс'
  status TEXT                 -- 'Новый','Не подписан','Заключен','Ждёт оплату','Оплачен','Исполнен','Исполнен(Частично)','Аннулирован(Не оплачен)'
  seller_inn TEXT, buyer_inn TEXT        -- FK participants.inn
  seller_broker TEXT, buyer_broker TEXT  -- FK brokers.code (e.g. 'BK045')
  payment_date TEXT, delivery_date TEXT  -- NULL if not happened yet
  delivered_lots REAL                    -- lots actually delivered (NULL if none)
  -- derived columns (already computed, use them):
  volume REAL          -- quantity * lot, in `unit`  (README: deal volume)
  unit_price REAL      -- amount / volume, in contract currency per unit (README: final price per unit)
  currency TEXT        -- 'Узбекский сум' (all Внутренний) | 'Доллар США' (all Экспортный)
  usd_rate REAL        -- USD rate on deal_date (only for USD deals)
  amount_uzs REAL      -- amount in UZS (amount * usd_rate for USD deals, else amount)
  tnved TEXT           -- product code from the contract (STABLE product key, use this to filter products)
  product_canon_ru TEXT, product_canon_uz TEXT  -- canonical product name for the tnved
  product_key TEXT     -- latin lowercase canonical name
  sort_no INT, class_no INT   -- parsed grade/class (0 = высший, 1,2,3,4); NULL if not stated
  delivered_volume REAL       -- delivered_lots * lot
  is_cancelled INT            -- 1 if status = 'Аннулирован(Не оплачен)' (deal did not happen)
  payment_delay_days INT      -- (payment_date - deal_date) - contract payment_days; >0 means paid late; NULL if unpaid
  delivery_delay_days INT     -- (delivery_date - payment_date) - contract delivery_days; >0 means delivered late

TABLE contracts (6 616 rows) — contract card filled by the seller
  contract_no TEXT PK, product_name TEXT, brand TEXT, size TEXT, sort TEXT, kind TEXT, klass TEXT,
  tnved TEXT, product_group TEXT ('Высоколиквидные товары'|'Прочие товары'), category TEXT, industry TEXT,
  unit TEXT, lot REAL, currency TEXT, base_price REAL (price per unit at registration), deposit_pct REAL,
  delivery_basis TEXT ('EXW','FCA','DAP','CPT'...), region_ru TEXT (Russian name), region TEXT (Uzbek-Latin name),
  warehouse TEXT (address), trade_type, contract_type, contract_form,
  payment_days INT (calendar days after deal to pay), delivery_days INT (calendar days after payment to deliver),
  packaging TEXT, seller_inn TEXT, reg_date TEXT, valid_until TEXT,
  product_canon_ru, product_canon_uz, product_key

TABLE participants (14 392 rows): inn TEXT PK (9 digits), name TEXT, region TEXT (Uzbek-Latin), activity TEXT,
  role TEXT ('Продавец' | 'Покупатель'), vat_payer INT (1/0), name_key TEXT (latin lowercase name without quotes/legal form, for searching)
TABLE brokers (120 rows): code TEXT PK ('BK001'..'BK120'), name TEXT, inn TEXT, region TEXT, name_key TEXT
TABLE usd_rates: date TEXT PK ('2022-01-01'..'2026-10-31'), rate REAL (UZS per 1 USD)
TABLE products: tnved TEXT PK, name_ru, name_uz, aliases

PRODUCT CODES (tnved -> RU / UZ):
{_PRODUCT_LINES}

REGIONS (deals.region / participants.region values):
{_REGION_LINES}

SQL FUNCTIONS available: ckey(text) -> same latin key as name_key (use: p.name_key LIKE '%' || ckey('Qojo Invest') || '%').
"""

RULES = """
RULES FOR WRITING SQL
1. Only ONE read-only SELECT (CTEs allowed). No modifications. Always add LIMIT (max 50) unless aggregating to few rows.
2. Products: filter by deals.tnved (or product_key), never by free-text `product`. If the question names a grade/class, add sort_no / class_no.
3. Companies: match on participants.name_key with ckey(); if the user gives an INN (9 digits) use inn. Always SELECT inn and name so homonyms are visible. If a name may match several companies, GROUP BY inn so each company is shown separately.
4. Brokers: by code 'BKxxx' or brokers.name_key. A broker takes part as seller_broker OR buyer_broker — count both unless the question says which side. A deal where the same broker is on both sides counts ONCE: use COUNT(DISTINCT deal_no) or UNION (not UNION ALL) in rankings.
5. Volume = volume column (quantity*lot), never quantity alone unless the question asks for lots. Never sum volumes across different `unit`s — GROUP BY unit. Never sum `amount` across currencies — use amount_uzs or GROUP BY currency.
6. Final price per unit = unit_price. start_price is the starting price. For an "average price" question return BOTH AVG(unit_price) AS avg_price AND SUM(amount)/SUM(volume) AS weighted_avg_price (same currency/unit) and show both in the template.
7. "Sold / traded / turnover" by default EXCLUDES cancelled deals (is_cancelled = 0) — and also return the cancelled figure separately when cheap (e.g. SUM(CASE WHEN is_cancelled=1 ...)). Counting deals ("how many deals") includes all statuses unless asked otherwise. CONSISTENCY: every SUM/AVG/COUNT in one query must use the same cancelled-filter (if the sum excludes cancelled, the deal count next to it must exclude them too — put is_cancelled = 0 in WHERE and give the cancelled count via a separate CASE column).
8. Dates: data covers 2022-01-03..2026-10-30 only. "This year"/"last month" are relative to 2026-10-30. If the question is outside the period, mark it unanswerable.
9. For a single deal/contract/company question, select all useful columns (deal_no, deal_date, product, volume, unit, amount, currency, status, seller/buyer inn+name, brokers).
10. Deal numbers: exact match only. Never substitute a nearby number. A 6-digit number after shartnoma/договор/контракт is contracts.contract_no (deals.contract_no links to it); after bitim/сделка it is deals.deal_no.
11. If the question cannot be answered from these tables (e.g. forecasts, reasons, people, phones, data outside the period, products not in the list), set answerable=false and explain why — do NOT invent a query that returns something else.
"""
