# Golden check 2026-11-05 03:23 model=gemini:gemini-3.5-flash

**37/40 passed**

| id | result | time | missing |
|---|---|---|---|
| g01 | ok | 6.7s |  |
| g02 | ok | 6.4s |  |
| g03 | FAIL | 7.3s | number 797626 |
| g04 | ok | 5.5s |  |
| g05 | ok | 5.5s |  |
| g06 | ok | 4.4s |  |
| g07 | ok | 6.2s |  |
| g08 | ok | 5.1s |  |
| g09 | ok | 7.8s |  |
| g10 | ok | 3.4s |  |
| g11 | ok | 8.9s |  |
| g12 | ok | 5.5s |  |
| g13 | ok | 8.1s |  |
| g14 | ok | 5.8s |  |
| g15 | ok | 3.1s |  |
| g16 | ok | 4.6s |  |
| g17 | ok | 5.9s |  |
| g18 | ok | 8.0s |  |
| g19 | ok | 5.2s |  |
| g20 | FAIL | 9.3s | number 66; number 33 |
| g21 | ok | 7.4s |  |
| g22 | ok | 6.6s |  |
| g23 | FAIL | 4.1s | string 'DAP' |
| g24 | ok | 19.0s |  |
| g25 | ok | 5.7s |  |
| g26 | ok | 6.1s |  |
| g27 | ok | 6.9s |  |
| g28 | ok | 7.2s |  |
| g29 | ok | 3.7s |  |
| g30 | ok | 6.8s |  |
| g31 | ok | 7.3s |  |
| g32 | ok | 8.5s |  |
| g33 | ok | 6.5s |  |
| g34 | ok | 6.3s |  |
| g35 | ok | 3.6s |  |
| g36 | ok | 5.1s |  |
| g37 | ok | 2.3s |  |
| g38 | ok | 5.5s |  |
| g39 | ok | 5.2s |  |
| g40 | ok | 3.5s |  |

## g01. Кто покупатель и продавец по сделке 100001?
tags: deals, single-deal, ru
**Javob:** По сделке № 100001 от 03.01.2022 продавец — **RUKUSHO‘ FERMER MCHJ** (ИНН 921912462), покупатель — **"Bo‘juk Servis" MChJ** (ИНН 978906167). Товар: Шрот хлопковый, объём 79 720 кг, сумма 304 547 938.4 сум, статус «Исполнен».
```sql
SELECT d.deal_no, d.deal_date, d.product_canon_ru AS product, d.volume, d.unit, d.amount, d.currency, d.status, d.seller_inn, ps.name AS seller_name, d.buyer_inn, pb.name AS buyer_name FROM deals d LEFT JOIN participants ps ON ps.inn = d.seller_inn LEFT JOIN participants pb ON pb.inn = d.buyer_inn WHERE d.deal_no = 100001
LIMIT 50
```
answerable=True ok=True time=6.7s missing=[]

## g02. Сколько тонн хлопка-сырца продано в 2024 году?
tags: deals, volume, product, ru
**Javob:** В 2024 году было продано **1 672 494 955 кг** хлопка-сырца на общую сумму 12 915 322 307 346.02 сум (заключено **28 079** сделок).

Аннулированные сделки не учитывались.
```sql
SELECT unit, SUM(volume) AS total_volume, COUNT(*) AS deal_count, SUM(amount_uzs) AS total_amount_uzs FROM deals WHERE tnved = '520100' AND year = 2024 AND is_cancelled = 0 GROUP BY unit
LIMIT 50
```
answerable=True ok=True time=6.4s missing=[]

## g03. Какая средняя цена портландцемента за тонну в марте 2023 года?
tags: deals, price, product, ru
**Javob:** В марте 2023 года средневзвешенная цена портландцемента составила **795 653.4 сум** за т (общий объём: 86 020 т, всего **517** сделок).

Рассчитана средневзвешенная цена (общая сумма / общий объём). Аннулированные сделки исключены.
```sql
SELECT unit, currency, SUM(amount_uzs) / SUM(volume) AS weighted_avg_price, SUM(volume) AS total_volume, COUNT(*) AS deal_count FROM deals WHERE tnved = '252329' AND year = 2023 AND month = 3 AND is_cancelled = 0 GROUP BY unit, currency
LIMIT 50
```
answerable=True ok=False time=7.3s missing=['number 797626']

## g04. Топ-5 брокеров по количеству сделок в 2025 году
tags: brokers, top-n, ru
**Javob:** Топ-5 брокеров по количеству сделок за 2025 год:
BK111 — "Gucham Broker" MChJ: **6 692** сделок
BK005 — NAXON BROKER AJ: **5 690** сделок
BK106 — PASUR BROKER MCHJ: **5 602** сделок
BK017 — FIPI BROKER MCHJ: **4 641** сделок
BK102 — "Shofin Broker" MChJ: **4 594** сделок

Сделка, где брокер представлял обе стороны, посчитана один раз. Учтены сделки во всех статусах.
```sql
WITH bd AS (
  SELECT seller_broker AS code, deal_no FROM deals WHERE year = 2025 AND seller_broker IS NOT NULL
  UNION
  SELECT buyer_broker AS code, deal_no FROM deals WHERE year = 2025 AND buyer_broker IS NOT NULL
)
SELECT b.code, b.name, COUNT(*) AS deal_count
FROM bd
JOIN brokers b ON b.code = bd.code
GROUP BY b.code, b.name
ORDER BY deal_count DESC
LIMIT 5
```
answerable=True ok=True time=5.5s missing=[]

## g05. Сколько сделок аннулировано в 2026 году?
tags: deals, status, ru
**Javob:** Результат (напрямую из данных):
cancelled_count: 6 266; total_cancelled_amount_uzs: 3 248 050 920 296.03
```sql
SELECT COUNT(*) AS cancelled_count, SUM(amount_uzs) AS total_cancelled_amount_uzs FROM deals WHERE year = 2026 AND is_cancelled = 1
LIMIT 50
```
answerable=True ok=True time=5.5s missing=[]

## g06. Какой курс доллара был 15.06.2024?
tags: usd, ru
**Javob:** На 15.06.2024 курс доллара США составлял **11 862.46 сум** за 1 USD.
```sql
SELECT date, rate FROM usd_rates WHERE date = '2024-06-15'
LIMIT 50
```
answerable=True ok=True time=4.4s missing=[]

## g07. Сумма экспортных сделок в 2023 году в сумах
tags: deals, export, usd, ru
**Javob:** В 2023 году сумма экспортных сделок составила **2 199 458 684 636.28 сумов** (всего 1 118 сделок).

Аннулированные сделки не учитывались.
```sql
SELECT SUM(amount_uzs) AS total_amount_uzs, COUNT(*) AS deal_count FROM deals WHERE contract_type = 'Экспортный' AND year = 2023 AND is_cancelled = 0
LIMIT 50
```
answerable=True ok=True time=6.2s missing=[]

## g08. Сколько сделок у компании Qojo Invest?
tags: deals, company, trap, ru
**Javob:** По названию «Qojo Invest» найдено 2 компании:
"Qojo‘ Invest" OK (ИНН 912004930) — **69** сделок: 0 как продавец, 69 как покупатель
"Qojo Invest" MChJ (ИНН 915861525) — **72** сделок: 0 как продавец, 72 как покупатель

Учтены сделки во всех статусах.
```sql
SELECT p.inn, p.name, COUNT(d.deal_no) AS total_deals, SUM(CASE WHEN d.seller_inn = p.inn THEN 1 ELSE 0 END) AS as_seller, SUM(CASE WHEN d.buyer_inn = p.inn THEN 1 ELSE 0 END) AS as_buyer FROM participants p LEFT JOIN deals d ON d.seller_inn = p.inn OR d.buyer_inn = p.inn WHERE p.inn IN ('912004930', '915861525') GROUP BY p.inn, p.name
LIMIT 50
```
answerable=True ok=True time=5.1s missing=[]

## g09. В каком регионе больше всего сделок по муке?
tags: deals, region, product, ru
**Javob:** Больше всего сделок по пшеничной муке зарегистрировано в регионе **Farg‘ona viloyati** — **7 943** сделок (из них 7 404 не аннулировано).

Учитывались сделки по коду ТН ВЭД 110100 по региону склада продавца.
```sql
SELECT region, COUNT(*) AS deal_count, SUM(CASE WHEN is_cancelled = 0 THEN 1 ELSE 0 END) AS active_deals FROM deals WHERE tnved = '110100' GROUP BY region ORDER BY deal_count DESC LIMIT 1
```
answerable=True ok=True time=7.8s missing=[]

## g10. STIR 953758401 qaysi kompaniya va qaysi viloyatda?
tags: participants, company, uz
**Javob:** Natija (ma'lumotlardan to'g'ridan-to'g'ri):
inn: 953758401; name: "Go‘qe Prokat" MChJ; region: Farg‘ona viloyati; activity: Производитель; role: Sotuvchi; vat_payer: 1
```sql
SELECT inn, name, region, activity, role, vat_payer FROM participants WHERE inn = '953758401'
LIMIT 50
```
answerable=True ok=True time=3.4s missing=[]

## g11. Namangan viloyatida 2025-yilda eng ko'p sotilgan tovar qaysi?
tags: deals, region, top-n, uz
**Javob:** Natija (ma'lumotlardan to'g'ridan-to'g'ri):
tnved: 520100; product_name: Paxta xomashyosi; unit: kg; deal_count: 4 039; total_volume: 239 952 425; total_amount_uzs: 2 182 001 254 207.84
tnved: 170199; product_name: Shakar; unit: tonna; deal_count: 1 980; total_volume: 77 072; total_amount_uzs: 1 083 583 849 336
tnved: 100199; product_name: Oziq-ovqat bug'doyi; unit: tonna; deal_count: 860; total_volume: 242 947; total_amount_uzs: 1 030 628 859 043
tnved: 271019; product_name: Dizel yoqilg'isi / Mazut; unit: kg; deal_count: 1 239; total_volume: 35 008 317; total_amount_uzs: 490 475 036 048
tnved: 271012; product_name: Avtomobil benzini; unit: litr; deal_count: 1 079; total_volume: 43 099 000; total_amount_uzs: 464 184 178 000
```sql
SELECT tnved, product_canon_uz AS product_name, unit, COUNT(*) AS deal_count, SUM(volume) AS total_volume, SUM(amount_uzs) AS total_amount_uzs FROM deals WHERE region = 'Namangan viloyati' AND year = 2025 AND is_cancelled = 0 GROUP BY tnved, product_canon_uz, unit ORDER BY total_amount_uzs DESC LIMIT 5
```
answerable=True ok=True time=8.9s missing=[]

## g12. BK045 brokeri jami nechta bitimda qatnashgan?
tags: brokers, uz
**Javob:** "ДУСУНУ БРОКЕР" МЧЖ (BK045) brokeri jami **6 712 ta** bitimda qatnashgan (2 781 ta sotuvchi tarafida, 3 946 ta xaridor tarafida).

Sotuvchi va xaridor tomonida bir vaqtda qatnashgan bitimlar bir marta hisoblandi.
```sql
SELECT b.code, b.name, COUNT(DISTINCT d.deal_no) AS total_deals, COUNT(DISTINCT CASE WHEN d.seller_broker = b.code THEN d.deal_no END) AS as_seller_broker, COUNT(DISTINCT CASE WHEN d.buyer_broker = b.code THEN d.deal_no END) AS as_buyer_broker FROM brokers b LEFT JOIN deals d ON d.seller_broker = b.code OR d.buyer_broker = b.code WHERE b.code = 'BK045' GROUP BY b.code, b.name
LIMIT 50
```
answerable=True ok=True time=5.5s missing=[]

## g13. Eng yirik bitim qaysi?
tags: deals, top-n, uz
**Javob:** Natija (ma'lumotlardan to'g'ridan-to'g'ri):
deal_no: 247890; deal_date: 2023-10-09; product: Oziq-ovqat bug'doyi; volume: 8 703; unit: tonna; amount: 30 190 376 286; currency: so'm; amount_uzs: 30 190 376 286; status: Bajarilgan; seller_inn: 902946936; seller_name: CHO‘HE KLASTER MCHJ; buyer_inn: 916644459; buyer_name: "МИКИ БИЗНЕС" ҚК
```sql
SELECT d.deal_no, d.deal_date, d.product_canon_uz AS product, d.volume, d.unit, d.amount, d.currency, d.amount_uzs, d.status, d.seller_inn, ps.name AS seller_name, d.buyer_inn, pb.name AS buyer_name FROM deals d LEFT JOIN participants ps ON ps.inn = d.seller_inn LEFT JOIN participants pb ON pb.inn = d.buyer_inn WHERE d.is_cancelled = 0 ORDER BY d.amount_uzs DESC LIMIT 1
```
answerable=True ok=True time=8.1s missing=[]

## g14. Yetkazib berish muddati kechikkan bitimlar soni qancha?
tags: deals, delay, uz
**Javob:** Natija (ma'lumotlardan to'g'ridan-to'g'ri):
delayed_deals_count: 17 805; avg_delay_days: 7.95; total_amount_uzs: 7 704 993 702 929.16
```sql
SELECT COUNT(*) AS delayed_deals_count, AVG(delivery_delay_days) AS avg_delay_days, SUM(amount_uzs) AS total_amount_uzs FROM deals WHERE delivery_delay_days > 0
LIMIT 50
```
answerable=True ok=True time=5.8s missing=[]

## g15. Сколько контрактов с базисом поставки EXW?
tags: contracts, ru
**Javob:** Зарегистрировано **5 194** контрактов с базисом поставки EXW.
```sql
SELECT COUNT(*) AS contract_count FROM contracts WHERE delivery_basis = 'EXW'
LIMIT 50
```
answerable=True ok=True time=3.1s missing=[]

## g16. Birorta ham bitim tuzilmagan shartnomalar nechta?
tags: contracts, uz
**Javob:** Natija (ma'lumotlardan to'g'ridan-to'g'ri):
unused_contracts_count: 133
```sql
SELECT COUNT(c.contract_no) AS unused_contracts_count FROM contracts c LEFT JOIN deals d ON c.contract_no = d.contract_no WHERE d.contract_no IS NULL
LIMIT 50
```
answerable=True ok=True time=4.6s missing=[]

## g17. Сколько контрактов со складом в Наманганской области?
tags: contracts, region, ru
**Javob:** Со складом в Наманганской области зарегистрировано **667** контрактов.
```sql
SELECT COUNT(*) AS contract_count FROM contracts WHERE region = 'Namangan viloyati' OR region_ru = 'Наманганская область'
LIMIT 50
```
answerable=True ok=True time=5.9s missing=[]

## g18. Fyuchers shaklidagi shartnomalar nechta?
tags: contracts, uz
**Javob:** Birja tizimida fyuchers shaklidagi jami **79 ta** shartnoma ro'yxatga olingan.
```sql
SELECT COUNT(*) AS contract_count FROM contracts WHERE contract_form = 'Фьючерс'
LIMIT 50
```
answerable=True ok=True time=8.0s missing=[]

## g19. Сколько экспортных контрактов зарегистрировано?
tags: contracts, export, ru
**Javob:** Всего зарегистрировано **148** экспортных контрактов.
```sql
SELECT COUNT(*) AS contract_count FROM contracts WHERE contract_type = 'Экспортный'
LIMIT 50
```
answerable=True ok=True time=5.2s missing=[]

## g20. 100118-shartnoma bo'yicha to'lov muddati va yetkazib berish muddati necha kun?
tags: contracts, single-contract, uz
**Javob:** Natija (ma'lumotlardan to'g'ridan-to'g'ri):
deal_no: 100118; contract_no: 100014; deal_date: 2022-01-03; product: Bug'doy uni; payment_days: 8; delivery_days: 16
```sql
SELECT d.deal_no, d.contract_no, d.deal_date, d.product_canon_uz AS product, c.payment_days, c.delivery_days FROM deals d LEFT JOIN contracts c ON d.contract_no = c.contract_no WHERE d.deal_no = 100118
LIMIT 50
```
answerable=True ok=False time=9.3s missing=['number 66', 'number 33']

## g21. Какая базовая цена в контракте 100002 и что это за товар?
tags: contracts, single-contract, price, ru
**Javob:** По контракту № 100002 базовая цена составляет **2 720 643 сум** за 1 т. Товар: **Аммиачная селитра** (Аммиачная селитра).
```sql
SELECT contract_no, product_name, product_canon_ru, base_price, currency, unit FROM contracts WHERE contract_no = '100002'
LIMIT 50
```
answerable=True ok=True time=7.4s missing=[]

## g22. Eng ko'p shartnoma ro'yxatdan o'tkazgan sotuvchi qaysi?
tags: contracts, company, top-n, uz
**Javob:** Natija (ma'lumotlardan to'g'ridan-to'g'ri):
inn: 996237847; name: VISAQE SERVIS MAS’ULIYATI CHEKLANGAN JAMIYATI; contract_count: 60
```sql
SELECT p.inn, p.name, COUNT(c.contract_no) AS contract_count FROM contracts c JOIN participants p ON p.inn = c.seller_inn GROUP BY p.inn, p.name ORDER BY contract_count DESC LIMIT 1
```
answerable=True ok=True time=6.6s missing=[]

## g23. DAP yetkazib berish bazisidagi shartnomalar soni qancha?
tags: contracts, uz
**Javob:** Natija (ma'lumotlardan to'g'ridan-to'g'ri):
contract_count: 374
```sql
SELECT COUNT(*) AS contract_count FROM contracts WHERE delivery_basis = 'DAP'
LIMIT 50
```
answerable=True ok=False time=4.1s missing=["string 'DAP'"]

## g24. Сколько сделок по хлопку-сырцу 1 сорта 1 класса?
tags: deals, grade, product, ru
**Javob:** Всего по хлопку-сырцу 1 сорта 1 класса зарегистрировано **29 136** сделок (27 341 исполнено/активно, 1 795 аннулировано) на общий объём **1 618 574 496 кг**.

Учтены сделки во всех статусах, объём суммирован только по неаннулированным сделкам.
```sql
SELECT COUNT(*) AS total_deals, SUM(CASE WHEN is_cancelled = 0 THEN 1 ELSE 0 END) AS active_deals, SUM(CASE WHEN is_cancelled = 1 THEN 1 ELSE 0 END) AS cancelled_deals, SUM(CASE WHEN is_cancelled = 0 THEN volume ELSE 0 END) AS total_volume, unit FROM deals WHERE tnved = '520100' AND sort_no = 1 AND class_no = 1 GROUP BY unit
LIMIT 50
```
answerable=True ok=True time=19.0s missing=[]

## g25. 2023-yilda 2-nav paxta xomashyosi qancha sotilgan?
tags: deals, grade, volume, uz
**Javob:** 2023-yilda 2-navli paxta xomashyosi jami **404 202.13 tonna** (404 202 126 kg) sotilgan — **6 749 ta** bitim, umumiy summasi 2 679 870 122 352.91 so'm.

Bekor qilingan bitimlar hisobga olinmadi.
```sql
SELECT unit, SUM(volume) AS total_volume, COUNT(*) AS deal_count, SUM(amount_uzs) AS total_amount_uzs FROM deals WHERE tnved = '520100' AND sort_no = 2 AND year = 2023 AND is_cancelled = 0 GROUP BY unit
LIMIT 50
```
answerable=True ok=True time=5.7s missing=[]

## g26. 2025-yilda oliy nav bug'doy uni qancha sotilgan?
tags: deals, grade, volume, uz
**Javob:** Natija (ma'lumotlardan to'g'ridan-to'g'ri):
unit: kg; total_volume: 20 708 500; deal_count: 1 189; total_amount_uzs: 129 266 244 784
```sql
SELECT unit, SUM(volume) AS total_volume, COUNT(*) AS deal_count, SUM(amount_uzs) AS total_amount_uzs FROM deals WHERE tnved = '110100' AND year = 2025 AND (sort_no = 0 OR class_no = 0) AND is_cancelled = 0 GROUP BY unit
LIMIT 50
```
answerable=True ok=True time=6.1s missing=[]

## g27. 4-klass bug'doy bo'yicha jami nechta bitim bor?
tags: deals, grade, product, uz
**Javob:** 4-sinf bug'doy bo'yicha jami **21 471 ta** bitim ro'yxatga olingan (shundan **20 133 ta** amaldagi, **1 338 ta** bekor qilingan), amaldagi bitimlar hajmi **5 529 704 tonna**.

Barcha yillar uchun ma'lumotlar keltirildi.
```sql
SELECT COUNT(*) AS total_deals, SUM(CASE WHEN is_cancelled = 0 THEN 1 ELSE 0 END) AS valid_deals, SUM(CASE WHEN is_cancelled = 1 THEN 1 ELSE 0 END) AS cancelled_deals, SUM(CASE WHEN is_cancelled = 0 THEN volume ELSE 0 END) AS total_volume, unit FROM deals WHERE tnved = '100199' AND class_no = 4 GROUP BY unit
LIMIT 50
```
answerable=True ok=True time=6.9s missing=[]

## g28. 2024-yilda eksport bitimlari summasi dollarda va so'mda qancha?
tags: deals, export, usd, uz
**Javob:** Natija (ma'lumotlardan to'g'ridan-to'g'ri):
total_usd: 202 495 621; total_uzs: 2 420 672 267 384.07; deal_count: 1 229
```sql
SELECT SUM(amount) AS total_usd, SUM(amount_uzs) AS total_uzs, COUNT(*) AS deal_count FROM deals WHERE year = 2024 AND contract_type = 'Экспортный' AND is_cancelled = 0
LIMIT 50
```
answerable=True ok=True time=7.2s missing=[]

## g29. Какой курс доллара был 01.03.2025?
tags: usd, ru
**Javob:** Курс доллара США на 01.03.2025 составлял **12 515.24 сум** за 1 USD.
```sql
SELECT date, rate FROM usd_rates WHERE date = '2025-03-01'
LIMIT 50
```
answerable=True ok=True time=3.7s missing=[]

## g30. 2022-yilda nechta eksport bitimi tuzilgan?
tags: deals, export, uz
**Javob:** Natija (ma'lumotlardan to'g'ridan-to'g'ri):
total_deals: 1 317; valid_deals: 1 237; cancelled_deals: 80; valid_amount_usd: 222 710 633.68; valid_amount_uzs: 2 464 045 852 849.85
```sql
SELECT COUNT(*) AS total_deals, SUM(CASE WHEN is_cancelled = 0 THEN 1 ELSE 0 END) AS valid_deals, SUM(CASE WHEN is_cancelled = 1 THEN 1 ELSE 0 END) AS cancelled_deals, SUM(CASE WHEN is_cancelled = 0 THEN amount ELSE 0 END) AS valid_amount_usd, SUM(CASE WHEN is_cancelled = 0 THEN amount_uzs ELSE 0 END) AS valid_amount_uzs FROM deals WHERE year = 2022 AND contract_type = 'Экспортный'
LIMIT 50
```
answerable=True ok=True time=6.8s missing=[]

## g31. Eng katta eksport bitimi qaysi va summasi dollarda qancha?
tags: deals, export, usd, top-n, uz
**Javob:** Natija (ma'lumotlardan to'g'ridan-to'g'ri):
deal_no: 547500; deal_date: 2026-06-24; product_name: Mis katodi; volume: 147; unit: tonna; amount: 1 683 554.25; currency: AQSh dollari; status: Bajarilgan; seller_inn: 992421731; seller_name: TIZAHI METALL MCHJ; buyer_inn: 919788432; buyer_name: "Bejul Savdo" OK
```sql
SELECT d.deal_no, d.deal_date, d.product_canon_uz AS product_name, d.volume, d.unit, d.amount, d.currency, d.status, d.seller_inn, ps.name AS seller_name, d.buyer_inn, pb.name AS buyer_name FROM deals d LEFT JOIN participants ps ON ps.inn = d.seller_inn LEFT JOIN participants pb ON pb.inn = d.buyer_inn WHERE d.contract_type = 'Экспортный' AND d.is_cancelled = 0 ORDER BY d.amount DESC LIMIT 1
```
answerable=True ok=True time=7.3s missing=[]

## g32. Сколько сделок у брокера BK001 в 2024 году?
tags: brokers, ru
**Javob:** В 2024 году брокер **"КЕКУХО БРОКЕР" МЧЖ** (BK001) принял участие в **1 124** сделках (1 049 заключено/исполнено, 75 аннулировано).

Учтены сделки во всех статусах. Каждая сделка посчитана один раз, даже если брокер обслуживал обе стороны.
```sql
SELECT b.code, b.name, COUNT(DISTINCT d.deal_no) AS total_deals, COUNT(DISTINCT CASE WHEN d.is_cancelled = 0 THEN d.deal_no END) AS active_deals, COUNT(DISTINCT CASE WHEN d.is_cancelled = 1 THEN d.deal_no END) AS cancelled_deals FROM brokers b LEFT JOIN deals d ON (d.seller_broker = b.code OR d.buyer_broker = b.code) AND d.year = 2024 WHERE b.code = 'BK001' GROUP BY b.code, b.name
LIMIT 50
```
answerable=True ok=True time=8.5s missing=[]

## g33. Qaysi broker jami eng ko'p bitimda qatnashgan?
tags: brokers, top-n, uz
**Javob:** Eng ko'p bitimda qatnashgan broker — **"Gucham Broker" MChJ** (BK111), jami **32 422 ta** bitim.

Broker sotuvchi yoki xaridor sifatida qatnashgan barcha bitimlar hisoblandi, har bir bitim bir marta inobatga olindi.
```sql
WITH bd AS (SELECT seller_broker AS code, deal_no FROM deals WHERE seller_broker IS NOT NULL UNION SELECT buyer_broker AS code, deal_no FROM deals WHERE buyer_broker IS NOT NULL) SELECT b.code, b.name, COUNT(*) AS deal_count FROM bd JOIN brokers b ON b.code = bd.code GROUP BY b.code, b.name ORDER BY deal_count DESC LIMIT 1
```
answerable=True ok=True time=6.5s missing=[]

## g34. Какой брокер был брокером продавца в наибольшем числе сделок?
tags: brokers, top-n, ru
**Javob:** Лидером среди брокеров продавца является **"Gucham Broker" MChJ** (код BK111) с результатом **21 471** сделок.

Учтены сделки во всех статусах.
```sql
SELECT b.code, b.name, COUNT(*) AS deal_count FROM deals d JOIN brokers b ON b.code = d.seller_broker GROUP BY b.code, b.name ORDER BY deal_count DESC LIMIT 1
```
answerable=True ok=True time=6.3s missing=[]

## g35. Какой объём торгов пшеницей был в 2021 году?
tags: trap, period, ru
**Javob:** В данных нет ответа на этот вопрос. В базе данных содержатся сведения только за период с 3 января 2022 года по 30 октября 2026 года. Данные за 2021 год отсутствуют.
```sql
-
```
answerable=False ok=True time=3.6s missing=[]

## g36. Noyabr 2026 da qancha un sotilgan?
tags: trap, period, uz
**Javob:** Ma'lumotlarda bu savolga javob yo'q. Ma'lumotlar bazasidagi bitimlar 2022-yil 3-yanvardan 2026-yil 30-oktabrgacha bo'lgan davrni qamrab oladi. 2026-yil noyabr oyi bo'yicha ma'lumotlar mavjud emas.
```sql
-
```
answerable=False ok=True time=5.1s missing=[]

## g37. Кто директор компании с ИНН 953758401 и какой у неё телефон?
tags: trap, participants, ru
**Javob:** В данных нет ответа на этот вопрос. В базе данных нет сведений о руководителях (директорах) и контактных телефонах компаний. Доступны только ИНН, наименование, регион, вид деятельности, статус плательщика НДС и история биржевых сделок.
```sql
-
```
answerable=False ok=True time=2.3s missing=[]

## g38. 100437-bitim bo'yicha xaridor kim?
tags: trap, single-deal, uz
**Javob:** Ma'lumotlarda mos yozuv topilmadi.
```sql
SELECT d.deal_no, d.deal_date, d.buyer_inn, pb.name AS buyer_name, d.seller_inn, ps.name AS seller_name, d.product_canon_uz AS product, d.volume, d.unit, d.amount, d.currency, d.status FROM deals d LEFT JOIN participants pb ON pb.inn = d.buyer_inn LEFT JOIN participants ps ON ps.inn = d.seller_inn WHERE d.deal_no = 100437
LIMIT 50
```
answerable=True ok=True time=5.5s missing=[]

## g39. Сколько золота продано на бирже в 2024 году?
tags: trap, product, ru
**Javob:** В данных нет ответа на этот вопрос. В базе данных биржи отсутствуют данные о продажах золота (золото не входит в перечень товаров, торгуемых на бирже).
```sql
-
```
answerable=False ok=True time=5.2s missing=[]

## g40. 2027-yilda paxta narxi qancha bo'ladi?
tags: trap, forecast, uz
**Javob:** Ma'lumotlarda bu savolga javob yo'q. Ma'lumotlar bazasida kelajak (2027-yil) uchun narxlar va prognozlar mavjud emas. Baza faqat 2022-01-03 dan 2026-10-30 gacha bo'lgan amaldagi birja bitimlarini o'z ichiga oladi.
```sql
-
```
answerable=False ok=True time=3.5s missing=[]
