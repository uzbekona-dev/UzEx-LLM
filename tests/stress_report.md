# Golden check 2026-11-05 04:12 model=gemini:gemini-3.5-flash

**45/50 passed**

| id | result | time | missing |
|---|---|---|---|
| s01 | ok | 13.5s |  |
| s02 | ok | 11.6s |  |
| s03 | ok | 8.9s |  |
| s04 | ok | 9.6s |  |
| s05 | FAIL | 16.0s | string '2026-08-14'; string '2026-10-30' |
| s06 | ok | 13.2s |  |
| s07 | FAIL | 6.5s | string '2022-01-03' |
| s08 | ok | 8.4s |  |
| s09 | ok | 9.0s |  |
| s10 | FAIL | 11.2s | number 5369 |
| s11 | ok | 21.3s |  |
| s12 | ok | 5.5s |  |
| s13 | FAIL | 9.9s | number 1 |
| s14 | ok | 5.6s |  |
| s15 | ok | 8.2s |  |
| s16 | ok | 5.8s |  |
| s17 | ok | 7.1s |  |
| s18 | ok | 8.4s |  |
| s19 | ok | 8.1s |  |
| s20 | ok | 11.5s |  |
| s21 | ok | 6.1s |  |
| s22 | ok | 6.5s |  |
| s23 | ok | 5.9s |  |
| s24 | ok | 15.0s |  |
| s25 | ok | 7.3s |  |
| s26 | ok | 11.9s |  |
| s27 | ok | 14.7s |  |
| s28 | ok | 11.3s |  |
| s29 | ok | 18.0s |  |
| s30 | ok | 6.2s |  |
| s31 | FAIL | 7.2s | string '2024-12-31' |
| s32 | ok | 7.6s |  |
| s33 | ok | 10.9s |  |
| s34 | ok | 13.0s |  |
| s35 | ok | 11.8s |  |
| s36 | ok | 11.6s |  |
| s37 | ok | 14.4s |  |
| s38 | ok | 10.8s |  |
| s39 | ok | 10.1s |  |
| s40 | ok | 8.3s |  |
| s41 | ok | 3.1s |  |
| s42 | ok | 3.2s |  |
| s43 | ok | 9.2s |  |
| s44 | ok | 2.0s |  |
| s45 | ok | 2.4s |  |
| s46 | ok | 2.7s |  |
| s47 | ok | 18.7s |  |
| s48 | ok | 10.9s |  |
| s49 | ok | 7.1s |  |
| s50 | ok | 6.9s |  |

## s01. В каком месяце 2024 года было больше всего сделок?
tags: deals, max-group, monthly, ru
**Javob:** В 2024 году больше всего сделок было в **10-м месяце** — всего **16 824** сделок, из которых **15 706** исполнены или находятся в процессе.

Показан месяц с максимальным общим числом сделок.
```sql
SELECT month, COUNT(*) AS deals_total, SUM(CASE WHEN is_cancelled = 0 THEN 1 ELSE 0 END) AS deals_active FROM deals WHERE year = 2024 GROUP BY month ORDER BY deals_total DESC LIMIT 1
```
answerable=True ok=True time=13.5s missing=[]

## s02. Qaysi yilda eng ko'p paxta sotilgan?
tags: deals, max-group, volume, product, uz
**Javob:** Eng ko'p paxta xomashyosi **2025-yilda** sotilgan — **1 844 729 923 kg** (jami **30 894 ta** bitim, umumiy summasi 16 957 079 437 704.36 so'm).

Bekor qilingan bitimlar hisobga olinmadi.
```sql
SELECT year, unit, SUM(volume) AS total_volume, COUNT(*) AS deals_active, SUM(amount_uzs) AS total_amount_uzs FROM deals WHERE tnved = '520100' AND is_cancelled = 0 GROUP BY year, unit ORDER BY total_volume DESC LIMIT 1
```
answerable=True ok=True time=11.6s missing=[]

## s03. Сколько сделок по цементу было в 2024 году по сравнению с 2023?
tags: deals, yoy, product, multi, ru
**Javob:** Статистика сделок по портландцементу за 2023 и 2024 годы:
**2023 год**: всего **7 101** сделок (действующих — 6 613, аннулировано — 488)
**2024 год**: всего **8 220** сделок (действующих — 7 643, аннулировано — 577)

Показано общее число зарегистрированных сделок и количество фактически состоявшихся.
```sql
SELECT year, COUNT(*) AS deals_total, SUM(CASE WHEN is_cancelled = 0 THEN 1 ELSE 0 END) AS deals_active, SUM(CASE WHEN is_cancelled = 1 THEN 1 ELSE 0 END) AS deals_cancelled FROM deals WHERE tnved = '252329' AND year IN (2023, 2024) GROUP BY year ORDER BY year ASC
LIMIT 50
```
answerable=True ok=True time=8.9s missing=[]

## s04. 2025-yilda bug'doyning eng past va eng yuqori narxi qancha bo'lgan?
tags: deals, price, min-max, product, multi, uz
**Javob:** Natija (ma'lumotlardan to'g'ridan-to'g'ri):
unit: tonna; currency: so'm; min_price: 3 563 967; max_price: 5 674 988; deal_count: 7 996
```sql
SELECT unit, currency, MIN(unit_price) AS min_price, MAX(unit_price) AS max_price, COUNT(*) AS deal_count FROM deals WHERE tnved = '100199' AND year = 2025 AND is_cancelled = 0 GROUP BY unit, currency ORDER BY deal_count DESC LIMIT 10
```
answerable=True ok=True time=9.6s missing=[]

## s05. Первая и последняя сделка компании с ИНН 921973071?
tags: deals, company, first-last, multi, ru
**Javob:** Первая и последняя сделка компании **"So‘ni Steel" QK** (ИНН 921973071):
**Первая сделка**: № 564167 от 14.08.2026 — Профиль алюминиевый, 1 462 кг, 119 851 075.76 сум (статус «Исполнен»)
**Последняя сделка**: № 604317 от 30.10.2026 — Профиль алюминиевый, 2 275 кг, 208 285 532 сум (статус «Новый»)

Учтены сделки компании в качестве продавца и покупателя во всех статусах.
```sql
SELECT * FROM (SELECT 'Первая' AS kind, d.deal_no, d.deal_date, d.product_canon_ru AS product, d.volume, d.unit, d.amount, d.currency, d.status, p.name AS company_name FROM deals d JOIN participants p ON p.inn = '921973071' WHERE d.seller_inn = '921973071' OR d.buyer_inn = '921973071' ORDER BY d.deal_date ASC, d.deal_time ASC, d.deal_no ASC LIMIT 1) UNION ALL SELECT * FROM (SELECT 'Последняя' AS kind, d.deal_no, d.deal_date, d.product_canon_ru AS product, d.volume, d.unit, d.amount, d.currency, d.status, p.name AS company_name FROM deals d JOIN participants p ON p.inn = '921973071' WHERE d.seller_inn = '921973071' OR d.buyer_inn = '921973071' ORDER BY d.deal_date DESC, d.deal_time DESC, d.deal_no DESC LIMIT 1)
```
answerable=True ok=False time=16.0s missing=["string '2026-08-14'", "string '2026-10-30'"]

## s06. Ma'lumotlardagi eng oxirgi bitim qaysi?
tags: deals, latest, uz
**Javob:** Natija (ma'lumotlardan to'g'ridan-to'g'ri):
deal_no: 604956; deal_date: 2026-10-30; deal_time: 16:59:54; product: Paxta xomashyosi; volume: 9 414; unit: kg; amount: 97 848 174.6; currency: so'm; status: Yangi; seller_inn: 904661689; seller_name: TO‘LI AGRO MCHJ; buyer_inn: 936490057; buyer_name: "Lukim Invest" MChJ
```sql
SELECT d.deal_no, d.deal_date, d.deal_time, d.product_canon_uz AS product, d.volume, d.unit, d.amount, d.currency, d.status, d.seller_inn, ps.name AS seller_name, d.buyer_inn, pb.name AS buyer_name FROM deals d LEFT JOIN participants ps ON ps.inn = d.seller_inn LEFT JOIN participants pb ON pb.inn = d.buyer_inn ORDER BY d.deal_date DESC, d.deal_time DESC, d.deal_no DESC LIMIT 1
```
answerable=True ok=True time=13.2s missing=[]

## s07. Когда был зарегистрирован самый старый контракт и сколько контрактов зарегистрировано в тот день?
tags: contracts, oldest, ru
**Javob:** Самый старый контракт зарегистрирован **03.01.2022**. В этот день было зарегистрировано **41** контрактов.
```sql
SELECT reg_date AS min_reg_date, COUNT(*) AS contract_count FROM contracts WHERE reg_date = (SELECT MIN(reg_date) FROM contracts) GROUP BY reg_date
LIMIT 50
```
answerable=True ok=False time=6.5s missing=["string '2022-01-03'"]

## s08. 2025-yilda nechta xil tovar sotilgan?
tags: deals, distinct, product, uz
**Javob:** Natija (ma'lumotlardan to'g'ridan-to'g'ri):
distinct_products_count: 40; deals_count: 107 678; total_amount_uzs: 52 060 836 360 057.12
```sql
SELECT COUNT(DISTINCT tnved) AS distinct_products_count, COUNT(*) AS deals_count, SUM(amount_uzs) AS total_amount_uzs FROM deals WHERE year = 2025 AND is_cancelled = 0
LIMIT 50
```
answerable=True ok=True time=8.4s missing=[]

## s09. Сколько компаний из Андижанской области являются продавцами?
tags: participants, distinct, region, ru
**Javob:** Из Андижанской области в реестре зарегистрировано **23** компаний-продавцов.
```sql
SELECT COUNT(*) AS seller_count FROM participants WHERE region = 'Andijon viloyati' AND role = 'Продавец'
LIMIT 50
```
answerable=True ok=True time=9.0s missing=[]

## s10. Paxta xaridorlari orasida nechtasi QQS to'lovchi?
tags: participants, distinct, vat, product, uz
**Javob:** Natija (ma'lumotlardan to'g'ridan-to'g'ri):
total_buyers: 7 682; vat_payers_count: 5 366; non_vat_payers_count: 2 316
```sql
SELECT COUNT(DISTINCT pb.inn) AS total_buyers, COUNT(DISTINCT CASE WHEN pb.vat_payer = 1 THEN pb.inn END) AS vat_payers_count, COUNT(DISTINCT CASE WHEN pb.vat_payer = 0 THEN pb.inn END) AS non_vat_payers_count FROM deals d JOIN participants pb ON pb.inn = d.buyer_inn WHERE d.tnved = '520100' AND d.is_cancelled = 0
LIMIT 50
```
answerable=True ok=False time=11.2s missing=['number 5369']

## s11. Сколько брокеров участвовало в сделках в 2024 году?
tags: brokers, distinct, ru
**Javob:** В 2024 году в сделках участвовало **120** брокеров, из них в состоявшихся (не аннулированных) сделках — **120**.

Учтены брокеры, выступавшие со стороны продавца и/или покупателя.
```sql
WITH year_brokers AS (SELECT seller_broker AS broker_code, is_cancelled FROM deals WHERE year = 2024 AND seller_broker IS NOT NULL UNION ALL SELECT buyer_broker AS broker_code, is_cancelled FROM deals WHERE year = 2024 AND buyer_broker IS NOT NULL) SELECT COUNT(DISTINCT broker_code) AS total_brokers, COUNT(DISTINCT CASE WHEN is_cancelled = 0 THEN broker_code END) AS active_brokers FROM year_brokers
LIMIT 50
```
answerable=True ok=True time=21.3s missing=[]

## s12. STIR 975923536 kompaniyaning faoliyat turi qanday?
tags: participants, activity, uz
**Javob:** **"Pudexiz Plast" MChJ** (STIR 975923536) kompaniyasining faoliyat turi: **Торговая компания** (joylashgan hududi: Samarqand viloyati, rolib: Sotuvchi).
```sql
SELECT inn, name, activity, region, role FROM participants WHERE inn = '975923536'
LIMIT 50
```
answerable=True ok=True time=5.5s missing=[]

## s13. ИНН 900025242 — это продавец или покупатель, и является ли он плательщиком НДС?
tags: participants, role, vat, multi, ru
**Javob:** Компания **SHENO LOGISTIK MAS’ULIYATI CHEKLANGAN JAMIYATI** (ИНН 900025242) зарегистрирована как **Покупатель**. Статус плательщика НДС: **Да**.
```sql
SELECT inn, name, role, vat_payer, CASE WHEN vat_payer = 1 THEN 'Да' ELSE 'Нет' END AS vat_payer_text, region, activity FROM participants WHERE inn = '900025242'
LIMIT 50
```
answerable=True ok=False time=9.9s missing=['number 1']

## s14. BK077 brokerining nomi nima?
tags: brokers, code-to-name, uz
**Javob:** BK077 kodli broker nomi: **XUYILEZ BROKER MCHJ** (STIR: 909630776, hududi: Samarqand viloyati).
```sql
SELECT code, name, inn, region FROM brokers WHERE code = 'BK077'
LIMIT 50
```
answerable=True ok=True time=5.6s missing=[]

## s15. Какой код у брокера Toje Broker?
tags: brokers, name-to-code, ru
**Javob:** Брокер **"Toje Broker" MChJ**: код **BK064**, ИНН 905409943, регион: Buxoro viloyati.
```sql
SELECT code, name, inn, region FROM brokers WHERE code = 'BK064' OR name_key LIKE '%' || ckey('BK064') || '%'
LIMIT 50
```
answerable=True ok=True time=8.2s missing=[]

## s16. BK033 brokeri qaysi viloyatda?
tags: brokers, region, uz
**Javob:** **KEFI BROKER AJ** (BK033) brokeri **Namangan viloyati**da joylashgan.
```sql
SELECT code, name, region FROM brokers WHERE code = 'BK033'
LIMIT 50
```
answerable=True ok=True time=5.8s missing=[]

## s17. Какой адрес склада по контракту 104321?
tags: contracts, single-contract, warehouse, ru
**Javob:** По контракту № 104321 (Азот) адрес склада: **Наманганская область, Namangan, ул. Zarafshon, 16 ("Sofafot Chem" MChJ, ИНН 961469485)** (Наманганская область). Продавец: "Sofafot Chem" MChJ (ИНН 961469485).
```sql
SELECT c.contract_no, c.product_name, c.warehouse, c.region_ru, c.seller_inn, p.name AS seller_name FROM contracts c LEFT JOIN participants p ON p.inn = c.seller_inn WHERE c.contract_no = '104321'
LIMIT 50
```
answerable=True ok=True time=7.1s missing=[]

## s18. Shartnomalar yetkazib berish bazisi bo'yicha qanday taqsimlangan (EXW, FCA, DAP, CPT)?
tags: contracts, delivery-basis, multi, uz
**Javob:** Yetkazib berish bazalari bo'yicha shartnomalar taqsimoti:
EXW — **5 194 ta** shartnoma
FCA — **684 ta** shartnoma
DAP — **374 ta** shartnoma
CPT — **364 ta** shartnoma

Ro'yxatga olingan barcha shartnomalar hisobga olindi.
```sql
SELECT delivery_basis, COUNT(*) AS contract_count FROM contracts WHERE delivery_basis IS NOT NULL AND delivery_basis != '' GROUP BY delivery_basis ORDER BY contract_count DESC
LIMIT 50
```
answerable=True ok=True time=8.4s missing=[]

## s19. Сколько контрактов в форме Форвард и сколько Спот?
tags: contracts, form, multi, ru
**Javob:** Зарегистрировано **6 108** спотовых контрактов и **429** форвардных контрактов.
```sql
SELECT SUM(CASE WHEN contract_form = 'Спот' THEN 1 ELSE 0 END) AS spot_count, SUM(CASE WHEN contract_form = 'Форвард' THEN 1 ELSE 0 END) AS forward_count FROM contracts
LIMIT 50
```
answerable=True ok=True time=8.1s missing=[]

## s20. Ichki va eksport shartnomalari bo'yicha o'rtacha to'lov muddati necha kun?
tags: contracts, avg, multi, uz
**Javob:** Natija (ma'lumotlardan to'g'ridan-to'g'ri):
contract_type: Ichki; avg_payment_days: 10.68; contract_count: 6 468
contract_type: Eksport; avg_payment_days: 6.61; contract_count: 148
```sql
SELECT contract_type, AVG(payment_days) AS avg_payment_days, COUNT(*) AS contract_count FROM contracts WHERE contract_type IN ('Внутренний', 'Экспортный') GROUP BY contract_type
LIMIT 50
```
answerable=True ok=True time=11.5s missing=[]

## s21. Какой размер задатка (%) по контракту 103000?
tags: contracts, single-contract, deposit, ru
**Javob:** По контракту № 103000 (Хлопок-сырец) размер задатка составляет **15%**. Продавец: "Mo‘sho‘n Tekstil" MChJ (ИНН 980622707).
```sql
SELECT c.contract_no, c.product_canon_ru AS product, c.deposit_pct, c.seller_inn, p.name AS seller_name FROM contracts c LEFT JOIN participants p ON p.inn = c.seller_inn WHERE c.contract_no = '103000'
LIMIT 50
```
answerable=True ok=True time=6.1s missing=[]

## s22. 250000-bitimda boshlang'ich narx va yakuniy narx qancha?
tags: deals, single-deal, price, multi, uz
**Javob:** Natija (ma'lumotlardan to'g'ridan-to'g'ri):
deal_no: 250000; deal_date: 2023-10-12; product: Polipropilen; start_price: 15 136 635; unit_price: 18 995 667; currency: so'm; unit: tonna; status: Bajarilgan
```sql
SELECT deal_no, deal_date, product_canon_uz AS product, start_price, unit_price, currency, unit, status FROM deals WHERE deal_no = 250000
LIMIT 50
```
answerable=True ok=True time=6.5s missing=[]

## s23. Какой размер лота и количество лотов в сделке 400000?
tags: deals, single-deal, lot, multi, ru
**Javob:** По сделке № 400000 от 04.03.2025 (Портландцемент): количество лотов — **227**, размер одного лота — **1 т** (общий объём: 227 т).
```sql
SELECT deal_no, deal_date, product_canon_ru AS product, quantity, lot, unit, volume FROM deals WHERE deal_no = 400000
LIMIT 50
```
answerable=True ok=True time=5.9s missing=[]

## s24. Qisman bajarilgan bitimlar nechta?
tags: deals, status, partial, uz
**Javob:** Natija (ma'lumotlardan to'g'ridan-to'g'ri):
deal_count: 22 648; total_amount_uzs: 9 704 776 474 564.31
```sql
SELECT COUNT(*) AS deal_count, SUM(amount_uzs) AS total_amount_uzs FROM deals WHERE status = 'Исполнен(Частично)'
LIMIT 50
```
answerable=True ok=True time=15.0s missing=[]

## s25. Сколько фактически поставлено по сделке 300013?
tags: deals, single-deal, delivered, partial, ru
**Javob:** По сделке № 300013 от 15.04.2024 (Портландцемент) фактически поставлено **30 т** (30 лотов из 63). Статус сделки: «Исполнен(Частично)».
```sql
SELECT d.deal_no, d.deal_date, d.product_canon_ru AS product, d.quantity, d.delivered_lots, d.volume, d.delivered_volume, d.unit, d.status FROM deals d WHERE d.deal_no = 300013
LIMIT 50
```
answerable=True ok=True time=7.3s missing=[]

## s26. To'lovi kechiktirilgan bitimlar nechta?
tags: deals, delay, payment, zero, uz
**Javob:** Natija (ma'lumotlardan to'g'ridan-to'g'ri):
delayed_deals_count: 0; avg_delay_days: —; total_amount_uzs: —
```sql
SELECT COUNT(*) AS delayed_deals_count, AVG(payment_delay_days) AS avg_delay_days, SUM(amount_uzs) AS total_amount_uzs FROM deals WHERE payment_delay_days > 0
LIMIT 50
```
answerable=True ok=True time=11.9s missing=[]

## s27. Средняя задержка поставки по цементу (в днях)?
tags: deals, delay, avg, product, ru
**Javob:** Средняя задержка поставки портландцемента составляет **-7.7 дней** (среди просроченных сделок — **8.02 дней**). Всего исполнено 35 955 сделок, из них с просрочкой — 1 378.

Показатель рассчитывается как отклонение фактического срока поставки от предусмотренного контрактом.
```sql
SELECT AVG(delivery_delay_days) AS avg_delay_days, AVG(CASE WHEN delivery_delay_days > 0 THEN delivery_delay_days END) AS avg_late_delay_days, COUNT(delivery_delay_days) AS total_delivered_deals, SUM(CASE WHEN delivery_delay_days > 0 THEN 1 ELSE 0 END) AS late_deals_count FROM deals WHERE tnved = '252329' AND delivery_delay_days IS NOT NULL
LIMIT 50
```
answerable=True ok=True time=14.7s missing=[]

## s28. 2024-yilda savdo turlari bo'yicha nechta bitim bo'lgan?
tags: deals, trade-type, multi, uz
**Javob:** 2024-yilda savdo turlari bo'yicha bitimlar soni:
Ingliz auksioni — **55 076 ta** bitim (shundan 51 198 tasi amalda, 3 878 tasi bekor qilingan)
Ikki tomonlama auksion — **49 004 ta** bitim (shundan 45 750 tasi amalda, 3 254 tasi bekor qilingan)
Teskari auksion — **2 567 ta** bitim (shundan 2 376 tasi amalda, 191 tasi bekor qilingan)

Ma'lumotlar barcha bitim hisoblarini qamrab oladi.
```sql
SELECT trade_type, COUNT(*) AS total_deals, SUM(CASE WHEN is_cancelled = 0 THEN 1 ELSE 0 END) AS active_deals, SUM(CASE WHEN is_cancelled = 1 THEN 1 ELSE 0 END) AS cancelled_deals FROM deals WHERE year = 2024 GROUP BY trade_type ORDER BY total_deals DESC
LIMIT 50
```
answerable=True ok=True time=11.3s missing=[]

## s29. Какой тип торгов чаще всего используется для цемента?
tags: deals, trade-type, max-group, product, ru
**Javob:** Чаще всего для цемента используется **Двусторонний аукцион** — всего **21 682** сделок (20 191 действующих).
Двусторонний аукцион: **21 682** сделок (20 191 действующих)
Английский аукцион: **11 678** сделок (10 867 действующих)
Обратный аукцион: **5 786** сделок (5 362 действующих)

Учтены все сделки за весь доступный период.
```sql
SELECT trade_type, COUNT(*) AS total_deals, SUM(CASE WHEN is_cancelled = 0 THEN 1 ELSE 0 END) AS active_deals FROM deals WHERE tnved = '252329' GROUP BY trade_type ORDER BY total_deals DESC
LIMIT 50
```
answerable=True ok=True time=18.0s missing=[]

## s30. 2024-yil 16-iyun (yakshanba) kuni dollar kursi qancha edi?
tags: usd, weekend, date, uz
**Javob:** Natija (ma'lumotlardan to'g'ridan-to'g'ri):
date: 2024-06-16; rate: 11 844.56
```sql
SELECT date, rate FROM usd_rates WHERE date = '2024-06-16'
LIMIT 50
```
answerable=True ok=True time=6.2s missing=[]

## s31. Какой был максимальный курс доллара в 2024 году и в какой день?
tags: usd, max, ru
**Javob:** В 2024 году максимальный курс доллара составил **12 410.16 сумов** (зафиксирован 31.12.2024).
```sql
SELECT date AS max_date, rate AS max_rate FROM usd_rates WHERE date >= '2024-01-01' AND date <= '2024-12-31' ORDER BY rate DESC LIMIT 1
```
answerable=True ok=False time=7.2s missing=["string '2024-12-31'"]

## s32. 2024-yilda dollar kursi eng past qachon bo'lgan va qancha?
tags: usd, min, uz
**Javob:** Natija (ma'lumotlardan to'g'ridan-to'g'ri):
date: 2024-03-09; rate: 11 657.83
```sql
SELECT date, rate FROM usd_rates WHERE date >= '2024-01-01' AND date <= '2024-12-31' ORDER BY rate ASC LIMIT 1
```
answerable=True ok=True time=7.6s missing=[]

## s33. Сумма сделки 350088 в долларах и в сумах?
tags: deals, single-deal, export, usd, multi, ru
**Javob:** По сделке № 350088 от 04.10.2024 (Пряжа хлопчатобумажная) сумма составляет **980 121 011.17 сумов** (эквивалент **81 662.46 USD** по курсу 12 002.1 UZS/USD). Статус сделки: «Исполнен».
```sql
SELECT d.deal_no, d.deal_date, d.product_canon_ru AS product, d.amount_uzs, CASE WHEN d.currency = 'Доллар США' THEN d.amount ELSE ROUND(d.amount_uzs / COALESCE(d.usd_rate, u.rate), 2) END AS amount_usd, COALESCE(d.usd_rate, u.rate) AS usd_rate, d.status FROM deals d LEFT JOIN usd_rates u ON u.date = d.deal_date WHERE d.deal_no = 350088
LIMIT 50
```
answerable=True ok=True time=10.9s missing=[]

## s34. 2025-yilda Портландцемент qancha sotilgan?
tags: deals, volume, product, mixed-lang, uz
**Javob:** 2025-yilda jami **1 325 527 tonna** portlandsement sotilgan — **8 215 ta** bitim, umumiy summasi 1 260 960 679 520 so'm.

Bekor qilingan bitimlar hisobga olinmadi (622 ta bekor qilingan bitim).
```sql
SELECT unit, SUM(volume) AS total_volume, SUM(amount_uzs) AS total_amount_uzs, COUNT(*) AS deals_active, (SELECT COUNT(*) FROM deals WHERE tnved = '252329' AND year = 2025 AND is_cancelled = 1) AS deals_cancelled FROM deals WHERE tnved = '252329' AND year = 2025 AND is_cancelled = 0 GROUP BY unit
LIMIT 50
```
answerable=True ok=True time=13.0s missing=[]

## s35. 📊 Сколько сделок по сахару было в 2024 году? 🍬
tags: deals, product, emoji, ru
**Javob:** В 2024 году по сахару зарегистрировано **2 631** сделок (из них действительных — **2 419**, аннулировано — 212).

Учтены сделки по ТН ВЭД 170199 во всех статусах.
```sql
SELECT COUNT(*) AS deals_total, SUM(CASE WHEN is_cancelled = 0 THEN 1 ELSE 0 END) AS deals_active, SUM(CASE WHEN is_cancelled = 1 THEN 1 ELSE 0 END) AS deals_cancelled FROM deals WHERE tnved = '170199' AND year = 2024
LIMIT 50
```
answerable=True ok=True time=11.8s missing=[]

## s36. Assalomu alaykum, hurmatli yordamchi! Men birja ma'lumotlari bilan ishlayapman va menga bir narsa juda kerak bo'lib qoldi. Iltimos, e'tibor bering: meni faqat bitta ko'rsatkich qiziqtiradi, boshqa hech narsa kerak emas, grafik ham, jadval ham, izoh ham shart emas. Savolim shu: 2024-yilda birjada jami qancha oziq-ovqat bug'doyi sotilgan (bekor qilingan bitimlarsiz)? Oldindan katta rahmat!
tags: deals, volume, product, long, uz
**Javob:** Natija (ma'lumotlardan to'g'ridan-to'g'ri):
unit: tonna; total_volume: 2 087 277; deal_count: 7 662; total_amount_uzs: 8 129 749 174 135; cancelled_deals: 528
```sql
SELECT unit, SUM(volume) AS total_volume, COUNT(*) AS deal_count, SUM(amount_uzs) AS total_amount_uzs, (SELECT COUNT(*) FROM deals WHERE tnved = '100199' AND year = 2024 AND is_cancelled = 1) AS cancelled_deals FROM deals WHERE tnved = '100199' AND year = 2024 AND is_cancelled = 0 GROUP BY unit
LIMIT 50
```
answerable=True ok=True time=11.6s missing=[]

## s37. Какая сумма сделок 100001 и 100002?
tags: deals, single-deal, two-ids, multi, ru
**Javob:** Данные по запрошенным сделкам:
Сделка № 100001 от 03.01.2022: Шрот хлопковый — **304 547 938.4 сум** (304 547 938.4 сумов), статус: «Исполнен»
Сделка № 100002 от 03.01.2022: Трубы полиэтиленовые — **23 145 714 сум** (23 145 714 сумов), статус: «Исполнен»
```sql
SELECT deal_no, deal_date, product_canon_ru AS product, amount, currency, amount_uzs, status FROM deals WHERE deal_no IN (100001, 100002)
LIMIT 50
```
answerable=True ok=True time=14.4s missing=[]

## s38. 170199 bo'yicha 2024 hajmi
tags: deals, volume, product, tnved-only, colloq, uz
**Javob:** 2024-yilda shakar (TN VED 170199) bo'yicha jami **93.38 tonna** (93 378 tonna) hajmdagi bitimlar amalga oshirilgan — **2 419 ta** amaldagi bitim, umumiy summasi 1 150 565 701 300 so'm.

Bekor qilingan bitimlar hisobga olinmadi (212 ta bekor qilingan bitim).
```sql
SELECT unit, SUM(volume) AS total_volume, COUNT(*) AS deals_active, SUM(amount_uzs) AS total_amount_uzs, (SELECT COUNT(*) FROM deals WHERE tnved = '170199' AND year = 2024 AND is_cancelled = 1) AS deals_cancelled FROM deals WHERE tnved = '170199' AND year = 2024 AND is_cancelled = 0 GROUP BY unit
LIMIT 50
```
answerable=True ok=True time=10.8s missing=[]

## s39. Qaysi ko'proq: Farg'ona yoki Namangan 2025 paxta hajmi?
tags: deals, volume, region, region-seller, compare, multi, uz
**Javob:** Natija (ma'lumotlardan to'g'ridan-to'g'ri):
region: Namangan viloyati; unit: kg; total_volume: 239 952 425; deal_count: 4 039; total_amount_uzs: 2 182 001 254 207.84
region: Farg‘ona viloyati; unit: kg; total_volume: 75 893 843; deal_count: 1 262; total_amount_uzs: 655 711 426 892.82
```sql
SELECT region, unit, SUM(volume) AS total_volume, COUNT(*) AS deal_count, SUM(amount_uzs) AS total_amount_uzs FROM deals WHERE tnved = '520100' AND year = 2025 AND region IN ('Farg‘ona viloyati', 'Namangan viloyati') AND is_cancelled = 0 GROUP BY region, unit ORDER BY total_volume DESC
LIMIT 50
```
answerable=True ok=True time=10.1s missing=[]

## s40. 2024 vs 2023 цена цемента?
tags: deals, price, yoy, compare, multi, colloq, ru
**Javob:** Динамика цен на портландцемент (2023 vs 2024):
2023 год: средневзвешенная цена — **787 119.86 сум** за т (простая средняя: 788 793.92 сум), всего **6 613** сделок объёмом 1 075 599 т.
2024 год: средневзвешенная цена — **870 157.39 сум** за т (простая средняя: 868 484.2 сум), всего **7 643** сделок объёмом 1 254 917 т.

Аннулированные сделки исключены из расчёта.
```sql
SELECT year, currency, unit, COUNT(*) AS deals_count, SUM(volume) AS total_volume, SUM(amount) AS total_amount, AVG(unit_price) AS avg_unit_price, SUM(amount) / SUM(volume) AS weighted_avg_price FROM deals WHERE tnved = '252329' AND year IN (2023, 2024) AND is_cancelled = 0 GROUP BY year, currency, unit ORDER BY year ASC
LIMIT 50
```
answerable=True ok=True time=8.3s missing=[]

## s41. 2024-yil oylar bo'yicha bitimlar sonining grafigini chizib ber
tags: trap, chart, uz
**Javob:** Ma'lumotlarda bu savolga javob yo'q. Tizim grafik va diagrammalar chizish imkoniyatiga ega emas, faqat matnli va jadval ko'rinishidagi ma'lumotlarni taqdim eta oladi.
```sql
-
```
answerable=False ok=True time=3.1s missing=[]

## s42. Отправь отчёт по сделкам за 2024 год мне на почту
tags: trap, email, ru
**Javob:** В данных нет ответа на этот вопрос. В системе отсутствует возможность отправки отчётов или писем на электронную почту (доступны только аналитические запросы к базе данных торговых сделок).
```sql
-
```
answerable=False ok=True time=3.2s missing=[]

## s43. How many deals in 2024?
tags: deals, en
**Javob:** В 2024 году зарегистрировано **106 647** сделок: **99 324** действующих и **7 323** аннулированных.
```sql
SELECT COUNT(*) AS deals_total, SUM(CASE WHEN is_cancelled = 0 THEN 1 ELSE 0 END) AS deals_active, SUM(CASE WHEN is_cancelled = 1 THEN 1 ELSE 0 END) AS deals_cancelled FROM deals WHERE year = 2024
LIMIT 50
```
answerable=True ok=True time=9.2s missing=[]

## s44. Bugun Toshkentda ob-havo qanday?
tags: trap, weather, uz
**Javob:** Ma'lumotlarda bu savolga javob yo'q. Ma'lumotlar bazasida ob-havo haqida ma'lumotlar mavjud emas (faqat UZEX tovar birjasi bitimlari va shartnomalari saqlanadi).
```sql
-
```
answerable=False ok=True time=2.0s missing=[]

## s45. Что такое UZEX?
tags: trap, meta, ru
**Javob:** В данных нет ответа на этот вопрос. Запрос содержит общий вопрос о бирже (что такое UZEX), а база данных содержит только информацию о сделках, контрактах, участниках и брокерах товарной биржи.
```sql
-
```
answerable=False ok=True time=2.4s missing=[]

## s46. Какой будет курс доллара в 2027 году?
tags: trap, forecast, usd, ru
**Javob:** В данных нет ответа на этот вопрос. Данные в базе охватывают период только до 30 октября 2026 года. Прогнозов и данных на 2027 год нет.
```sql
-
```
answerable=False ok=True time=2.7s missing=[]

## s47. Қайси йилда энг кўп битим тузилган?
tags: deals, max-group, cyr, uz
**Javob:** Natija (ma'lumotlardan to'g'ridan-to'g'ri):
year: 2025; deals_total: 115 763; deals_active: 107 678; total_amount_uzs: 52 060 836 360 057.12
```sql
SELECT year, COUNT(*) AS deals_total, SUM(CASE WHEN is_cancelled = 0 THEN 1 ELSE 0 END) AS deals_active, SUM(CASE WHEN is_cancelled = 0 THEN amount_uzs ELSE 0 END) AS total_amount_uzs FROM deals GROUP BY year ORDER BY deals_total DESC LIMIT 1
```
answerable=True ok=True time=18.7s missing=[]

## s48. Сколько разных продавцов продавали хлопок в 2025 году?
tags: deals, distinct, company, product, ru
**Javob:** В 2025 году хлопок-сырец продавали **67** различных продавцов (всего сделок: 30 894).

Аннулированные сделки не учитывались (всего аннулировано сделок: 2 162).
```sql
SELECT COUNT(DISTINCT CASE WHEN is_cancelled = 0 THEN seller_inn END) AS active_sellers_count, COUNT(DISTINCT seller_inn) AS total_sellers_count, SUM(CASE WHEN is_cancelled = 0 THEN 1 ELSE 0 END) AS active_deals, SUM(CASE WHEN is_cancelled = 1 THEN 1 ELSE 0 END) AS cancelled_deals FROM deals WHERE tnved = '520100' AND year = 2025
LIMIT 50
```
answerable=True ok=True time=10.9s missing=[]

## s49. 2025-yilda qaysi oyda eksport bitimlari summasi dollarda eng katta bo'lgan?
tags: deals, export, usd, max-group, monthly, uz
**Javob:** Natija (ma'lumotlardan to'g'ridan-to'g'ri):
month: 7; total_amount_usd: 23 805 580.3; deals_count: 145
```sql
SELECT month, SUM(amount) AS total_amount_usd, COUNT(*) AS deals_count FROM deals WHERE year = 2025 AND contract_type = 'Экспортный' AND is_cancelled = 0 GROUP BY month ORDER BY total_amount_usd DESC LIMIT 1
```
answerable=True ok=True time=7.1s missing=[]

## s50. Toshkent shahrida nechta xaridor ro'yxatdan o'tgan?
tags: participants, distinct, region, uz
**Javob:** Toshkent shahrida jami **2 538 ta** xaridor ro'yxatdan o'tgan.
```sql
SELECT COUNT(*) AS buyer_count FROM participants WHERE region = 'Toshkent shahri' AND role = 'Покупатель'
LIMIT 50
```
answerable=True ok=True time=6.9s missing=[]
