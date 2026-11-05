# Yechim tavsifi — UZEX birja bitimlari bo'yicha AI-agent

> UZEX AI Hackathon, saralash bosqichi. Telegram-bot: o'zbek yoki rus tilidagi savolga faqat berilgan CSV
> ma'lumotlari asosida javob beradi. Quyida — o'zbekcha (lotin) tavsif, undan keyin xuddi shu tuzilmada ruscha.

---

## 1. Maqsad va yondashuv

Vazifa — 500 000 bitim, 6 616 shartnoma, 14 392 ishtirokchi, 120 broker va kunlik dollar kursi bo'yicha
savollarga **aniq raqam, nom va kod bilan** javob berish, ma'lumotda javob bo'lmasa — shuni ochiq aytish.
Topshiriqdagi eng qattiq talab: o'ylab topilgan raqam, kompaniya yoki tovar = saralashdan chiqish. Shuning uchun
yondashuv bitta prinsipga qurilgan: **LLM hech qachon hisoblamaydi, ma'lumotni ko'rmaydi va "eslamaydi"**.
Bitta LLM chaqiruvi savolni SQL so'roviga va javob *shabloniga* (`{ustun}` uyachali matn) tarjima qiladi
(ikkinchi, qisqa chaqiruv — SQL-tanqidchi — so'rov mantiqini qoidalar bo'yicha tekshiradi);
SQLite hisoblaydi, shablonni qatorlar bilan kod to'ldiradi. LLM natija qatorlarini umuman ko'rmaydi, shuning
uchun raqam, nom, kod va sana javob matniga faqat bazadagi qatorlardan kiradi — o'ylab topishga joy yo'q.
Savoldagi kompaniya nomlari, STIR va broker kodlari LLMga yuborilishidan oldin `{C1}`, `{INN1}`, `{B1}`
belgilariga almashtiriladi ("maxfiylik tuzilma darajasida"). Ustiga-ustak, tayyor matn grounding verifier
tekshiruvidan o'tadi. Javob ostida foydalanuvchi savol qanday tushunilgani, nechta qator topilgani va qaysi
SQL ishlatilgani ("asos" bloki)ni ko'radi.

## 2. Arxitektura

```
Telegram foydalanuvchi (uz / ru)
        │
        ▼
 aiogram 3 bot (bot.py)  ── har chat uchun navbat, ⏳ progress, 4096 belgiga bo'lish
        │
        ▼
 Entity resolution — kod, LLMsiz (app/entities.py)
   tovar → TN VED kodi (rapidfuzz, UZ/RU sinonimlar), kompaniya → STIR nomzodlari,
   broker → BKxxx, bitim raqami, STIR; "topilmadi" ham aytiladi
        │
        ▼
 Pseudonimizatsiya — kod (app/pseudonym.py)
   kompaniya nomi → {C1}, aniq STIR → {INN1}, broker kodi/nomi → {B1};
   LLMga faqat legenda: "{C1}: kompaniya; 2 ta ishtirokchi mos keldi"
   (ma'lumotda yo'q iboralar o'zgarmaydi — ular bizdagi identifikator emas)
        │
        ▼
 LLM reja — BITTA chaqiruv (app/agent.py, PLAN_SYSTEM + TEMPLATE_RULES) → JSON:
   {language, answerable, reason, interpretation, sql,
    render{headline, line, empty, note}}      ← SQL + javob shabloni, qatorlarsiz
        │
        ▼
 Tokenlarni almashtirish — lokal (Masked.substitute_sql)
   {C1_INNS} → '9120…', '9158…';  {INN1} → '9537…';  {B1} → 'BK045';  {C1_KEY} → ckey(nom)
        │
        ▼
 SQL guard (app/sql_guard.py)
   faqat SELECT/WITH, bitta so'rov, taqiqlangan kalit so'zlar, DB read-only (mode=ro),
   20 s timeout, LIMIT 50 majburiy          ──► xato bo'lsa LLMga qaytariladi (≤3 urinish)
        │
        ▼
 SQLite natija qatorlari (data/uzex.db)      ← LLM bu qatorlarni hech qachon ko'rmaydi
        │
        ▼
 Shablon guard (app/render.py check_template)
   savolda/SQLda yo'q literal raqam yoki noma'lum ustun → rad ──► LLMga izoh bilan qayta (≤3 urinish)
        │
        ▼
 Shablonni to'ldirish — lokal (app/render.py render)
   {ustun} {ustun:t} {ustun:date} {row_count} {C1}; raqam formati, birlik/valyuta/holat tarjimasi,
   ≤10 qator, 0 qator → "empty" matni, "note" → taxminlar; yaroqsiz shablon → umumiy "ustun: qiymat"
        │
        ▼
 Grounding verifier (app/verify.py) — oxirgi himoya chizig'i
   raqamlar / BK kodlar / sanalar / kompaniya nomlari qatorlarda yoki savolda bo'lishi shart
        │ o'tmadi → umumiy "ustun: qiymat" ko'rinishi (render_generic)
        ▼
 Javob + "asos" bloki (app/format.py): ✅ qator soni · vaqt · 🔎 talqin · ▸ SQL (yig'iladigan)
        │
        ▼
 logs/qa.jsonl — har savol: SQL, talqin, javob, verified, used_template, vaqt (faqat shu mashinada)
```

Vaqt byudjeti: LLM chaqiruvlari uchun jami 45 s (`ANSWER_BUDGET_SEC`); byudjet tugasa yangi LLM chaqiruvi
boshlanmaydi va foydalanuvchiga "qayta yuboring" deyiladi. Har bir LLM so'rovi 40 s, har SQL 20 s bilan
cheklangan — 90 s qattiq limit shunday ta'minlanadi. Oddiy holatda savolga **bitta** LLM chaqiruvi yetadi
(avvalgi rejimda ikkita: SQL + matn), qayta urinishlar faqat SQL xatosi yoki shablon guard rad etganda.

## 3. Ma'lumotlarni tayyorlash

`scripts/build_db.py` 9 ta CSV ni bitta SQLite bazaga yuklaydi (`deals`, `contracts`, `participants`,
`brokers`, `usd_rates`, `products`) va indekslaydi. Import paytida:

- `"304 547 938.4"` kabi matnli raqamlar → REAL; `DD.MM.YYYY` → ISO `YYYY-MM-DD`; `year`, `month` ustunlari.
- **Hosila ustunlar** (README qoidalari bo'yicha, bir marta, deterministik):
  `volume = quantity × lot` (o'lchov birligida), `unit_price = amount / volume` (yakuniy narx; `start_price`
  boshlang'ich narx), `currency` shartnomadan, `usd_rate` bitim sanasidagi kurs, `amount_uzs = amount × usd_rate`
  (eksport) yoki `amount` (ichki), `delivered_volume = delivered_lots × lot`, `is_cancelled`
  (holat `Аннулирован(Не оплачен)`), `payment_delay_days` va `delivery_delay_days` (shartnomadagi muddatdan
  oshgan kunlar), `sort_no` / `class_no` (nav va klass matndan ajratilgan).
- **Tovar kanoni:** 40 ta TN VED kodi uchun qo'lda tuzilgan lug'at (`app/dictionaries.py`): kanonik nom RU/UZ
  va sinonimlar. Har bitimga `tnved`, `product_canon_ru/uz`, `product_key` yoziladi.
- Kompaniya va broker nomlari uchun `name_key` — kirill/lotin transliteratsiyasi, kichik harf, qo'shtirnoq va
  huquqiy shaklsiz (`app/normalize.py: company_key`). Xuddi shu funksiya SQLda `ckey()` sifatida mavjud.
- Regionlar: shartnomalardagi ruscha nom → bitimlardagi o'zbekcha-lotin nom (`region_ru` + `region`).

TAHLIL.md dagi tuzoqlar va ularning yechimi:

| Tuzoq | Yechim |
|---|---|
| Tovar nomlari 697 xil yozilgan ("Хлопок-сырец", "ХЛОПОК СЫРЕЦ", "Мочевина (карбамид)") | Filtr faqat `tnved` bo'yicha; LLMga qoida: `product` matn ustuniga filtr qo'ymaslik. Entity resolution "paxta / хлопок / cotton" ni 520100 ga keltiradi |
| Nav va klass turlicha ("I сорт", "1-сорта", "первый сорт") | `sort_no`, `class_no` ustunlari (0 = высший) |
| 27 juft deyarli bir xil nomli kompaniya (`Qojo‘ Invest` OK va `Qojo Invest` MChJ) | Nomzodlar STIR bilan ko'rsatiladi; SQL `GROUP BY inn`, har kompaniya alohida qatorda; STIR berilgan bo'lsa u ustun |
| Uch yozuv tizimi (lotin, o'zbek kirill, rus kirill) | Ikkala tomon lotinga transliteratsiya qilib solishtiriladi (`name_key`, `ckey()`, rapidfuzz) |
| Regionlar ikki tilda | 14 juftlik lug'at, `region` / `region_ru` |
| Matnli raqamlar, `DD.MM.YYYY` sanalar | Importda tipga o'tkaziladi |
| Hajm = Количество × Лот; "Стартовая цена" yakuniy emas | `volume`, `unit_price` hosila ustunlar; LLMga aniq qoida |
| Turli birlik va valyutalarni qo'shib bo'lmaydi | Qoida: `GROUP BY unit`, `amount_uzs` yoki `GROUP BY currency` |
| 33 719 bekor qilingan bitim | `is_cancelled`; "sotildi/hajm" sukut bo'yicha bekorlarsiz, bekorlar soni alohida; "nechta bitim" — barcha holatlar |
| Bitim raqamlarida 4 956 bo'shliq | Aniq moslik; bo'sh natija → "bunday bitim yo'q", yaqin raqam olinmaydi |
| Davr 03.01.2022–30.10.2026 | Promptda davr yozilgan; tashqarisi → `answerable=false` |

## 4. Javoblar qanday tekshiriladi

**4.1. LLM hisoblamaydi va qatorlarni ko'rmaydi — SQLite hisoblaydi, kod to'ldiradi.** Summa, o'rtacha,
top-N, sanalar farqi — hammasi SQLda. LLM javob matnini emas, **shablon** yozadi (`render` maydoni):
`headline` (birinchi/yagona qator uchun 1–2 jumla), `line` (bir necha qator kutilganda har qator uchun bitta
satr), `empty` (0 qator bo'lganda nima deyish), `note` (taxminlar). Uyachalar: `{ustun}`, `{ustun:t}`
(kg → tonna, ÷1000 — yagona ruxsat etilgan arifmetika, uni ham kod bajaradi), `{ustun:int}`, `{ustun:date}`
(DD.MM.YYYY), `{row_count}`, `{C1}`/`{INN1}`/`{B1}`. `app/render.py` shablonni SQLite qatorlari bilan lokal
to'ldiradi: raqamlarni formatlaydi (`1 234 567.89`), identifikator ustunlarini (bitim raqami, STIR, yil, kod)
mingliklarga bo'lmaydi, o'zbek tilida birlik/valyuta/holat so'zlarini tarjima qiladi ("тонна" → "tonna",
"Узбекский сум" → "so'm", "Исполнен" → "Bajarilgan"), ko'pi bilan 10 satr chiqaradi.

**4.2. Shablon guard** (`app/render.py: check_template`, har reja uchun kodda). Shablon rad etiladi, agar unda
savolda yoki SQLda yo'q literal raqam bo'lsa (12 gacha bo'lgan butun sonlar — "top-5", "2 ta" — ruxsat) yoki
SELECTda yo'q ustun ishlatilsa, yoki `headline` ham, `line` ham bo'sh bo'lsa. Rad etilsa rejalashtiruvchi LLMga
muammo ro'yxati va mavjud ustunlar bilan qayta so'rov yuboriladi (jami 3 urinish); shunda ham o'tmasa — umumiy
"ustun: qiymat" ko'rinishi (`render_generic`): chiroyli emas, lekin to'g'ri.

**4.3. Grounding verifier** (`app/verify.py`) — tayyor matn uchun oxirgi himoya chizig'i, shablon tufayli
odatda ishga tushmaydi, lekin saqlab qolingan:
- Javobdagi har bir raqam natija qatorlaridagi biror katakka teng bo'lishi shart (yoki uning 0–2 kasrgacha
  yaxlitlangani; "ming/mln/mlrd" so'zi bo'lsa — shu masshtabga bo'lingani; "tonna" bo'lsa — ÷1000).
  Savoldagi va SQLdagi literallar (yil, bitim raqami, STIR, TN VED) ham ruxsat etiladi; qatorlar soni ham.
- `BKxxx` broker kodlari va sanalar (ISO yoki `DD.MM.YYYY`) qatorlarda yoki savolda bo'lishi shart.
- Kompaniya nomlari (qo'shtirnoqda yoki MChJ/OOO/AJ... bilan tugaydigan) `company_key` orqali
  qatorlardagi biror matn katagida bo'lishi shart.
- O'tmasa → shablon matni tashlanadi, javob sifatida qatorlar o'zi ("Natija (ma'lumotlardan
  to'g'ridan-to'g'ri)") ko'rsatiladi. Ya'ni o'ylab topilgan raqam foydalanuvchiga yetib bormaydi.

**4.4. "Ma'lumot yo'q" siyosati.** Rejalashtiruvchi LLM `answerable=false` qo'yadi, agar savol: davr
tashqarisida (2021, noyabr 2026), sxemada yo'q narsa haqida (rahbar, telefon, sabab, prognoz), ro'yxatda yo'q
tovar (oltin) bo'lsa. Bo'sh natija (mavjud bo'lmagan bitim raqami) shablonning `empty` matni bilan qaytadi
("bunday yozuv yo'q"); kod ham, LLM ham yaqin qiymatni "taxmin" qilmaydi. Entity resolution kompaniya nomini
topa olmasa, legendada "bu ibora hech bir ishtirokchiga mos kelmadi" deyiladi va LLM o'xshash boshqa
kompaniyani olmaydi.

**4.5. Taxminlar ochiq aytiladi.** Reja JSONdagi `interpretation` — savol tilida bir jumla: davr, tovar
(TN VED), bekorlar chiqarilgani, formula (hajm = miqdor × lot). U javob ostida "🔎 Talqin" sifatida
ko'rinadi, SQL esa yig'iladigan blokda; shablondagi `note` javob oxirida. Komissiya har javobning asosini
ko'ra oladi.

**4.6. SQL xavfsizligi.** Baza `mode=ro` bilan ochiladi; faqat bitta `SELECT`/`WITH`; `insert/update/
delete/drop/attach/pragma/...` taqiqlangan; `LIMIT` bo'lmasa 50 qo'shiladi; 20 s progress-handler timeout.

**4.7. Vaqt va ishonchlilik.** LLM chaqiruvlari uchun 45 s byudjet, har so'rov 40 s, SQL 20 s — 90 s
limitdan oshmaydi. LLM zanjiri: `LLM_MODELS=gemini:...,anthropic:...,openai:...` — har model 2 marta (429/5xx/
timeout), keyin keyingisi; auth xatosi bo'lsa darhol keyingisi. Bitta vendor ishlamasa bot ishlayveradi.
Har chat uchun navbat (asyncio.Lock), har savol alohida DB ulanish — parallel chatlar bir-biriga xalaqit bermaydi.

**4.8. Maxfiylik.** Tashqi LLMga mashinadan chiqadigan narsa: jadval sxemasi va qoidalar (`app/schema_prompt.py`),
niqoblangan savol va placeholder legendasi, oldingi 2 savolning talqini, LLM o'zi yozgan SQL va shablon.
Hech qachon chiqmaydigan narsa: xom CSV/baza, SQL natija qatorlari, ishtirokchi nomlari va STIRlari,
foydalanuvchi yozgan broker kodlari, `logs/qa.jsonl`. Kompaniya nomi savolda `{C1}` ga aylanadi, LLM
SQLda `{C1_INNS}` deb yozadi, real STIRlar faqat shu mashinada, so'rov bajarilishidan oldin o'rniga qo'yiladi
(`app/pseudonym.py`). Tovar nomlari niqoblanmaydi — ular TN VED kodlari, shaxsiy ma'lumot emas. Ma'lumotda
mos kelmagan iboralar ham o'zgartirilmaydi: ular bizda saqlanadigan identifikator emas. Kafolatlar
`tests/test_privacy.py` da tekshiriladi. Bu rejim ishlab chiqarish uchun to'liq lokal modelga o'tish yo'lidagi
qadam ham: `OPENAI_BASE_URL` ni Ollama/vLLM ga yo'naltirish kifoya, kod o'zgarmaydi.

**4.9. Testlar.**
- `tests/` — 285 ta offline pytest (LLMsiz): normalizatsiya, SQL guard, verifier, entity resolution,
  pseudonimizatsiya va shablon guard (`test_privacy.py`), reja JSONini tahlil qilish (`test_parse_json.py`),
  agent oqimi soxta LLM bilan (`test_agent.py`), bot xabarlarini bo'lish, LLM zanjiri (soxta provayderlar
  bilan), formatlash, o'zbek kirill (`test_script.py`), analitika (`test_analytics.py`).
- `tests/golden.jsonl` — 40 ta savol (20 uz / 20 ru; bitim, shartnoma, tovar, broker, eksport, nav/klass,
  top-N, 6 ta tuzoq) har biri uchun qo'lda yozilgan SQL va kutilgan raqamlar/satrlar.
  `tests/test_golden_offline.py` shu SQLlar hozirgi bazada kutilgan qiymatni berishini tekshiradi (regressiya).
  `scripts/golden_check.py` esa jonli agent javobida kutilgan raqamlar borligini tekshiradi.
- `scripts/run_questions.py` — `tests/questions.txt` dagi savollarni jonli agentdan o'tkazib hisobot yozadi.

**4.10. O'zbek kirill yozuvi.** Savol o'zbek kirillida yozilsa, javob ham o'zbek kirillida beriladi
(`app/script.py`). Javob odatdagidek o'zbek lotinida tuziladi, keyin LLMsiz, deterministik tarzda kirillga
o'giriladi. Faqat bizning matnimiz o'giriladi (shablon matni, "asos" bloki yorliqlari, xabarlar); ma'lumot
qiymatlari (kompaniya nomlari) o'girishdan keyin qo'yiladi va bazadagidek qoladi; raqamlar, kodlar (`BK045`) va
qisqartmalar (`SQL`, `UZS`) o'zgarmaydi. Tekshiruv: `tests/test_script.py`.

**4.11. Deterministik analitika** (`app/analytics.py`, `ANALYTICS=1`). Biz yozgan qat'iy SQL asosidagi tayyor
hisobotlar; LLM ishtirok etmaydi.
- **"📊 Analitika" tugmasi** javob ostida faqat savolda ishonchli aniqlangan obyekt bo'lsa chiqadi: tovar
  (TN VED, moslik bali ≥ 90), kompaniya (STIR bo'yicha; nomdosh kompaniyalar alohida tugma oladi) yoki broker.
  Ko'pi bilan 3 tugma; rad javobi, bo'sh natija va timeoutda tugma yo'q. Bosilganda hisobot yuboriladi:
  - *Tovar:* yillar bo'yicha bitimlar (bekorlar alohida), bekor qilinmagan hajm (birlik bo'yicha), summa (so'm),
    vaznli o'rtacha narx; top hududlar (sotuvchi ombori), top sotuvchilar, top xaridorlar.
  - *Kompaniya:* hudud / rol / faoliyat; yillar bo'yicha sotuvchi va xaridor sifatidagi bitimlar, bekorlar,
    summa; top tovarlar; brokerlar.
  - *Broker:* yillar bo'yicha bitimlar (broker ikki tomonda bo'lsa ham bitim bir marta sanaladi), summa; top
    tovarlar; top mijozlar.
- **`/statistika`** — butun baza bo'yicha umumiy ko'rinish: yillar bo'yicha, summa bo'yicha top-10 tovar, top
  brokerlar, top hududlar; natija keshlanadi.
- **Til.** Hisobot javob tilida (uz lotin / uz kirill / ru); `/statistika` Telegram interfeysi ruscha bo'lsa ru,
  aks holda uz lotin. Ma'lumot qiymatlari (kompaniya nomlari) bazadagidek qoladi.
- **Nega xavfsiz.** LLM yo'q; obyektni kod topadi (`app/entities.py`); har bir raqam mustaqil SQL bilan
  solishtiruvchi testlar bilan qoplangan (`tests/test_analytics.py`); savolga javob berish konveyeri (prompt,
  agent) o'zgarmagan; hisobot xatosi faqat tugmaga ta'sir qiladi ("Analitika hozircha mavjud emas"), bot
  ishlashda davom etadi. Bayroq `ANALYTICS`: `.env.example` da 0, serverda yoqilgan.

## 5. Sinov natijalari

`tests/report.md` (2026-11-05, model `gemini:gemini-3.5-flash`): 24 savol (12 ru, 12 uz), **24/24 javob
berildi**, 21 tasi ma'lumotli javob (hammasi `verified=True`), 3 tasi to'g'ri rad etildi (kompaniya direktori,
2021-yil, noyabr 2026). Vaqt: min 4.1 s, o'rtacha ≈ 11 s, maksimum 30.7 s (birinchi, "sovuq" so'rov).
Bir xil savol ru/uz da bir xil raqam berdi (paxta 2024: 1 672 494 955 kg / 28 079 bitim; sement mart 2023:
797 626.31 so'm; kurs 15.06.2024: 11 862.46; bekor 2026: 6 266; kechikkan yetkazish: 17 805 — TAHLIL.md dagi
mustaqil profiling bilan mos).

Shu yugurishda ikki mantiqiy xato topildi va promptdagi qoidalar bilan tuzatildi (`app/schema_prompt.py`,
4- va 7-qoidalar):
1. **Broker ikki marta sanaldi.** Uz-savolda top-5 broker `UNION ALL` bilan tuzilgan — bir bitimda ikki
   tomonda ham bir broker bo'lsa, ikki marta sanaladi (6 784 vs to'g'ri 6 692). Qoida: `COUNT(DISTINCT deal_no)`
   yoki `UNION`.
2. **Bekorlar filtri nomuvofiq.** "Un bo'yicha eng ko'p bitim qaysi regionda" savolida bitimlar soni barcha
   holatlar bo'yicha, hajm esa bekorlarsiz hisoblangan — bir javobda ikki xil ta'rif. Qoida: bitta so'rovdagi
   barcha SUM/AVG/COUNT bir xil `is_cancelled` filtriga ega bo'lsin, bekorlar soni alohida ustunda.

`tests/report.md` tuzatishdan oldingi natijani ko'rsatadi (shuning uchun u yerda 16- va 12-savolda eski SQL
turibdi); hisobot `.gitignore` da, chunki har yugurish LLM kvotasini sarflaydi.

**B rejimi (bitta chaqiruv + shablon) bilan qayta yugurish.** 40 savollik golden to'plam (`scripts/golden_check.py`):
**37/40 o'tdi**, vaqt 2.3–19 s, mediana ≈ 6 s (ikki chaqiruvli rejimda ≈ 10 s edi). Uchta xato:
1. "O'rtacha narx" — oddiy o'rtacha (`AVG(unit_price)`) o'rniga vaznli (yoki aksincha) hisoblangan — talqin
   masalasi. Qoida qo'shildi: ikkala o'rtacha ham qaytariladi.
2. Shartnoma raqami bitim raqami sifatida o'qilgan. Qoida qo'shildi: "shartnoma / договор №" →
   `contracts.contract_no`.
3. Bitta savolda shablon guard rad etgani uchun umumiy "ustun: qiymat" ko'rinishi chiqdi — raqamlar to'g'ri,
   lekin matn kutilgan satrga mos kelmadi.
Uchala holatda ham javobdagi raqamlar bazadagi qatorlardan olingan edi; o'ylab topilgan qiymat bo'lmadi.

## 6. Cheklovlar (halol)

- **Talqin noaniqligi.** "O'rtacha narx" oddiy o'rtacha (`AVG(unit_price)`) yoki vaznli
  (`SUM(amount)/SUM(volume)`) bo'lishi mumkin — agent ko'pincha ikkalasini beradi, lekin komissiya kutgan
  ta'rif boshqacha bo'lishi mumkin. "Sotildi" sukut bo'yicha bekorlarsiz; "nechta bitim" — barcha holatlar.
  Taxmin har doim "Talqin" qatorida yoziladi.
- **Entity resolution chegarasi.** Juda qisqa yoki umumiy nomlar ("Invest", "Savdo") ko'p kompaniyaga mos
  keladi — ko'pi bilan 10 nomzod ko'rsatiladi; noyob bo'lmasa STIR so'rash kerak. "Toshkent" shahar yoki
  viloyat bo'lishi mumkin. Ruscha nomni lotinga o'girishda `ц/щ` kabi harflar bir xil kalitga tushishi mumkin.
- **Faqat ma'lumotdagi narsa.** Prognoz, sabab, kompaniya rahbari/telefoni, boshqa birjalar — javob yo'q.
  Davr: 2022-01-03 .. 2026-10-30 (kurs 2026-10-31 gacha).
- **LLMga bog'liqlik.** SQL mantiqini LLM yozadi: shablon guard va verifier raqamning *mavjudligini*
  kafolatlaydi, lekin SQL savolga mos kelishini emas — bu golden-test va "Talqin" qatori orqali nazorat
  qilinadi. 50 ta qatordan ko'p natija qisqartiriladi (`truncated`), shablon ko'pi bilan 10 satr chiqaradi.
- **Shablon ko'rmasdan yoziladi.** LLM qatorlarni ko'rmagani uchun shablon ba'zan natijaga "yopishmaydi"
  (masalan, bir qator kutilgan joyda bir nechta chiqadi) — bunday holda javob to'g'ri, lekin quruqroq;
  guard rad etsa umumiy "ustun: qiymat" ko'rinishi chiqadi.
- **Pseudonimizatsiya chegarasi.** Faqat bazada mos kelgan nomlar niqoblanadi; bazada yo'q nom savol
  matnida qoladi (bu bizda saqlanadigan identifikator emas). Tovar nomlari ataylab niqoblanmaydi.
- **Vaqt.** LLM vendorlari sekinlashsa javob 20 s dan oshishi mumkin; byudjet tugasa foydalanuvchi qayta
  so'rashi kerak. Kontekst faqat oxirgi 2 savol ("va 2023-da?" kabi davom savollari uchun).

## 7. Texnologiyalar

Python 3.12; SQLite (standart kutubxona, read-only URI, progress-handler timeout); aiogram 3 (Telegram, long
polling); LLM zanjiri — google-genai (Gemini), anthropic (Claude Messages API), openai (shu jumladan har qanday
OpenAI-mos endpoint: Groq, Ollama, vLLM, OpenRouter — lokal model uchun `OPENAI_BASE_URL`); rapidfuzz (fuzzy
entity matching); python-dotenv; pytest (285 offline test + 40 golden). Tashqi infratuzilma yo'q: bitta
jarayon, bitta `.db` fayl (~335 MB).

---
---

# Описание решения — AI-агент по биржевым сделкам UZEX

> Отборочный этап UZEX AI Hackathon. Telegram-бот отвечает на вопросы на узбекском или русском языке строго по
> предоставленным CSV-данным.

## 1. Цель и подход

Задача — отвечать на вопросы по 500 000 сделок, 6 616 контрактам, 14 392 участникам, 120 брокерам и дневному
курсу доллара **точными числами, названиями и кодами**, а если ответа в данных нет — прямо это говорить. Самое
жёсткое требование: выдуманное число, компания или товар = вылет из отбора. Поэтому подход построен на одном
принципе: **LLM никогда не считает, не видит данные и не «вспоминает» их**. Один вызов LLM переводит вопрос
в SQL и в *шаблон* ответа (текст со слотами `{колонка}`), второй короткий вызов (SQL-критик) проверяет логику
запроса по правилам; SQLite считает, код заполняет шаблон строками. LLM
вообще не видит строк результата, поэтому числа, названия, коды и даты попадают в текст ответа только из
строк базы — выдумывать нечего. Названия компаний, ИНН и коды брокеров из вопроса заменяются на `{C1}`,
`{INN1}`, `{B1}` до отправки в LLM («конфиденциальность на уровне конструкции»). Поверх этого готовый текст
проходит grounding verifier. Под ответом пользователь видит, как понят вопрос, сколько строк найдено и какой
SQL выполнен (блок «основание»).

## 2. Архитектура

```
Пользователь Telegram (uz / ru)
        │
        ▼
 aiogram 3 бот (bot.py) ── очередь на чат, ⏳ прогресс, разбиение по 4096 символов
        │
        ▼
 Entity resolution — код, без LLM (app/entities.py)
   товар → код ТН ВЭД (rapidfuzz, синонимы UZ/RU), компания → кандидаты с ИНН,
   брокер → BKxxx, номер сделки, ИНН; «не найдено» тоже сообщается
        │
        ▼
 Псевдонимизация — код (app/pseudonym.py)
   название компании → {C1}, явный ИНН → {INN1}, код/имя брокера → {B1};
   LLM получает только легенду: «{C1}: компания; найдено 2 участника»
   (фразы, не найденные в данных, не трогаем — это не наши идентификаторы)
        │
        ▼
 План от LLM — ОДИН вызов (app/agent.py, PLAN_SYSTEM + TEMPLATE_RULES) → JSON:
   {language, answerable, reason, interpretation, sql,
    render{headline, line, empty, note}}      ← SQL + шаблон ответа, без строк
        │
        ▼
 Подстановка токенов — локально (Masked.substitute_sql)
   {C1_INNS} → '9120…', '9158…';  {INN1} → '9537…';  {B1} → 'BK045';  {C1_KEY} → ckey(название)
        │
        ▼
 SQL guard (app/sql_guard.py)
   только SELECT/WITH, один запрос, запрещённые ключевые слова, БД read-only (mode=ro),
   таймаут 20 с, обязательный LIMIT 50       ──► ошибка возвращается LLM (≤3 попытки)
        │
        ▼
 Строки результата SQLite (data/uzex.db)     ← LLM эти строки никогда не видит
        │
        ▼
 Guard шаблона (app/render.py check_template)
   литеральное число, которого нет в вопросе/SQL, или неизвестная колонка → отказ ──► LLM с пояснением (≤3 попытки)
        │
        ▼
 Заполнение шаблона — локально (app/render.py render)
   {колонка} {колонка:t} {колонка:date} {row_count} {C1}; формат чисел, перевод единиц/валют/статусов,
   ≤10 строк, 0 строк → текст «empty», «note» → допущения; негодный шаблон → общий вид «колонка: значение»
        │
        ▼
 Grounding verifier (app/verify.py) — последний рубеж
   числа / коды BK / даты / названия компаний обязаны быть в строках или в вопросе
        │ не прошло → общий вид «колонка: значение» (render_generic)
        ▼
 Ответ + блок «основание» (app/format.py): ✅ число строк · время · 🔎 как понят вопрос · ▸ SQL (свёрнут)
        │
        ▼
 logs/qa.jsonl — каждый вопрос: SQL, интерпретация, ответ, verified, used_template, время (только на этой машине)
```

Бюджет времени: 45 с суммарно на вызовы LLM (`ANSWER_BUDGET_SEC`); после исчерпания новый вызов не
начинается, пользователю предлагается повторить вопрос. Каждый запрос к LLM ограничен 40 с, каждый SQL — 20 с;
так обеспечивается жёсткий лимит 90 с. В штатном случае на вопрос уходит **один** вызов LLM (раньше два: SQL
и текст); повторные вызовы — только при ошибке SQL или отказе guard шаблона.

## 3. Подготовка данных

`scripts/build_db.py` загружает 9 CSV в одну базу SQLite (`deals`, `contracts`, `participants`, `brokers`,
`usd_rates`, `products`) и строит индексы. При импорте:

- Текстовые числа вида `"304 547 938.4"` → REAL; `DD.MM.YYYY` → ISO `YYYY-MM-DD`; колонки `year`, `month`.
- **Производные колонки** (по правилам README, один раз, детерминированно):
  `volume = quantity × lot` (в единице измерения), `unit_price = amount / volume` (итоговая цена; `start_price`
  — стартовая), `currency` из контракта, `usd_rate` на дату сделки, `amount_uzs = amount × usd_rate` (экспорт)
  или `amount` (внутренние), `delivered_volume = delivered_lots × lot`, `is_cancelled` (состояние
  `Аннулирован(Не оплачен)`), `payment_delay_days` и `delivery_delay_days` (превышение сроков из контракта),
  `sort_no` / `class_no` (сорт и класс, разобранные из текста).
- **Канон товара:** словарь на 40 кодов ТН ВЭД (`app/dictionaries.py`): каноническое название RU/UZ и
  синонимы. В каждую сделку записываются `tnved`, `product_canon_ru/uz`, `product_key`.
- Для компаний и брокеров — `name_key`: транслитерация кириллица→латиница, нижний регистр, без кавычек и
  правовой формы (`app/normalize.py: company_key`). Та же функция доступна в SQL как `ckey()`.
- Регионы: русское название из контрактов → узбекско-латинское из сделок (`region_ru` + `region`).

Ловушки из TAHLIL.md и их обработка:

| Ловушка | Решение |
|---|---|
| 697 вариантов написания товара («Хлопок-сырец», «ХЛОПОК СЫРЕЦ», «Мочевина (карбамид)») | Фильтр только по `tnved`; правило LLM: не фильтровать по текстовой колонке `product`. Entity resolution сводит «paxta / хлопок / cotton» к 520100 |
| Сорт и класс пишутся по-разному («I сорт», «1-сорта», «первый сорт») | Колонки `sort_no`, `class_no` (0 = высший) |
| 27 пар почти одинаковых компаний (`Qojo‘ Invest` OK и `Qojo Invest` MChJ) | Кандидаты показываются с ИНН; SQL `GROUP BY inn`, каждая компания отдельной строкой; при наличии ИНН он приоритетен |
| Три системы письма (латиница, узбекская и русская кириллица) | Обе стороны транслитерируются в латиницу (`name_key`, `ckey()`, rapidfuzz) |
| Регионы на двух языках | Словарь из 14 пар, `region` / `region_ru` |
| Текстовые числа, даты `DD.MM.YYYY` | Приведение типов при импорте |
| Объём = Количество × Лот; «Стартовая цена» не итоговая | Производные `volume`, `unit_price`; явное правило для LLM |
| Нельзя складывать разные единицы и валюты | Правило: `GROUP BY unit`, `amount_uzs` или `GROUP BY currency` |
| 33 719 аннулированных сделок | `is_cancelled`; «продано/объём» по умолчанию без аннулированных, их число отдельно; «сколько сделок» — все статусы |
| 4 956 пропусков в номерах сделок | Точное совпадение; пустой результат → «такой сделки нет», соседний номер не подставляется |
| Период 03.01.2022–30.10.2026 | Период в промпте; вне его → `answerable=false` |

## 4. Как проверяются ответы

**4.1. LLM не считает и не видит строк — считает SQLite, заполняет код.** Суммы, средние, топ-N, разницы
дат — всё в SQL. LLM пишет не текст ответа, а **шаблон** (поле `render`): `headline` (1–2 предложения для
первой/единственной строки), `line` (по строке на каждую запись, когда ожидается несколько), `empty` (что
сказать при 0 строк), `note` (допущения). Слоты: `{колонка}`, `{колонка:t}` (кг → тонны, ÷1000 —
единственная разрешённая арифметика, и выполняет её код), `{колонка:int}`, `{колонка:date}` (DD.MM.YYYY),
`{row_count}`, `{C1}`/`{INN1}`/`{B1}`. `app/render.py` заполняет шаблон строками SQLite локально: форматирует
числа (`1 234 567.89`), не группирует по тысячам колонки-идентификаторы (номер сделки, ИНН, год, код),
для узбекского переводит единицы/валюты/статусы («тонна» → «tonna», «Узбекский сум» → «so'm», «Исполнен» →
«Bajarilgan»), выводит не более 10 строк.

**4.2. Guard шаблона** (`app/render.py: check_template`, кодом для каждого плана). Шаблон отклоняется, если в
нём есть литеральное число, которого нет в вопросе или SQL (целые до 12 — «топ-5», «2 компании» — разрешены),
используется колонка, которой нет в SELECT, или пусты и `headline`, и `line`. При отказе планирующей LLM
отправляется повторный запрос со списком проблем и доступными колонками (всего 3 попытки); если и это не
помогло — общий вид «колонка: значение» (`render_generic`): некрасиво, но верно.

**4.3. Grounding verifier** (`app/verify.py`) — последний рубеж для готового текста; благодаря шаблону обычно
не срабатывает, но сохранён:
- Каждое число в ответе обязано совпадать с какой-то ячейкой строк результата (или быть её округлением до
  0–2 знаков; при словах «тыс/млн/млрд» — делением на этот масштаб; при «тонн» — ÷1000). Также разрешены
  литералы из вопроса и SQL (год, номер сделки, ИНН, ТН ВЭД) и число строк.
- Коды брокеров `BKxxx` и даты (ISO или `DD.MM.YYYY`) обязаны быть в строках или в вопросе.
- Названия компаний (в кавычках или оканчивающиеся на MChJ/OOO/AJ…) через `company_key` обязаны содержаться
  в какой-то текстовой ячейке строк.
- Не прошло → текст шаблона отбрасывается, ответом становятся сами строки («Результат (напрямую из данных)»).
  Выдуманное число до пользователя не доходит.

**4.4. Политика «данных нет».** Планирующая LLM ставит `answerable=false`, если вопрос вне периода (2021,
ноябрь 2026), о том, чего нет в схеме (директор, телефон, причины, прогнозы), о товаре вне списка (золото).
Пустой результат (несуществующий номер сделки) возвращается текстом `empty` из шаблона («такой записи нет»);
ни код, ни LLM не подставляют близкое значение. Если entity resolution не нашла названную компанию, легенда
говорит «эта фраза не совпала ни с одним участником», и LLM не берёт похожую.

**4.5. Допущения проговариваются.** `interpretation` в JSON плана — одно предложение на языке вопроса: период,
товар (ТН ВЭД), исключены ли аннулированные, формула (объём = количество × лот). Оно показывается под ответом как
«🔎 Как понят вопрос», SQL — в сворачиваемом блоке; `note` из шаблона — в конце ответа. Комиссия видит
основание каждого ответа.

**4.6. Безопасность SQL.** База открывается с `mode=ro`; один `SELECT`/`WITH`; `insert/update/delete/drop/
attach/pragma/…` запрещены; без `LIMIT` добавляется 50; таймаут 20 с через progress-handler.

**4.7. Время и надёжность.** 45 с бюджета на LLM, 40 с на запрос, 20 с на SQL — лимит 90 с не превышается.
Цепочка моделей `LLM_MODELS=gemini:…,anthropic:…,openai:…` — каждая модель 2 попытки (429/5xx/таймаут), затем
следующая; при ошибке авторизации — сразу следующая. Отказ одного вендора бот переживает. Очередь на чат
(asyncio.Lock), отдельное соединение с БД на вопрос — параллельные чаты не мешают друг другу.

**4.8. Конфиденциальность данных.** Что уходит с машины во внешнюю LLM: схема таблиц и правила
(`app/schema_prompt.py`), замаскированный вопрос с легендой плейсхолдеров, интерпретации двух предыдущих
вопросов, написанные самой LLM SQL и шаблон. Что не уходит никогда: исходные CSV/база, строки результата SQL,
названия и ИНН участников, коды брокеров, названные пользователем, `logs/qa.jsonl`. Название компании в
вопросе превращается в `{C1}`, LLM пишет в SQL `{C1_INNS}`, а реальные ИНН подставляются только на этой машине
перед выполнением запроса (`app/pseudonym.py`). Названия товаров не маскируются — это коды ТН ВЭД, не
персональные данные. Фразы, не найденные в данных, тоже не трогаются: это не идентификаторы, которые мы
храним. Гарантии проверяются в `tests/test_privacy.py`. Этот режим — ещё и шаг к полностью локальной модели
для продакшена: достаточно направить `OPENAI_BASE_URL` на Ollama/vLLM, код не меняется.

**4.9. Тесты.**
- `tests/` — 285 офлайн-тестов pytest (без LLM): нормализация, SQL guard, verifier, entity resolution,
  псевдонимизация и guard шаблона (`test_privacy.py`), разбор JSON плана (`test_parse_json.py`), поток агента
  с фиктивной LLM (`test_agent.py`), разбиение сообщений бота, цепочка LLM (с фиктивными провайдерами),
  форматирование, узбекская кириллица (`test_script.py`), аналитика (`test_analytics.py`).
- `tests/golden.jsonl` — 40 вопросов (20 uz / 20 ru; сделки, контракты, товары, брокеры, экспорт, сорт/класс,
  топ-N, 6 ловушек), для каждого — написанный вручную SQL и ожидаемые числа/строки.
  `tests/test_golden_offline.py` проверяет, что эти SQL на текущей базе дают ожидаемые значения (регрессия).
  `scripts/golden_check.py` проверяет, что в ответе живого агента есть ожидаемые числа.
- `scripts/run_questions.py` — прогоняет `tests/questions.txt` через живого агента и пишет отчёт.

**4.10. Узбекская кириллица.** Если вопрос написан на узбекской кириллице, ответ тоже даётся на узбекской
кириллице (`app/script.py`). Ответ, как обычно, строится на узбекской латинице, затем детерминированно, без
LLM, переводится в кириллицу. Конвертируется только наш текст (текст шаблона, подписи блока «основание»,
сообщения); значения из данных (названия компаний) подставляются после конвертации и остаются как в базе;
числа, коды (`BK045`) и аббревиатуры (`SQL`, `UZS`) не меняются. Проверка: `tests/test_script.py`.

**4.11. Детерминированная аналитика** (`app/analytics.py`, `ANALYTICS=1`). Готовые отчёты по фиксированному
SQL, написанному нами; LLM не участвует.
- **Кнопка «📊 Analitika»** под ответом появляется, только если в вопросе есть уверенно распознанная сущность:
  товар (ТН ВЭД, оценка совпадения ≥ 90), компания (по ИНН; омонимы получают отдельные кнопки) или брокер.
  Не более 3 кнопок; при отказе, пустом результате и таймауте кнопки нет. По нажатию приходит отчёт:
  - *Товар:* сделки по годам (аннулированные отдельно), объём без аннулированных (по единицам), сумма (сум),
    средневзвешенная цена; топ регионов (склад продавца), топ продавцов, топ покупателей.
  - *Компания:* регион / роль / деятельность; сделки по годам как продавец и как покупатель, аннулированные,
    сумма; топ товаров; брокеры.
  - *Брокер:* сделки по годам (сделка считается один раз, даже если брокер на обеих сторонах), сумма; топ
    товаров; топ клиентов.
- **`/statistika`** — обзор всей базы: по годам, топ-10 товаров по сумме, топ брокеров, топ регионов;
  результат кэшируется.
- **Язык.** Отчёт на языке ответа (uz латиница / uz кириллица / ru); `/statistika` — ru, если интерфейс
  Telegram русский, иначе uz латиница. Значения из данных (названия компаний) остаются как в базе.
- **Почему это безопасно.** LLM нет; сущность находит код (`app/entities.py`); каждое число покрыто тестами,
  сверяющими отчёт с независимым SQL (`tests/test_analytics.py`); конвейер ответов на вопросы (промпт, агент)
  не менялся; ошибка отчёта затрагивает только кнопку («Analitika hozircha mavjud emas»), бот продолжает
  работать. Флаг `ANALYTICS`: 0 в `.env.example`, на сервере включён.

## 5. Результаты тестирования

`tests/report.md` (2026-11-05, модель `gemini:gemini-3.5-flash`): 24 вопроса (12 ru, 12 uz), **24/24
отвечены**, 21 — содержательно (все `verified=True`), 3 — корректно отклонены (директор компании, 2021 год,
ноябрь 2026). Время: мин 4.1 с, среднее ≈ 11 с, максимум 30.7 с (первый, «холодный» запрос). Одинаковые вопросы
на ru/uz дали одинаковые числа (хлопок 2024: 1 672 494 955 кг / 28 079 сделок; цемент март 2023: 797 626.31
сум; курс 15.06.2024: 11 862.46; аннулировано 2026: 6 266; просроченные поставки: 17 805 — совпадает с
независимым профилированием в TAHLIL.md).

В этом прогоне найдены две логические ошибки, исправленные правилами промпта (`app/schema_prompt.py`,
правила 4 и 7):
1. **Брокер считался дважды.** В uz-вопросе топ-5 брокеров строился через `UNION ALL` — если один брокер с
   обеих сторон сделки, она считалась дважды (6 784 вместо верных 6 692). Правило: `COUNT(DISTINCT deal_no)`
   или `UNION`.
2. **Несогласованный фильтр аннулированных.** В вопросе «в каком регионе больше всего сделок по муке» число
   сделок считалось по всем статусам, а объём — без аннулированных: два определения в одном ответе. Правило: все
   SUM/AVG/COUNT в одном запросе используют один фильтр `is_cancelled`, число аннулированных — отдельной колонкой.

`tests/report.md` показывает результат до исправления (поэтому в вопросах 16 и 12 там старый SQL); отчёт в
`.gitignore`, так как каждый прогон расходует квоту LLM.

**Повторный прогон в режиме B (один вызов + шаблон).** Golden-набор из 40 вопросов (`scripts/golden_check.py`):
**37/40 пройдено**, время 2.3–19 с, медиана ≈ 6 с (в режиме с двумя вызовами было ≈ 10 с). Три промаха:
1. «Средняя цена» — посчитана простая (`AVG(unit_price)`) вместо взвешенной (или наоборот) — вопрос
   интерпретации. Добавлено правило: возвращать обе средние.
2. Номер контракта прочитан как номер сделки. Добавлено правило: «shartnoma / договор №» →
   `contracts.contract_no`.
3. В одном вопросе guard шаблона отклонил шаблон, и ответ вышел в общем виде «колонка: значение» — числа верны,
   но строка не совпала с ожидаемым текстом.
Во всех трёх случаях числа в ответе были взяты из строк базы; выдуманных значений не было.

## 6. Ограничения (честно)

- **Неоднозначность интерпретации.** «Средняя цена» может быть простой (`AVG(unit_price)`) или взвешенной
  (`SUM(amount)/SUM(volume)`) — агент обычно даёт обе, но ожидание комиссии может отличаться. «Продано» по
  умолчанию без аннулированных; «сколько сделок» — все статусы. Допущение всегда в строке «Как понят вопрос».
- **Границы entity resolution.** Короткие или общие названия («Invest», «Savdo») подходят многим компаниям —
  показывается не более 10 кандидатов; при неоднозначности нужен ИНН. «Ташкент» может быть городом или
  областью. При транслитерации русских названий буквы вроде `ц/щ` могут давать одинаковый ключ.
- **Только то, что есть в данных.** Прогнозы, причины, руководитель/телефон компании, другие биржи — ответа
  нет. Период: 2022-01-03 .. 2026-10-30 (курс до 2026-10-31).
- **Зависимость от LLM.** Логику SQL пишет LLM: guard шаблона и verifier гарантируют *наличие* числа в
  данных, но не соответствие SQL вопросу — это контролируется golden-тестами и строкой «Как понят вопрос».
  Результаты длиннее 50 строк усекаются (`truncated`), шаблон выводит не более 10 строк.
- **Шаблон пишется вслепую.** LLM не видит строк, поэтому шаблон иногда «не ложится» на результат (например,
  ожидалась одна строка, а вернулось несколько) — ответ тогда верный, но суше; при отказе guard выводится общий
  вид «колонка: значение».
- **Границы псевдонимизации.** Маскируются только названия, найденные в базе; не найденное название остаётся в
  тексте вопроса (это не хранимый нами идентификатор). Названия товаров намеренно не маскируются.
- **Время.** При замедлении вендоров ответ может превысить 20 с; при исчерпании бюджета пользователю нужно
  повторить вопрос. Контекст — только последние 2 вопроса (для уточнений вида «а в 2023?»).

## 7. Технологии

Python 3.12; SQLite (стандартная библиотека, read-only URI, таймаут через progress-handler); aiogram 3
(Telegram, long polling); цепочка LLM — google-genai (Gemini), anthropic (Claude Messages API), openai (включая
любой OpenAI-совместимый endpoint: Groq, Ollama, vLLM, OpenRouter — `OPENAI_BASE_URL` для локальной модели);
rapidfuzz (fuzzy-сопоставление сущностей); python-dotenv; pytest (285 офлайн-тестов + 40 golden). Внешней
инфраструктуры нет: один процесс, один файл `.db` (~335 МБ).
