# Golden check 2026-11-05 03:36 model=gemini:gemini-3.5-flash

**40/40 passed**

| id | result | time | missing |
|---|---|---|---|
| g01 | ok | 7.7s |  |
| g02 | ok | 8.4s |  |
| g03 | ok | 6.9s |  |
| g04 | ok | 5.4s |  |
| g05 | ok | 10.7s |  |
| g06 | ok | 3.5s |  |
| g07 | ok | 7.3s |  |
| g08 | ok | 19.0s |  |
| g09 | ok | 7.9s |  |
| g10 | ok | 3.6s |  |
| g11 | ok | 8.6s |  |
| g12 | ok | 8.7s |  |
| g13 | ok | 7.8s |  |
| g14 | ok | 6.8s |  |
| g15 | ok | 2.8s |  |
| g16 | ok | 5.2s |  |
| g17 | ok | 5.2s |  |
| g18 | ok | 6.6s |  |
| g19 | ok | 3.9s |  |
| g20 | ok | 5.8s |  |
| g21 | ok | 4.6s |  |
| g22 | ok | 6.2s |  |
| g23 | ok | 3.8s |  |
| g24 | ok | 20.7s |  |
| g25 | ok | 5.8s |  |
| g26 | ok | 8.2s |  |
| g27 | ok | 8.6s |  |
| g28 | ok | 5.5s |  |
| g29 | ok | 3.2s |  |
| g30 | ok | 7.3s |  |
| g31 | ok | 7.6s |  |
| g32 | ok | 6.0s |  |
| g33 | ok | 8.3s |  |
| g34 | ok | 9.6s |  |
| g35 | ok | 3.2s |  |
| g36 | ok | 5.5s |  |
| g37 | ok | 2.8s |  |
| g38 | ok | 4.9s |  |
| g39 | ok | 5.5s |  |
| g40 | ok | 3.4s |  |

## g01. Кто покупатель и продавец по сделке 100001?
tags: deals, single-deal, ru
**Javob:** По сделке № 100001 от 03.01.2022 продавец — **RUKUSHO‘ FERMER MCHJ** (ИНН 921912462), покупатель — **"Bo‘juk Servis" MChJ** (ИНН 978906167). Товар: Шрот хлопковый, объём 79 720 кг, сумма 304 547 938.4 сум, статус «Исполнен».
```sql
SELECT d.deal_no, d.deal_date, d.product_canon_ru AS product, d.volume, d.unit, d.amount, d.currency, d.status, d.seller_inn, ps.name AS seller_name, d.buyer_inn, pb.name AS buyer_name FROM deals d LEFT JOIN participants ps ON ps.inn = d.seller_inn LEFT JOIN participants pb ON pb.inn = d.buyer_inn WHERE d.deal_no = 100001
LIMIT 50
```
answerable=True ok=True time=7.7s missing=[]

## g02. Сколько тонн хлопка-сырца продано в 2024 году?
tags: deals, volume, product, ru
**Javob:** В 2024 году было продано **1 672 494 955 кг** хлопка-сырца по **28 079** сделкам на общую сумму 12 915 322 307 346.02 сумов.

Аннулированные (неоплаченные) сделки не учитывались.
```sql
SELECT unit, SUM(volume) AS total_volume, COUNT(*) AS deal_count, SUM(amount_uzs) AS total_amount_uzs FROM deals WHERE tnved = '520100' AND year = 2024 AND is_cancelled = 0 GROUP BY unit
LIMIT 50
```
answerable=True ok=True time=8.4s missing=[]

## g03. Какая средняя цена портландцемента за тонну в марте 2023 года?
tags: deals, price, product, ru
**Javob:** В марте 2023 года средняя цена портландцемента составила **797 626.31 сум** за т (взвешенная средняя — **795 653.4 сум**). Всего оформлено **517** сделок общим объёмом 86 020 т.

Аннулированные сделки не учитывались.
```sql
SELECT currency, unit, AVG(unit_price) AS avg_price, SUM(amount) / SUM(volume) AS weighted_avg_price, COUNT(*) AS deal_count, SUM(volume) AS total_volume FROM deals WHERE tnved = '252329' AND year = 2023 AND month = 3 AND is_cancelled = 0 GROUP BY currency, unit
LIMIT 50
```
answerable=True ok=True time=6.9s missing=[]

## g04. Топ-5 брокеров по количеству сделок в 2025 году
tags: brokers, top-n, ru
**Javob:** Топ-5 брокеров по количеству сделок в 2025 году:
BK111 — "Gucham Broker" MChJ: **6 692** сделок
BK005 — NAXON BROKER AJ: **5 690** сделок
BK106 — PASUR BROKER MCHJ: **5 602** сделок
BK017 — FIPI BROKER MCHJ: **4 641** сделок
BK102 — "Shofin Broker" MChJ: **4 594** сделок

Учтены сделки во всех статусах. Если брокер обслуживал обе стороны сделки, она посчитана один раз.
```sql
WITH bd AS (SELECT seller_broker AS code, deal_no FROM deals WHERE year = 2025 AND seller_broker IS NOT NULL UNION SELECT buyer_broker AS code, deal_no FROM deals WHERE year = 2025 AND buyer_broker IS NOT NULL) SELECT b.code, b.name, COUNT(*) AS deal_count FROM bd JOIN brokers b ON b.code = bd.code GROUP BY b.code, b.name ORDER BY deal_count DESC LIMIT 5
```
answerable=True ok=True time=5.4s missing=[]

## g05. Сколько сделок аннулировано в 2026 году?
tags: deals, status, ru
**Javob:** Результат (напрямую из данных):
cancelled_count: 6 266; cancelled_amount_uzs: 3 248 050 920 296.03
```sql
SELECT COUNT(*) AS cancelled_count, SUM(amount_uzs) AS cancelled_amount_uzs FROM deals WHERE year = 2026 AND is_cancelled = 1
LIMIT 50
```
answerable=True ok=True time=10.7s missing=[]

## g06. Какой курс доллара был 15.06.2024?
tags: usd, ru
**Javob:** Курс доллара США на 15.06.2024 составлял **11 862.46** сумов за 1 USD.
```sql
SELECT date, rate FROM usd_rates WHERE date = '2024-06-15'
LIMIT 50
```
answerable=True ok=True time=3.5s missing=[]

## g07. Сумма экспортных сделок в 2023 году в сумах
tags: deals, export, usd, ru
**Javob:** В 2023 году сумма экспортных сделок составила **2 199 458 684 636.28 сумов** (всего **1 118** сделок).

Аннулированные сделки не учитывались. Суммы в валюте пересчитаны в сумы по курсу ЦБ на дату сделки.
```sql
SELECT COUNT(*) AS deal_count, SUM(amount_uzs) AS total_amount_uzs FROM deals WHERE contract_type = 'Экспортный' AND year = 2023 AND is_cancelled = 0
LIMIT 50
```
answerable=True ok=True time=7.3s missing=[]

## g08. Сколько сделок у компании Qojo Invest?
tags: deals, company, trap, ru
**Javob:** Количество сделок для «Qojo Invest» (найдено совпадений: 2):
"Qojo‘ Invest" OK (ИНН 912004930) — **69** сделок: 0 как продавец, 69 как покупатель
"Qojo Invest" MChJ (ИНН 915861525) — **72** сделок: 0 как продавец, 72 как покупатель

Учтены сделки во всех статусах за весь период.
```sql
SELECT p.inn, p.name, COUNT(d.deal_no) AS total_deals, SUM(CASE WHEN d.seller_inn = p.inn THEN 1 ELSE 0 END) AS as_seller, SUM(CASE WHEN d.buyer_inn = p.inn THEN 1 ELSE 0 END) AS as_buyer FROM participants p LEFT JOIN deals d ON d.seller_inn = p.inn OR d.buyer_inn = p.inn WHERE p.inn IN ('912004930', '915861525') GROUP BY p.inn, p.name
LIMIT 50
```
answerable=True ok=True time=19.0s missing=[]

## g09. В каком регионе больше всего сделок по муке?
tags: deals, region, product, ru
**Javob:** Больше всего сделок по пшеничной муке заключено в регионе **Farg‘ona viloyati** — **7 943** сделок на общий объём 128 957 100 кг.
Farg‘ona viloyati — **7 943** сделок (128 957 100 кг, 626 641 249 524 сум)
Toshkent shahri — **5 577** сделок (91 228 300 кг, 438 273 952 868 сум)
Namangan viloyati — **4 503** сделок (72 340 600 кг, 369 955 805 860 сум)
Andijon viloyati — **2 937** сделок (47 597 800 кг, 235 177 777 604 сум)
Jizzax viloyati — **2 144** сделок (34 083 200 кг, 173 032 281 671 сум)

Учтены сделки во всех статусах. Регион определяется по месту расположения склада продавца.
```sql
SELECT region, COUNT(*) AS deal_count, SUM(CASE WHEN is_cancelled = 0 THEN volume ELSE 0 END) AS total_volume, unit, SUM(CASE WHEN is_cancelled = 0 THEN amount_uzs ELSE 0 END) AS total_amount_uzs FROM deals WHERE tnved = '110100' GROUP BY region, unit ORDER BY deal_count DESC LIMIT 5
```
answerable=True ok=True time=7.9s missing=[]

## g10. STIR 953758401 qaysi kompaniya va qaysi viloyatda?
tags: participants, company, uz
**Javob:** Natija (ma'lumotlardan to'g'ridan-to'g'ri):
inn: 953758401; name: "Go‘qe Prokat" MChJ; region: Farg‘ona viloyati; activity: Производитель; role: Sotuvchi
```sql
SELECT inn, name, region, activity, role FROM participants WHERE inn = '953758401'
LIMIT 50
```
answerable=True ok=True time=3.6s missing=[]

## g11. Namangan viloyatida 2025-yilda eng ko'p sotilgan tovar qaysi?
tags: deals, region, top-n, uz
**Javob:** Natija (ma'lumotlardan to'g'ridan-to'g'ri):
tnved: 520100; product_name: Paxta xomashyosi; total_amount_uzs: 2 182 001 254 207.84; deal_count: 4 039
tnved: 170199; product_name: Shakar; total_amount_uzs: 1 083 583 849 336; deal_count: 1 980
tnved: 100199; product_name: Oziq-ovqat bug'doyi; total_amount_uzs: 1 030 628 859 043; deal_count: 860
tnved: 271019; product_name: Dizel yoqilg'isi / Mazut; total_amount_uzs: 584 336 482 836; deal_count: 1 449
tnved: 271012; product_name: Avtomobil benzini; total_amount_uzs: 464 184 178 000; deal_count: 1 079
```sql
SELECT d.tnved, d.product_canon_uz AS product_name, SUM(d.amount_uzs) AS total_amount_uzs, COUNT(*) AS deal_count FROM deals d WHERE d.region = 'Namangan viloyati' AND d.year = 2025 AND d.is_cancelled = 0 GROUP BY d.tnved, d.product_canon_uz ORDER BY total_amount_uzs DESC LIMIT 5
```
answerable=True ok=True time=8.6s missing=[]

## g12. BK045 brokeri jami nechta bitimda qatnashgan?
tags: brokers, uz
**Javob:** Natija (ma'lumotlardan to'g'ridan-to'g'ri):
code: BK045; name: "ДУСУНУ БРОКЕР" МЧЖ; deal_count: 6 712; as_seller_broker: 2 781; as_buyer_broker: 3 946
```sql
SELECT b.code, b.name, COUNT(DISTINCT d.deal_no) AS deal_count, COUNT(DISTINCT CASE WHEN d.seller_broker = b.code THEN d.deal_no END) AS as_seller_broker, COUNT(DISTINCT CASE WHEN d.buyer_broker = b.code THEN d.deal_no END) AS as_buyer_broker FROM brokers b LEFT JOIN deals d ON d.seller_broker = b.code OR d.buyer_broker = b.code WHERE b.code = 'BK045' GROUP BY b.code, b.name
LIMIT 50
```
answerable=True ok=True time=8.7s missing=[]

## g13. Eng yirik bitim qaysi?
tags: deals, top-n, uz
**Javob:** Natija (ma'lumotlardan to'g'ridan-to'g'ri):
deal_no: 247890; deal_date: 2023-10-09; product: Oziq-ovqat bug'doyi; volume: 8 703; unit: tonna; amount: 30 190 376 286; currency: so'm; amount_uzs: 30 190 376 286; status: Bajarilgan; seller_inn: 902946936; seller_name: CHO‘HE KLASTER MCHJ; buyer_inn: 916644459; buyer_name: "МИКИ БИЗНЕС" ҚК
```sql
SELECT d.deal_no, d.deal_date, d.product_canon_uz AS product, d.volume, d.unit, d.amount, d.currency, d.amount_uzs, d.status, d.seller_inn, ps.name AS seller_name, d.buyer_inn, pb.name AS buyer_name FROM deals d LEFT JOIN participants ps ON ps.inn = d.seller_inn LEFT JOIN participants pb ON pb.inn = d.buyer_inn WHERE d.is_cancelled = 0 ORDER BY d.amount_uzs DESC LIMIT 1
```
answerable=True ok=True time=7.8s missing=[]

## g14. Yetkazib berish muddati kechikkan bitimlar soni qancha?
tags: deals, delay, uz
**Javob:** Yetkazib berish muddati kechikkan bitimlar soni **17 805 ta**ni tashkil etadi (umumiy summasi 7 704 993 702 929.16 so'm).

Faqat yetkazib berish kechikishi qayd etilgan (delivery_delay_days > 0) va bekor qilinmagan bitimlar hisoblandi.
```sql
SELECT COUNT(*) AS delayed_deals_count, SUM(amount_uzs) AS total_amount_uzs FROM deals WHERE delivery_delay_days > 0 AND is_cancelled = 0
LIMIT 50
```
answerable=True ok=True time=6.8s missing=[]

## g15. Сколько контрактов с базисом поставки EXW?
tags: contracts, ru
**Javob:** Всего найдено **5 194** контрактов с базисом поставки EXW.
```sql
SELECT COUNT(*) AS contract_count FROM contracts WHERE delivery_basis = 'EXW'
LIMIT 50
```
answerable=True ok=True time=2.8s missing=[]

## g16. Birorta ham bitim tuzilmagan shartnomalar nechta?
tags: contracts, uz
**Javob:** Birorta ham bitim tuzilmagan shartnomalar soni **133 ta**ni tashkil etadi.
```sql
SELECT COUNT(c.contract_no) AS unused_contracts_count FROM contracts c LEFT JOIN deals d ON c.contract_no = d.contract_no WHERE d.contract_no IS NULL
LIMIT 50
```
answerable=True ok=True time=5.2s missing=[]

## g17. Сколько контрактов со складом в Наманганской области?
tags: contracts, region, ru
**Javob:** Со складом в Наманганской области зарегистрировано **667** контрактов.
```sql
SELECT COUNT(*) AS contract_count FROM contracts WHERE region = 'Namangan viloyati'
LIMIT 50
```
answerable=True ok=True time=5.2s missing=[]

## g18. Fyuchers shaklidagi shartnomalar nechta?
tags: contracts, uz
**Javob:** Natija (ma'lumotlardan to'g'ridan-to'g'ri):
total_contracts: 79
```sql
SELECT COUNT(*) AS total_contracts FROM contracts WHERE contract_form = 'Фьючерс'
LIMIT 50
```
answerable=True ok=True time=6.6s missing=[]

## g19. Сколько экспортных контрактов зарегистрировано?
tags: contracts, export, ru
**Javob:** Всего зарегистрировано **148** экспортных контрактов.
```sql
SELECT COUNT(*) AS registered_contracts_count FROM contracts WHERE contract_type = 'Экспортный'
LIMIT 50
```
answerable=True ok=True time=3.9s missing=[]

## g20. 100118-shartnoma bo'yicha to'lov muddati va yetkazib berish muddati necha kun?
tags: contracts, single-contract, uz
**Javob:** **100118**-sonli shartnoma (Пшеница продовольственная) bo'yicha to'lov muddati — **66 kun**, yetkazib berish muddati — **33 kun** (sotuvchi: "Mifo‘ Tekstil" MChJ, STIR 957505604).
```sql
SELECT c.contract_no, c.product_name, c.payment_days, c.delivery_days, c.seller_inn, p.name AS seller_name FROM contracts c LEFT JOIN participants p ON p.inn = c.seller_inn WHERE c.contract_no = '100118'
LIMIT 50
```
answerable=True ok=True time=5.8s missing=[]

## g21. Какая базовая цена в контракте 100002 и что это за товар?
tags: contracts, single-contract, price, ru
**Javob:** По контракту № 100002 товар — **Аммиачная селитра** (Аммиачная селитра), базовая цена составляет **2 720 643 сум** за т.
```sql
SELECT contract_no, product_name, product_canon_ru, base_price, unit, currency FROM contracts WHERE contract_no = '100002'
LIMIT 50
```
answerable=True ok=True time=4.6s missing=[]

## g22. Eng ko'p shartnoma ro'yxatdan o'tkazgan sotuvchi qaysi?
tags: contracts, company, top-n, uz
**Javob:** Eng ko'p shartnoma ro'yxatdan o'tkazgan sotuvchi — **VISAQE SERVIS MAS’ULIYATI CHEKLANGAN JAMIYATI** (STIR: 996237847), jami **60 ta** shartnoma.

Ma'lumotlar shartnomalar reestri asosida hisoblandi.
```sql
SELECT p.inn, p.name, COUNT(c.contract_no) AS contract_count FROM contracts c JOIN participants p ON c.seller_inn = p.inn GROUP BY p.inn, p.name ORDER BY contract_count DESC LIMIT 1
```
answerable=True ok=True time=6.2s missing=[]

## g23. DAP yetkazib berish bazisidagi shartnomalar soni qancha?
tags: contracts, uz
**Javob:** DAP yetkazib berish bazisidagi shartnomalar soni **374 ta**.
```sql
SELECT COUNT(*) AS contract_count FROM contracts WHERE delivery_basis = 'DAP'
LIMIT 50
```
answerable=True ok=True time=3.8s missing=[]

## g24. Сколько сделок по хлопку-сырцу 1 сорта 1 класса?
tags: deals, grade, product, ru
**Javob:** Всего зарегистрировано **29 136** сделок (27 341 активных, 1 795 аннулировано) на общий объём 1 618 574 496 кг и сумму 14 447 122 239 054.87 сум.

Включает все сделки за весь доступный период.
```sql
SELECT COUNT(*) AS total_deals, SUM(CASE WHEN is_cancelled = 0 THEN 1 ELSE 0 END) AS active_deals, SUM(CASE WHEN is_cancelled = 1 THEN 1 ELSE 0 END) AS cancelled_deals, SUM(CASE WHEN is_cancelled = 0 THEN volume ELSE 0 END) AS total_volume, unit, SUM(CASE WHEN is_cancelled = 0 THEN amount_uzs ELSE 0 END) AS total_amount_uzs FROM deals WHERE tnved = '520100' AND sort_no = 1 AND class_no = 1 GROUP BY unit
LIMIT 50
```
answerable=True ok=True time=20.7s missing=[]

## g25. 2023-yilda 2-nav paxta xomashyosi qancha sotilgan?
tags: deals, grade, volume, uz
**Javob:** 2023-yilda **404 202.13 tonna** (404 202 126 kg) 2-nav paxta xomashyosi sotilgan — **6 749 ta** bitim, umumiy summasi 2 679 870 122 352.91 so'm.

Bekor qilingan bitimlar hisobga olinmadi.
```sql
SELECT unit, SUM(volume) AS total_volume, SUM(amount_uzs) AS total_amount, COUNT(*) AS deal_count FROM deals WHERE tnved = '520100' AND year = 2023 AND sort_no = 2 AND is_cancelled = 0 GROUP BY unit
LIMIT 50
```
answerable=True ok=True time=5.8s missing=[]

## g26. 2025-yilda oliy nav bug'doy uni qancha sotilgan?
tags: deals, grade, volume, uz
**Javob:** Natija (ma'lumotlardan to'g'ridan-to'g'ri):
unit: kg; total_volume: 20 708 500; deal_count: 1 189; total_amount_uzs: 129 266 244 784
```sql
SELECT unit, SUM(volume) AS total_volume, COUNT(*) AS deal_count, SUM(amount_uzs) AS total_amount_uzs FROM deals WHERE tnved = '110100' AND year = 2025 AND is_cancelled = 0 AND (sort_no = 0 OR class_no = 0) GROUP BY unit
LIMIT 50
```
answerable=True ok=True time=8.2s missing=[]

## g27. 4-klass bug'doy bo'yicha jami nechta bitim bor?
tags: deals, grade, product, uz
**Javob:** Natija (ma'lumotlardan to'g'ridan-to'g'ri):
deal_count: 21 471; valid_deals: 20 133; cancelled_deals: 1 338; total_volume: 5 529 704; unit: tonna; total_amount_uzs: 21 378 556 940 517
```sql
SELECT COUNT(*) AS deal_count, SUM(CASE WHEN is_cancelled = 0 THEN 1 ELSE 0 END) AS valid_deals, SUM(CASE WHEN is_cancelled = 1 THEN 1 ELSE 0 END) AS cancelled_deals, SUM(CASE WHEN is_cancelled = 0 THEN volume ELSE 0 END) AS total_volume, unit, SUM(CASE WHEN is_cancelled = 0 THEN amount_uzs ELSE 0 END) AS total_amount_uzs FROM deals WHERE tnved = '100199' AND class_no = 4 GROUP BY unit
LIMIT 50
```
answerable=True ok=True time=8.6s missing=[]

## g28. 2024-yilda eksport bitimlari summasi dollarda va so'mda qancha?
tags: deals, export, usd, uz
**Javob:** Natija (ma'lumotlardan to'g'ridan-to'g'ri):
deal_count: 1 229; total_usd: 202 495 621; total_uzs: 2 420 672 267 384.07
```sql
SELECT COUNT(*) AS deal_count, SUM(amount) AS total_usd, SUM(amount_uzs) AS total_uzs FROM deals WHERE year = 2024 AND contract_type = 'Экспортный' AND is_cancelled = 0
LIMIT 50
```
answerable=True ok=True time=5.5s missing=[]

## g29. Какой курс доллара был 01.03.2025?
tags: usd, ru
**Javob:** Курс доллара США на 01.03.2025 составлял **12 515.24 сум** за 1 USD.
```sql
SELECT date, rate FROM usd_rates WHERE date = '2025-03-01'
LIMIT 50
```
answerable=True ok=True time=3.2s missing=[]

## g30. 2022-yilda nechta eksport bitimi tuzilgan?
tags: deals, export, uz
**Javob:** 2022-yilda jami **1 317 ta** eksport bitimi tuzilgan. Ulardan **1 237 ta** bitim amalda bo'lib, **80 ta** bitim bekor qilingan.

Eksport bitimlarining umumiy qiymati 236 554 900.6 AQSh dollarini tashkil etdi.
```sql
SELECT COUNT(*) AS total_deals, SUM(CASE WHEN is_cancelled = 0 THEN 1 ELSE 0 END) AS valid_deals, SUM(CASE WHEN is_cancelled = 1 THEN 1 ELSE 0 END) AS cancelled_deals, SUM(amount) AS total_amount_usd FROM deals WHERE year = 2022 AND contract_type = 'Экспортный'
LIMIT 50
```
answerable=True ok=True time=7.3s missing=[]

## g31. Eng katta eksport bitimi qaysi va summasi dollarda qancha?
tags: deals, export, usd, top-n, uz
**Javob:** Natija (ma'lumotlardan to'g'ridan-to'g'ri):
deal_no: 547500; deal_date: 2026-06-24; product: Mis katodi; volume: 147; unit: tonna; amount: 1 683 554.25; currency: AQSh dollari; status: Bajarilgan; seller_inn: 992421731; seller_name: TIZAHI METALL MCHJ; buyer_inn: 919788432; buyer_name: "Bejul Savdo" OK
```sql
SELECT d.deal_no, d.deal_date, d.product_canon_uz AS product, d.volume, d.unit, d.amount, d.currency, d.status, d.seller_inn, ps.name AS seller_name, d.buyer_inn, pb.name AS buyer_name FROM deals d LEFT JOIN participants ps ON ps.inn = d.seller_inn LEFT JOIN participants pb ON pb.inn = d.buyer_inn WHERE d.contract_type = 'Экспортный' AND d.is_cancelled = 0 ORDER BY d.amount DESC LIMIT 1
```
answerable=True ok=True time=7.6s missing=[]

## g32. Сколько сделок у брокера BK001 в 2024 году?
tags: brokers, ru
**Javob:** У брокера **"КЕКУХО БРОКЕР" МЧЖ** (BK001) в 2024 году зафиксировано **1 124** сделок (371 со стороны продавца, 753 со стороны покупателя).

Учтены сделки во всех статусах. Сделки, где брокер выступал с обеих сторон, посчитаны один раз.
```sql
SELECT b.code, b.name, COUNT(DISTINCT d.deal_no) AS total_deals, COUNT(DISTINCT CASE WHEN d.seller_broker = 'BK001' THEN d.deal_no END) AS as_seller_broker, COUNT(DISTINCT CASE WHEN d.buyer_broker = 'BK001' THEN d.deal_no END) AS as_buyer_broker FROM brokers b LEFT JOIN deals d ON (d.seller_broker = b.code OR d.buyer_broker = b.code) AND d.year = 2024 WHERE b.code = 'BK001' GROUP BY b.code, b.name
LIMIT 50
```
answerable=True ok=True time=6.0s missing=[]

## g33. Qaysi broker jami eng ko'p bitimda qatnashgan?
tags: brokers, top-n, uz
**Javob:** Barcha davr mobaynida eng ko'p bitimda qatnashgan broker — **"Gucham Broker" MChJ** (BK111), u jami **32 422 ta** bitimda qatnashgan.
BK111 — "Gucham Broker" MChJ: **32 422 ta** bitim
BK085 — KAZEHI BROKER MCHJ: **20 808 ta** bitim
BK017 — FIPI BROKER MCHJ: **20 141 ta** bitim
BK106 — PASUR BROKER MCHJ: **19 099 ta** bitim
BK102 — "Shofin Broker" MChJ: **18 567 ta** bitim

Broker sotuvchi yoki xaridor tomonida qatnashgan bitimlar hisoblandi, har bir bitim bir marta hisobga olingan.
```sql
WITH bd AS (SELECT seller_broker AS code, deal_no FROM deals WHERE seller_broker IS NOT NULL UNION SELECT buyer_broker AS code, deal_no FROM deals WHERE buyer_broker IS NOT NULL) SELECT b.code, b.name, COUNT(*) AS deal_count FROM bd JOIN brokers b ON b.code = bd.code GROUP BY b.code, b.name ORDER BY deal_count DESC LIMIT 5
```
answerable=True ok=True time=8.3s missing=[]

## g34. Какой брокер был брокером продавца в наибольшем числе сделок?
tags: brokers, top-n, ru
**Javob:** Наибольшее число сделок в качестве брокера продавца оформил брокер **"Gucham Broker" MChJ** (BK111) — **21 471** сделок.

Учтены сделки во всех статусах за весь доступный период.
```sql
SELECT b.code AS broker_code, b.name AS broker_name, COUNT(d.deal_no) AS deal_count FROM deals d JOIN brokers b ON b.code = d.seller_broker GROUP BY b.code, b.name ORDER BY deal_count DESC LIMIT 1
```
answerable=True ok=True time=9.6s missing=[]

## g35. Какой объём торгов пшеницей был в 2021 году?
tags: trap, period, ru
**Javob:** В данных нет ответа на этот вопрос. В базе данных отсутствуют сведения за 2021 год (данные доступны только за период с 3 января 2022 года по 30 октября 2026 года).
```sql
-
```
answerable=False ok=True time=3.2s missing=[]

## g36. Noyabr 2026 da qancha un sotilgan?
tags: trap, period, uz
**Javob:** Ma'lumotlarda bu savolga javob yo'q. Ma'lumotlar bazasidagi bitimlar 2022-yil 3-yanvardan 2026-yil 30-oktabrgacha bo'lgan davrni qamrab oladi. 2026-yil noyabr oyi bo'yicha ma'lumotlar mavjud emas.
```sql
-
```
answerable=False ok=True time=5.5s missing=[]

## g37. Кто директор компании с ИНН 953758401 и какой у неё телефон?
tags: trap, participants, ru
**Javob:** В данных нет ответа на этот вопрос. В базе данных нет сведений о директорах, руководителях и контактных телефонах компаний (содержатся только ИНН, наименование, регион, вид деятельности и роль в торгах).
```sql
-
```
answerable=False ok=True time=2.8s missing=[]

## g38. 100437-bitim bo'yicha xaridor kim?
tags: trap, single-deal, uz
**Javob:** 100437-sonli bitim ma'lumotlar bazasidan topilmadi.
```sql
SELECT d.deal_no, d.deal_date, d.product_canon_uz AS product, d.volume, d.unit, d.amount, d.currency, d.status, d.seller_inn, ps.name AS seller_name, d.buyer_inn, pb.name AS buyer_name FROM deals d LEFT JOIN participants ps ON ps.inn = d.seller_inn LEFT JOIN participants pb ON pb.inn = d.buyer_inn WHERE d.deal_no = 100437
LIMIT 50
```
answerable=True ok=True time=4.9s missing=[]

## g39. Сколько золота продано на бирже в 2024 году?
tags: trap, product, ru
**Javob:** В данных нет ответа на этот вопрос. Товар «золото» отсутствует в списке биржевых товаров и не торгуется на бирже.
```sql
-
```
answerable=False ok=True time=5.5s missing=[]

## g40. 2027-yilda paxta narxi qancha bo'ladi?
tags: trap, forecast, uz
**Javob:** Ma'lumotlarda bu savolga javob yo'q. Ma'lumotlar bazasida faqat 2022-yil 3-yanvardan 2026-yil 30-oktabrgacha bo'lgan bitimlar mavjud. Kelajak davrlari (2027-yil) uchun narxlar va prognoz ma'lumotlari yo'q.
```sql
-
```
answerable=False ok=True time=3.4s missing=[]
