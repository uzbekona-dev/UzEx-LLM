# Golden check 2026-11-05 02:53 model=gemini:gemini-3.5-flash

**40/40 passed**

| id | result | time | missing |
|---|---|---|---|
| g01 | ok | 13.3s |  |
| g02 | ok | 12.9s |  |
| g03 | ok | 12.5s |  |
| g04 | ok | 14.8s |  |
| g05 | ok | 14.2s |  |
| g06 | ok | 5.5s |  |
| g07 | ok | 12.6s |  |
| g08 | ok | 11.2s |  |
| g09 | ok | 13.3s |  |
| g10 | ok | 6.4s |  |
| g11 | ok | 23.5s |  |
| g12 | ok | 8.4s |  |
| g13 | ok | 16.4s |  |
| g14 | ok | 7.7s |  |
| g15 | ok | 6.5s |  |
| g16 | ok | 7.1s |  |
| g17 | ok | 7.0s |  |
| g18 | ok | 7.9s |  |
| g19 | ok | 5.3s |  |
| g20 | ok | 20.3s |  |
| g21 | ok | 12.3s |  |
| g22 | ok | 13.2s |  |
| g23 | ok | 5.4s |  |
| g24 | ok | 8.2s |  |
| g25 | ok | 10.7s |  |
| g26 | ok | 13.2s |  |
| g27 | ok | 9.5s |  |
| g28 | ok | 17.8s |  |
| g29 | ok | 5.7s |  |
| g30 | ok | 8.7s |  |
| g31 | ok | 18.9s |  |
| g32 | ok | 6.7s |  |
| g33 | ok | 9.3s |  |
| g34 | ok | 7.7s |  |
| g35 | ok | 3.0s |  |
| g36 | ok | 4.4s |  |
| g37 | ok | 2.1s |  |
| g38 | ok | 7.5s |  |
| g39 | ok | 5.0s |  |
| g40 | ok | 3.2s |  |

## g01. Кто покупатель и продавец по сделке 100001?
tags: deals, single-deal, ru
**Javob:** По сделке №100001 продавцом выступает **RUKUSHO‘ FERMER MCHJ** (ИНН 921912462), а покупателем — **"Bo‘juk Servis" MChJ** (ИНН 978906167). Сделка оформлена 2022-01-03 на товар «Шрот хлопковый» объемом 79.72 тонны (79 720 кг) на сумму 304 547 938.4 Узбекский сум со статусом «Исполнен».
```sql
SELECT d.deal_no, d.deal_date, d.product_canon_ru, d.seller_inn, ps.name AS seller_name, d.buyer_inn, pb.name AS buyer_name, d.volume, d.unit, d.amount, d.currency, d.status, d.seller_broker, d.buyer_broker FROM deals d LEFT JOIN participants ps ON d.seller_inn = ps.inn LEFT JOIN participants pb ON d.buyer_inn = pb.inn WHERE d.deal_no = 100001 LIMIT 50
```
answerable=True ok=True time=13.3s missing=[]

## g02. Сколько тонн хлопка-сырца продано в 2024 году?
tags: deals, volume, product, ru
**Javob:** В 2024 году общий объем проданного хлопка-сырца составил **1 672 494.955 тонн** (1 672 494 955 кг) в рамках 28 079 сделок.

Расчет выполнен без учета аннулированных сделок.
```sql
SELECT unit, SUM(volume) AS total_volume, COUNT(*) AS total_deals FROM deals WHERE tnved = '520100' AND year = 2024 AND is_cancelled = 0 GROUP BY unit
LIMIT 50
```
answerable=True ok=True time=12.9s missing=[]

## g03. Какая средняя цена портландцемента за тонну в марте 2023 года?
tags: deals, price, product, ru
**Javob:** В марте 2023 года средневзвешенная цена портландцемента составила **795 653.40 сум** за тонну, а средняя цена единицы — **797 626.31 сум** за тонну. Общий объем по 517 сделкам составил 86 020 тонн.

Расчет выполнен без учета аннулированных сделок.
```sql
SELECT unit, currency, ROUND(SUM(amount_uzs) / SUM(volume), 2) AS weighted_avg_price, ROUND(AVG(unit_price), 2) AS avg_unit_price, SUM(volume) AS total_volume, COUNT(*) AS deals_count FROM deals WHERE tnved = '252329' AND year = 2023 AND month = 3 AND unit = 'тонна' AND is_cancelled = 0 GROUP BY unit, currency
LIMIT 50
```
answerable=True ok=True time=12.5s missing=[]

## g04. Топ-5 брокеров по количеству сделок в 2025 году
tags: brokers, top-n, ru
**Javob:** Лидером по количеству сделок в 2025 году стал брокер "Gucham Broker" MChJ с показателем **6 692 сделки**.

Топ-5 брокеров:
1. "Gucham Broker" MChJ (код BK111) — **6 692 сделки**
2. NAXON BROKER AJ (код BK005) — **5 690 сделок**
3. PASUR BROKER MCHJ (код BK106) — **5 602 сделки**
4. FIPI BROKER MCHJ (код BK017) — 4 641 сделка
5. "Shofin Broker" MChJ (код BK102) — 4 594 сделки

При расчете сделка учитывалась единожды, даже если брокер участвовал с обеих сторон или только со стороны продавца/покупателя.
```sql
WITH broker_deals AS (
    SELECT seller_broker AS broker_code, deal_no FROM deals WHERE year = 2025 AND seller_broker IS NOT NULL
    UNION
    SELECT buyer_broker AS broker_code, deal_no FROM deals WHERE year = 2025 AND buyer_broker IS NOT NULL
)
SELECT b.code, b.name, COUNT(bd.deal_no) AS deal_count
FROM broker_deals bd
JOIN brokers b ON bd.broker_code = b.code
GROUP BY b.code, b.name
ORDER BY deal_count DESC
LIMIT 5
```
answerable=True ok=True time=14.8s missing=[]

## g05. Сколько сделок аннулировано в 2026 году?
tags: deals, status, ru
**Javob:** В 2026 году было аннулировано **6 266 сделок** на общую сумму **3 248 050 920 296.032 узбекских сумов**.
```sql
SELECT COUNT(*) AS cancelled_deals_count, SUM(amount_uzs) AS total_cancelled_amount_uzs FROM deals WHERE year = 2026 AND is_cancelled = 1
LIMIT 50
```
answerable=True ok=True time=14.2s missing=[]

## g06. Какой курс доллара был 15.06.2024?
tags: usd, ru
**Javob:** 15 июня 2024 года курс доллара США составлял **11 862.46** сумов.
```sql
SELECT date, rate FROM usd_rates WHERE date = '2024-06-15'
LIMIT 50
```
answerable=True ok=True time=5.5s missing=[]

## g07. Сумма экспортных сделок в 2023 году в сумах
tags: deals, export, usd, ru
**Javob:** Общая сумма экспортных сделок за 2023 год составляет **2 199 458 684 636.28 сум** (всего **1 118** сделок).

При расчете не учитывались аннулированные сделки.
```sql
SELECT SUM(CASE WHEN is_cancelled = 0 THEN amount_uzs ELSE 0 END) AS total_amount_uzs, COUNT(CASE WHEN is_cancelled = 0 THEN 1 END) AS deal_count, SUM(CASE WHEN is_cancelled = 1 THEN amount_uzs ELSE 0 END) AS cancelled_amount_uzs, COUNT(CASE WHEN is_cancelled = 1 THEN 1 END) AS cancelled_deal_count FROM deals WHERE contract_type = 'Экспортный' AND year = 2023
LIMIT 50
```
answerable=True ok=True time=12.6s missing=[]

## g08. Сколько сделок у компании Qojo Invest?
tags: deals, company, trap, ru
**Javob:** Найдено две компании с похожим названием:

- **"Qojo‘ Invest" OK** (ИНН 912004930): всего **69** сделок (0 в качестве продавца и 69 в качестве покупателя).
- **"Qojo Invest" MChJ** (ИНН 915861525): всего **72** сделки (0 в качестве продавца и 72 в качестве покупателя).
```sql
SELECT p.inn, p.name, COUNT(d.deal_no) AS total_deals, COUNT(CASE WHEN d.seller_inn = p.inn THEN 1 END) AS as_seller, COUNT(CASE WHEN d.buyer_inn = p.inn THEN 1 END) AS as_buyer FROM participants p LEFT JOIN deals d ON p.inn = d.seller_inn OR p.inn = d.buyer_inn WHERE p.inn IN ('912004930', '915861525') GROUP BY p.inn, p.name
LIMIT 50
```
answerable=True ok=True time=11.2s missing=[]

## g09. В каком регионе больше всего сделок по муке?
tags: deals, region, product, ru
**Javob:** Больше всего сделок по пшеничной муке зарегистрировано в регионе **Farg‘ona viloyati** — **7 943 сделки** на общий объем 128 957.1 тонна (128 957 100 кг) суммой 626 641 249 524 сум.

Топ регионов по количеству сделок:
- Farg‘ona viloyati: 7 943 сделки (128 957.1 тонна / 128 957 100 кг)
- Toshkent shahri: 5 577 сделок (91 228.3 тонн / 91 228 300 кг)
- Namangan viloyati: 4 503 сделки (72 340.6 тонн / 72 340 600 кг)
- Andijon viloyati: 2 937 сделок (47 597.8 тонн / 47 597 800 кг)
- Jizzax viloyati: 2 144 сделки (34 083.2 тонн / 34 083 200 кг)
- Toshkent viloyati: 2 080 сделок (33 773.3 тонн / 33 773 300 кг)
- Qashqadaryo viloyati: 1 874 сделки (30 331.4 тонн / 30 331 400 кг)
- Buxoro viloyati: 1 853 сделки (29 160.8 тонн / 29 160 800 кг)
- Xorazm viloyati: 1 327 сделок (20 722.9 тонн / 20 722 900 кг)
- Sirdaryo viloyati: 1 028 сделок (16 759.7 тонн / 16 759 700 кг)

Аннулированные сделки исключены из расчета объема и суммы.
```sql
SELECT region, COUNT(*) AS deal_count, SUM(CASE WHEN is_cancelled = 0 THEN volume ELSE 0 END) AS total_volume, unit, SUM(CASE WHEN is_cancelled = 0 THEN amount_uzs ELSE 0 END) AS total_amount_uzs FROM deals WHERE tnved = '110100' GROUP BY region, unit ORDER BY deal_count DESC LIMIT 10
```
answerable=True ok=True time=13.3s missing=[]

## g10. STIR 953758401 qaysi kompaniya va qaysi viloyatda?
tags: participants, company, uz
**Javob:** STIR 953758401 raqamli kompaniya — **"Go‘qe Prokat" MChJ** bo‘lib, u **Farg‘ona viloyati**da ro‘yxatdan o‘tgan. Faoliyat turi — Ishlab chiqaruvchi (Производитель), birjadagi roli — Sotuvchi.
```sql
SELECT inn, name, region, activity, role, vat_payer FROM participants WHERE inn = '953758401' LIMIT 50
```
answerable=True ok=True time=6.4s missing=[]

## g11. Namangan viloyatida 2025-yilda eng ko'p sotilgan tovar qaysi?
tags: deals, region, top-n, uz
**Javob:** 2025-yilda Namangan viloyatida eng ko'p sotilgan tovar **Paxta xomashyosi** (TNVED 520100) bo'lib, uning umumiy savdo hajmi **2 182 001 254 207.84 so'm**ni tashkil etdi (239 952.425 tonna (239 952 425 kg), 4 039 ta bitim). 

Eng yuqori savdo hajmiga ega tovarlar:
- Paxta xomashyosi (TNVED 520100): 2 182 001 254 207.84 so'm (239 952.425 tonna (239 952 425 kg))
- Shakar (TNVED 170199): 1 083 583 849 336 so'm (77 072 tonna)
- Oziq-ovqat bug'doyi (TNVED 100199): 1 030 628 859 043 so'm (242 947 tonna)
- Dizel yoqilg'isi / Mazut (TNVED 271019): 490 475 036 048 so'm (35 008.317 tonna (35 008 317 kg))
- Avtomobil benzini (TNVED 271012): 464 184 178 000 so'm (43 099 000 litr)
- Po'lat armatura (TNVED 721420): 209 832 090 798 so'm (18 041 tonna)
- Paxta ipi (kalava) (TNVED 520512): 205 127 133 643.20 so'm (3 995 tonna)
- Paxta shroti (TNVED 230610): 174 411 171 106.52 so'm (33 783.346 tonna (33 783 346 kg))
- Bug'doy uni (TNVED 110100): 142 254 310 273 so'm (27 002.6 tonna (27 002 600 kg))
- Paxta yog'i (TNVED 151229): 134 748 033 535 so'm (5 383 tonna)

Hisob-kitobda bekor qilingan bitimlar inobatga olinmagan.
```sql
SELECT tnved, product_canon_uz, unit, COUNT(*) AS deal_count, SUM(volume) AS total_volume, SUM(amount_uzs) AS total_amount_uzs FROM deals WHERE region = 'Namangan viloyati' AND year = 2025 AND is_cancelled = 0 GROUP BY tnved, product_canon_uz, unit ORDER BY total_amount_uzs DESC LIMIT 10
```
answerable=True ok=True time=23.5s missing=[]

## g12. BK045 brokeri jami nechta bitimda qatnashgan?
tags: brokers, uz
**Javob:** BK045 brokeri qatnashgan barcha bitimlar soni **6 712 ta**ni tashkil etadi. 

Hisob-kitobda broker sotuvchi yoki xaridor sifatida qatnashgan barcha holatdagi bitimlar inobatga olingan.
```sql
SELECT COUNT(DISTINCT deal_no) AS total_deals FROM deals WHERE seller_broker = 'BK045' OR buyer_broker = 'BK045'
LIMIT 50
```
answerable=True ok=True time=8.4s missing=[]

## g13. Eng yirik bitim qaysi?
tags: deals, top-n, uz
**Javob:** Natija (ma'lumotlardan to'g'ridan-to'g'ri):
deal_no: 247890; deal_date: 2023-10-09; product: Oziq-ovqat bug'doyi; volume: 8703.0; unit: тонна; amount: 30190376286.0; currency: Узбекский сум; amount_uzs: 30190376286.0; status: Исполнен; seller_inn: 902946936; seller_name: CHO‘HE KLASTER MCHJ; buyer_inn: 916644459; buyer_name: "МИКИ БИЗНЕС" ҚК; seller_broker: BK119; buyer_broker: BK105
```sql
SELECT d.deal_no, d.deal_date, d.product_canon_uz AS product, d.volume, d.unit, d.amount, d.currency, d.amount_uzs, d.status, d.seller_inn, sp.name AS seller_name, d.buyer_inn, bp.name AS buyer_name, d.seller_broker, d.buyer_broker FROM deals d LEFT JOIN participants sp ON d.seller_inn = sp.inn LEFT JOIN participants bp ON d.buyer_inn = bp.inn WHERE d.is_cancelled = 0 ORDER BY d.amount_uzs DESC LIMIT 1
```
answerable=True ok=True time=16.4s missing=[]

## g14. Yetkazib berish muddati kechikkan bitimlar soni qancha?
tags: deals, delay, uz
**Javob:** Yetkazib berish muddati kechikkan bitimlar soni **17 805 ta**ni tashkil etadi.
```sql
SELECT COUNT(*) AS delayed_delivery_deals_count FROM deals WHERE delivery_delay_days > 0
LIMIT 50
```
answerable=True ok=True time=7.7s missing=[]

## g15. Сколько контрактов с базисом поставки EXW?
tags: contracts, ru
**Javob:** Общее количество зарегистрированных контрактов с базисом поставки EXW составляет **5 194**.
```sql
SELECT COUNT(*) AS total_contracts FROM contracts WHERE delivery_basis = 'EXW'
LIMIT 50
```
answerable=True ok=True time=6.5s missing=[]

## g16. Birorta ham bitim tuzilmagan shartnomalar nechta?
tags: contracts, uz
**Javob:** Birorta ham bitim tuzilmagan shartnomalar soni **133 ta**ni tashkil etadi.
```sql
SELECT COUNT(*) AS unused_contracts_count FROM contracts c LEFT JOIN deals d ON c.contract_no = d.contract_no WHERE d.deal_no IS NULL
LIMIT 50
```
answerable=True ok=True time=7.1s missing=[]

## g17. Сколько контрактов со складом в Наманганской области?
tags: contracts, region, ru
**Javob:** Со складом в Наманганской области зарегистрировано **667 контрактов**.
```sql
SELECT COUNT(*) AS total_contracts FROM contracts WHERE region = 'Namangan viloyati'
LIMIT 50
```
answerable=True ok=True time=7.0s missing=[]

## g18. Fyuchers shaklidagi shartnomalar nechta?
tags: contracts, uz
**Javob:** Fyuchers shaklidagi shartnomalar soni **79 ta**ni tashkil etadi.
```sql
SELECT COUNT(*) AS total_contracts FROM contracts WHERE contract_form = 'Фьючерс'
LIMIT 50
```
answerable=True ok=True time=7.9s missing=[]

## g19. Сколько экспортных контрактов зарегистрировано?
tags: contracts, export, ru
**Javob:** Зарегистрировано **148** экспортных контрактов.
```sql
SELECT COUNT(*) AS total_export_contracts FROM contracts WHERE contract_type = 'Экспортный'
LIMIT 50
```
answerable=True ok=True time=5.3s missing=[]

## g20. 100118-shartnoma bo'yicha to'lov muddati va yetkazib berish muddati necha kun?
tags: contracts, single-contract, uz
**Javob:** Natija (ma'lumotlardan to'g'ridan-to'g'ri):
contract_no: 100014; deal_no: 100118; payment_days: 8; delivery_days: 16; payment_delay_days: 0; delivery_delay_days: -15
contract_no: 100118; deal_no: 116470; payment_days: 66; delivery_days: 33; payment_delay_days: -8; delivery_delay_days: -23
contract_no: 100118; deal_no: 116485; payment_days: 66; delivery_days: 33; payment_delay_days: -4; delivery_delay_days: 0
contract_no: 100118; deal_no: 116542; payment_days: 66; delivery_days: 33; payment_delay_days: -26; delivery_delay_days: -25
contract_no: 100118; deal_no: 116567; payment_days: 66; delivery_days: 33; payment_delay_days: -18; delivery_delay_days: -23
contract_no: 100118; deal_no: 116571; payment_days: 66; delivery_days: 33; payment_delay_days: -24; delivery_delay_days: -1
contract_no: 100118; deal_no: 116613; payment_days: 66; delivery_days: 33; payment_delay_days: -5; delivery_delay_days: -28
contract_no: 100118; deal_no: 116630; payment_days: 66; delivery_days: 33; payment_delay_days: -8; delivery_delay_days: -6
contract_no: 100118; deal_no: 116692; payment_days: 66; delivery_days: 33; payment_delay_days: -19; delivery_delay_days: -17
contract_no: 100118; deal_no: 116816; payment_days: 66; delivery_days: 33; payment_delay_days: -2; delivery_delay_days: -3
```sql
SELECT c.contract_no, d.deal_no, c.payment_days, c.delivery_days, d.payment_delay_days, d.delivery_delay_days FROM contracts c LEFT JOIN deals d ON c.contract_no = d.contract_no WHERE c.contract_no = '100118' OR d.deal_no = 100118 LIMIT 50
```
answerable=True ok=True time=20.3s missing=[]

## g21. Какая базовая цена в контракте 100002 и что это за товар?
tags: contracts, single-contract, price, ru
**Javob:** По контракту №100002 поставляется товар **Аммиачная селитра** (код ТН ВЭД 310230), а его базовая цена составляет **2 720 643 узбекских сумов** за тонну.
```sql
SELECT contract_no, product_name, product_canon_ru, tnved, base_price, currency, unit FROM contracts WHERE contract_no = '100002'
LIMIT 50
```
answerable=True ok=True time=12.3s missing=[]

## g22. Eng ko'p shartnoma ro'yxatdan o'tkazgan sotuvchi qaysi?
tags: contracts, company, top-n, uz
**Javob:** Eng ko'p shartnoma ro'yxatdan o'tkazgan sotuvchi — **VISAQE SERVIS MAS’ULIYATI CHEKLANGAN JAMIYATI** (INN: 996237847). Ushbu kompaniya tomonidan ro'yxatdan o'tkazilgan shartnomalar soni **60** ta.
```sql
SELECT p.inn, p.name, COUNT(c.contract_no) AS registered_contracts_count FROM contracts c JOIN participants p ON c.seller_inn = p.inn GROUP BY p.inn, p.name ORDER BY registered_contracts_count DESC LIMIT 1
```
answerable=True ok=True time=13.2s missing=[]

## g23. DAP yetkazib berish bazisidagi shartnomalar soni qancha?
tags: contracts, uz
**Javob:** DAP yetkazib berish bazisi bo'yicha tuzilgan shartnomalar soni **374** tani tashkil etadi.
```sql
SELECT COUNT(*) AS contracts_count FROM contracts WHERE delivery_basis = 'DAP'
LIMIT 50
```
answerable=True ok=True time=5.4s missing=[]

## g24. Сколько сделок по хлопку-сырцу 1 сорта 1 класса?
tags: deals, grade, product, ru
**Javob:** Общее количество сделок по хлопку-сырцу 1 сорта 1 класса составляет **29 136**. Из них **27 341** исполненных (активных) сделок и **1 795** аннулированных.
```sql
SELECT COUNT(*) AS total_deals, COUNT(CASE WHEN is_cancelled = 0 THEN 1 END) AS active_deals, COUNT(CASE WHEN is_cancelled = 1 THEN 1 END) AS cancelled_deals FROM deals WHERE tnved = '520100' AND sort_no = 1 AND class_no = 1
LIMIT 50
```
answerable=True ok=True time=8.2s missing=[]

## g25. 2023-yilda 2-nav paxta xomashyosi qancha sotilgan?
tags: deals, grade, volume, uz
**Javob:** 2023-yilda 2-navli paxta xomashyosi bo'yicha jami **404 202.126 tonna** (**404 202 126 kg**) hajmda **6 749 ta bitim** tuzilgan.

Bekor qilingan bitimlar hisobga olinmagan.
```sql
SELECT SUM(volume) AS total_volume, unit, COUNT(*) AS deal_count
FROM deals
WHERE tnved = '520100'
  AND sort_no = 2
  AND year = 2023
  AND is_cancelled = 0
GROUP BY unit
LIMIT 50
```
answerable=True ok=True time=10.7s missing=[]

## g26. 2025-yilda oliy nav bug'doy uni qancha sotilgan?
tags: deals, grade, volume, uz
**Javob:** 2025-yilda oliy navli bug'doy unidan jami **20 708.5 tonna** (**20 708 500 kg**) hajmdagi mahsulot **129 266 244 784 so'm** summasida sotilgan. Ushbu davrda 1 189 ta bitim tuzilgan.

Hisob-kitobda bekor qilingan bitimlar inobatga olinmagan.
```sql
SELECT unit, SUM(volume) AS total_volume, SUM(amount_uzs) AS total_amount_uzs, COUNT(*) AS deal_count FROM deals WHERE tnved = '110100' AND (sort_no = 0 OR class_no = 0) AND year = 2025 AND is_cancelled = 0 GROUP BY unit
LIMIT 50
```
answerable=True ok=True time=13.2s missing=[]

## g27. 4-klass bug'doy bo'yicha jami nechta bitim bor?
tags: deals, grade, product, uz
**Javob:** 4-klass bug'doy bo'yicha jami **21 471 ta** bitim mavjud bo'lib, shundan **20 133 ta**si amaldagi bitimlar va **1 338 ta**si bekor qilingan bitimlardir.
```sql
SELECT COUNT(*) AS total_deals, SUM(CASE WHEN is_cancelled = 0 THEN 1 ELSE 0 END) AS valid_deals, SUM(CASE WHEN is_cancelled = 1 THEN 1 ELSE 0 END) AS cancelled_deals FROM deals WHERE tnved = '100199' AND (class_no = 4 OR sort_no = 4)
LIMIT 50
```
answerable=True ok=True time=9.5s missing=[]

## g28. 2024-yilda eksport bitimlari summasi dollarda va so'mda qancha?
tags: deals, export, usd, uz
**Javob:** 2024-yilda eksport bitimlarining umumiy summasi **202 495 621.0 AQSh dollari** va **2 420 672 267 384.0713 so'm**ni (1 229 ta bitim) tashkil etdi.

Hisob-kitobda bekor qilingan bitimlar chiqarib tashlangan.
```sql
SELECT SUM(CASE WHEN is_cancelled = 0 THEN amount END) AS total_amount_usd, SUM(CASE WHEN is_cancelled = 0 THEN amount_uzs END) AS total_amount_uzs, COUNT(CASE WHEN is_cancelled = 0 THEN 1 END) AS deal_count, SUM(CASE WHEN is_cancelled = 1 THEN amount END) AS cancelled_amount_usd, COUNT(CASE WHEN is_cancelled = 1 THEN 1 END) AS cancelled_deal_count FROM deals WHERE year = 2024 AND contract_type = 'Экспортный'
LIMIT 50
```
answerable=True ok=True time=17.8s missing=[]

## g29. Какой курс доллара был 01.03.2025?
tags: usd, ru
**Javob:** Курс доллара США на 01.03.2025 составил **12 515.24 сума**.
```sql
SELECT date, rate FROM usd_rates WHERE date = '2025-03-01'
LIMIT 50
```
answerable=True ok=True time=5.7s missing=[]

## g30. 2022-yilda nechta eksport bitimi tuzilgan?
tags: deals, export, uz
**Javob:** 2022-yilda jami **1 317 ta** eksport bitimi tuzilgan. Shundan **1 237 tasi** faol bitimlar bo'lib, **80 tasi** bekor qilingan.
```sql
SELECT COUNT(*) AS total_deals, COUNT(CASE WHEN is_cancelled = 0 THEN 1 END) AS active_deals, COUNT(CASE WHEN is_cancelled = 1 THEN 1 END) AS cancelled_deals FROM deals WHERE year = 2022 AND contract_type = 'Экспортный'
LIMIT 50
```
answerable=True ok=True time=8.7s missing=[]

## g31. Eng katta eksport bitimi qaysi va summasi dollarda qancha?
tags: deals, export, usd, top-n, uz
**Javob:** Eng katta eksport bitimi **547500-sonli bitim** bo'lib, uning summasi **1 683 554.25 AQSh dollari**ni tashkil etadi. Ushbu bitim 2026-06-24 sanasida "Катод медный М00к" mahsulotining 147.0 tonna hajmi bo'yicha TIZAHI METALL MCHJ (STIR: 992421731) hamda "Bejul Savdo" OK (STIR: 919788432) o'rtasida tuzilgan va holati Bajarilgan.

Hisob-kitobda bekor qilingan bitimlar chiqarib tashlangan.
```sql
SELECT d.deal_no, d.deal_date, d.product, d.volume, d.unit, d.amount, d.currency, d.status, d.seller_inn, p_sell.name AS seller_name, d.buyer_inn, p_buy.name AS buyer_name, d.seller_broker, d.buyer_broker FROM deals d LEFT JOIN participants p_sell ON d.seller_inn = p_sell.inn LEFT JOIN participants p_buy ON d.buyer_inn = p_buy.inn WHERE d.contract_type = 'Экспортный' AND d.is_cancelled = 0 ORDER BY d.amount DESC LIMIT 1
```
answerable=True ok=True time=18.9s missing=[]

## g32. Сколько сделок у брокера BK001 в 2024 году?
tags: brokers, ru
**Javob:** У брокера BK001 в 2024 году было совершено **1 124 сделки**.
```sql
SELECT COUNT(DISTINCT deal_no) AS total_deals FROM deals WHERE year = 2024 AND (seller_broker = 'BK001' OR buyer_broker = 'BK001')
LIMIT 50
```
answerable=True ok=True time=6.7s missing=[]

## g33. Qaysi broker jami eng ko'p bitimda qatnashgan?
tags: brokers, top-n, uz
**Javob:** Jami eng ko'p bitimlarda qatnashgan broker — BK111 kodli **"Gucham Broker" MChJ** bo'lib, u barcha sotuv va xarid jarayonlarida jami **32 422 ta bitim**da ishtirok etgan.
```sql
WITH broker_deals AS (
  SELECT seller_broker AS broker_code, deal_no FROM deals WHERE seller_broker IS NOT NULL
  UNION
  SELECT buyer_broker AS broker_code, deal_no FROM deals WHERE buyer_broker IS NOT NULL
)
SELECT b.code, b.name, COUNT(bd.deal_no) AS total_deals
FROM brokers b
JOIN broker_deals bd ON b.code = bd.broker_code
GROUP BY b.code, b.name
ORDER BY total_deals DESC
LIMIT 1
```
answerable=True ok=True time=9.3s missing=[]

## g34. Какой брокер был брокером продавца в наибольшем числе сделок?
tags: brokers, top-n, ru
**Javob:** Брокером продавца в наибольшем числе сделок был **"Gucham Broker" MChJ** (код **BK111**), выступивший брокером продавца в **21 471** сделках.
```sql
SELECT b.code, b.name, COUNT(d.deal_no) AS deal_count
FROM deals d
JOIN brokers b ON d.seller_broker = b.code
GROUP BY b.code, b.name
ORDER BY deal_count DESC
LIMIT 1
```
answerable=True ok=True time=7.7s missing=[]

## g35. Какой объём торгов пшеницей был в 2021 году?
tags: trap, period, ru
**Javob:** В данных нет ответа на этот вопрос. В базе данных присутствуют сделки только за период с 3 января 2022 года по 30 октября 2026 года. Данные за 2021 год отсутствуют.
```sql
-
```
answerable=False ok=True time=3.0s missing=[]

## g36. Noyabr 2026 da qancha un sotilgan?
tags: trap, period, uz
**Javob:** Ma'lumotlarda bu savolga javob yo'q. Ma'lumotlar bazasida 2026-yil noyabr oyi uchun битимлар мавжуд эмас (ma'lumotlar davri 2022-01-03 dan 2026-10-30 gacha).
```sql
-
```
answerable=False ok=True time=4.4s missing=[]

## g37. Кто директор компании с ИНН 953758401 и какой у неё телефон?
tags: trap, participants, ru
**Javob:** В данных нет ответа на этот вопрос. В базе данных отсутствует информация о директорах компаний и их контактных телефонах (доступны только ИНН, наименование, регион, вид деятельности и роль).
```sql
-
```
answerable=False ok=True time=2.1s missing=[]

## g38. 100437-bitim bo'yicha xaridor kim?
tags: trap, single-deal, uz
**Javob:** Ma'lumotlarda bu savolga javob yo'q.
```sql
SELECT d.deal_no, d.deal_date, d.buyer_inn, p_buyer.name AS buyer_name, d.seller_inn, p_seller.name AS seller_name, d.product_canon_uz, d.volume, d.unit, d.amount, d.currency, d.status FROM deals d LEFT JOIN participants p_buyer ON d.buyer_inn = p_buyer.inn LEFT JOIN participants p_seller ON d.seller_inn = p_seller.inn WHERE d.deal_no = 100437
LIMIT 50
```
answerable=True ok=True time=7.5s missing=[]

## g39. Сколько золота продано на бирже в 2024 году?
tags: trap, product, ru
**Javob:** В данных нет ответа на этот вопрос. Товар 'золото' не торгуется на бирже (отсутствует в перечне товаров базы данных).
```sql
-
```
answerable=False ok=True time=5.0s missing=[]

## g40. 2027-yilda paxta narxi qancha bo'ladi?
tags: trap, forecast, uz
**Javob:** Ma'lumotlarda bu savolga javob yo'q. Ma'lumotlar bazasida faqat 2022-yil 3-yanvardan 2026-yil 30-oktyabrgacha bo'lgan bitimlar mavjud. 2027-yil uchun narxlarni prognoz qilish yoki ma'lumot olish imkoniyati yo'q.
```sql
-
```
answerable=False ok=True time=3.2s missing=[]
