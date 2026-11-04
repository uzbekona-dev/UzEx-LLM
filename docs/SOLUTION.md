# Yechim tavsifi — UZEX birja bitimlari bo'yicha AI-agent

> UZEX AI Hackathon, saralash bosqichi. Telegram-bot: o'zbek yoki rus tilidagi savolga faqat berilgan CSV
> ma'lumotlari asosida javob beradi. Quyida — o'zbekcha (lotin) tavsif, undan keyin xuddi shu tuzilmada ruscha.

---

## 1. Maqsad va yondashuv

Vazifa — 500 000 bitim, 6 616 shartnoma, 14 392 ishtirokchi, 120 broker va kunlik dollar kursi bo'yicha
savollarga **aniq raqam, nom va kod bilan** javob berish, ma'lumotda javob bo'lmasa — shuni ochiq aytish.
Topshiriqdagi eng qattiq talab: o'ylab topilgan raqam, kompaniya yoki tovar = saralashdan chiqish. Shuning uchun
yondashuv bitta prinsipga qurilgan: **LLM hech qachon hisoblamaydi va hech qachon ma'lumot "eslamaydi"**. LLM
faqat savolni SQL so'roviga tarjima qiladi va SQLite qaytargan qatorlarni matnga aylantiradi. Javobdagi har bir
raqam, sana, broker kodi va kompaniya nomi kod bilan natija qatorlarida borligi tekshiriladi; tekshiruvdan
o'tmagan javob qayta yoziladi yoki shablon javob bilan almashtiriladi. Javob ostida foydalanuvchi savol qanday
tushunilgani, nechta qator topilgani va qaysi SQL ishlatilgani ("asos" bloki)ni ko'radi.

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
 LLM reja (app/agent.py, PLAN_SYSTEM) → JSON:
   {language, answerable, reason, interpretation, sql}
        │
        ▼
 SQL guard (app/sql_guard.py)
   faqat SELECT/WITH, bitta so'rov, taqiqlangan kalit so'zlar, DB read-only (mode=ro),
   20 s timeout, LIMIT 50 majburiy          ──► xato bo'lsa LLMga qaytariladi (≤3 urinish)
        │
        ▼
 SQLite natija qatorlari (data/uzex.db)
        │
        ▼
 LLM matn yozadi (ANSWER_SYSTEM): faqat qatorlardagi qiymatlar, savol tilida
        │
        ▼
 Grounding verifier (app/verify.py)
   raqamlar / BK kodlar / sanalar / kompaniya nomlari qatorlarda yoki savolda bo'lishi shart
        │ o'tmadi → LLMga "faqat qatorlardagi qiymatlar" izohi bilan qayta (≤2 urinish)
        │ yana o'tmadi → shablon javob: qatorlar to'g'ridan-to'g'ri (app/agent.py _fallback_answer)
        ▼
 Javob + "asos" bloki (app/format.py): ✅ qator soni · vaqt · 🔎 talqin · ▸ SQL (yig'iladigan)
        │
        ▼
 logs/qa.jsonl — har savol: SQL, talqin, javob, verified, vaqt
```

Vaqt byudjeti: LLM chaqiruvlari uchun jami 50 s (`ANSWER_BUDGET_SEC`); byudjet tugasa yangi LLM chaqiruvi
boshlanmaydi va foydalanuvchiga "qayta yuboring" deyiladi. Har bir LLM so'rovi 40 s, har SQL 20 s bilan
cheklangan — 90 s qattiq limit shunday ta'minlanadi.

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

**4.1. LLM hisoblamaydi — SQLite hisoblaydi.** Summa, o'rtacha, top-N, sanalar farqi — hammasi SQLda.
Matn yozuvchi LLMga ruxsat etilgan yagona arifmetika: kg → tonna (÷1000), va u holda ikkala qiymat
ko'rsatiladi. Foiz, yig'indi, boshqa konvertatsiya — taqiqlangan (`ANSWER_SYSTEM`).

**4.2. Grounding verifier** (`app/verify.py`, har javob uchun kodda):
- Javobdagi har bir raqam natija qatorlaridagi biror katakka teng bo'lishi shart (yoki uning 0–2 kasrgacha
  yaxlitlangani; "ming/mln/mlrd" so'zi bo'lsa — shu masshtabga bo'lingani; "tonna" bo'lsa — ÷1000).
  Savoldagi va SQLdagi literallar (yil, bitim raqami, STIR, TN VED) ham ruxsat etiladi; qatorlar soni ham.
- `BKxxx` broker kodlari va sanalar (ISO yoki `DD.MM.YYYY`) qatorlarda yoki savolda bo'lishi shart.
- Kompaniya nomlari (qo'shtirnoqda yoki MChJ/OOO/AJ... bilan tugaydigan) `company_key` orqali
  qatorlardagi biror matn katagida bo'lishi shart.
- O'tmasa → LLMga qaysi qiymatlar qatorlarda yo'qligi aytilib qayta yozdiriladi (2 urinish); yana o'tmasa →
  LLM matni butunlay tashlanadi, javob sifatida qatorlar o'zi ("Natija (ma'lumotlardan to'g'ridan-to'g'ri)")
  ko'rsatiladi. Ya'ni o'ylab topilgan raqam foydalanuvchiga yetib bormaydi.

**4.3. "Ma'lumot yo'q" siyosati.** Rejalashtiruvchi LLM `answerable=false` qo'yadi, agar savol: davr
tashqarisida (2021, noyabr 2026), sxemada yo'q narsa haqida (rahbar, telefon, sabab, prognoz), ro'yxatda yo'q
tovar (oltin) bo'lsa. Bo'sh natija (mavjud bo'lmagan bitim raqami) ham "bunday yozuv yo'q" deb qaytadi; kod
ham, LLM ham yaqin qiymatni "taxmin" qilmaydi. Entity resolution kompaniya nomini topa olmasa, buni LLMga aytadi
va LLM o'xshash boshqa kompaniyani olmaydi.

**4.4. Taxminlar ochiq aytiladi.** Reja JSONdagi `interpretation` — savol tilida bir jumla: davr, tovar
(TN VED), bekorlar chiqarilgani, formula (hajm = miqdor × lot). U javob ostida "🔎 Talqin" sifatida
ko'rinadi, SQL esa yig'iladigan blokda. Komissiya har javobning asosini ko'ra oladi.

**4.5. SQL xavfsizligi.** Baza `mode=ro` bilan ochiladi; faqat bitta `SELECT`/`WITH`; `insert/update/
delete/drop/attach/pragma/...` taqiqlangan; `LIMIT` bo'lmasa 50 qo'shiladi; 20 s progress-handler timeout.

**4.6. Vaqt va ishonchlilik.** LLM chaqiruvlari uchun 50 s byudjet, har so'rov 40 s, SQL 20 s — 90 s
limitdan oshmaydi. LLM zanjiri: `LLM_MODELS=gemini:...,anthropic:...,openai:...` — har model 2 marta (429/5xx/
timeout), keyin keyingisi; auth xatosi bo'lsa darhol keyingisi. Bitta vendor ishlamasa bot ishlayveradi.
Har chat uchun navbat (asyncio.Lock), har savol alohida DB ulanish — parallel chatlar bir-biriga xalaqit bermaydi.

**4.7. Testlar.**
- `tests/` — 124 ta offline pytest (LLMsiz): normalizatsiya, SQL guard, verifier, entity resolution, bot
  xabarlarini bo'lish, LLM zanjiri (soxta provayderlar bilan), formatlash.
- `tests/golden.jsonl` — 40 ta savol (20 uz / 20 ru; bitim, shartnoma, tovar, broker, eksport, nav/klass,
  top-N, 6 ta tuzoq) har biri uchun qo'lda yozilgan SQL va kutilgan raqamlar/satrlar.
  `tests/test_golden_offline.py` shu SQLlar hozirgi bazada kutilgan qiymatni berishini tekshiradi (regressiya).
  `scripts/golden_check.py` esa jonli agent javobida kutilgan raqamlar borligini tekshiradi.
- `scripts/run_questions.py` — `tests/questions.txt` dagi savollarni jonli agentdan o'tkazib hisobot yozadi.

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
- **LLMga bog'liqlik.** SQL mantiqini LLM yozadi: verifier raqamning *mavjudligini* kafolatlaydi, lekin SQL
  savolga mos kelishini emas — bu golden-test va "Talqin" qatori orqali nazorat qilinadi. 50 ta qatordan
  ko'p natija qisqartiriladi (`truncated`), katta ro'yxatlar to'liq chiqmaydi.
- **Vaqt.** LLM vendorlari sekinlashsa javob 30 s dan oshishi mumkin; byudjet tugasa foydalanuvchi qayta
  so'rashi kerak. Kontekst faqat oxirgi 2 savol ("va 2023-da?" kabi davom savollari uchun).

## 7. Texnologiyalar

Python 3.12; SQLite (standart kutubxona, read-only URI, progress-handler timeout); aiogram 3 (Telegram, long
polling); LLM zanjiri — google-genai (Gemini), anthropic (Claude Messages API), openai (shu jumladan har qanday
OpenAI-mos endpoint: Groq, Ollama, OpenRouter); rapidfuzz (fuzzy entity matching); python-dotenv; pytest
(124 offline test + 40 golden). Tashqi infratuzilma yo'q: bitta jarayon, bitta `.db` fayl (~335 MB).

---
---

# Описание решения — AI-агент по биржевым сделкам UZEX

> Отборочный этап UZEX AI Hackathon. Telegram-бот отвечает на вопросы на узбекском или русском языке строго по
> предоставленным CSV-данным.

## 1. Цель и подход

Задача — отвечать на вопросы по 500 000 сделок, 6 616 контрактам, 14 392 участникам, 120 брокерам и дневному
курсу доллара **точными числами, названиями и кодами**, а если ответа в данных нет — прямо это говорить. Самое
жёсткое требование: выдуманное число, компания или товар = вылет из отбора. Поэтому подход построен на одном
принципе: **LLM никогда не считает и никогда не «вспоминает» данные**. LLM только переводит вопрос в SQL и
превращает строки, возвращённые SQLite, в текст. Каждое число, дата, код брокера и название компании в ответе
проверяются кодом на наличие в строках результата; не прошедший проверку ответ переписывается или заменяется
шаблоном. Под ответом пользователь видит, как понят вопрос, сколько строк найдено и какой SQL выполнен
(блок «основание»).

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
 План от LLM (app/agent.py, PLAN_SYSTEM) → JSON:
   {language, answerable, reason, interpretation, sql}
        │
        ▼
 SQL guard (app/sql_guard.py)
   только SELECT/WITH, один запрос, запрещённые ключевые слова, БД read-only (mode=ro),
   таймаут 20 с, обязательный LIMIT 50       ──► ошибка возвращается LLM (≤3 попытки)
        │
        ▼
 Строки результата SQLite (data/uzex.db)
        │
        ▼
 LLM пишет текст (ANSWER_SYSTEM): только значения из строк, на языке вопроса
        │
        ▼
 Grounding verifier (app/verify.py)
   числа / коды BK / даты / названия компаний обязаны быть в строках или в вопросе
        │ не прошло → LLM переписывает с пометкой «только значения из строк» (≤2 попытки)
        │ снова нет → шаблон: строки как есть (app/agent.py _fallback_answer)
        ▼
 Ответ + блок «основание» (app/format.py): ✅ число строк · время · 🔎 как понят вопрос · ▸ SQL (свёрнут)
        │
        ▼
 logs/qa.jsonl — каждый вопрос: SQL, интерпретация, ответ, verified, время
```

Бюджет времени: 50 с суммарно на вызовы LLM (`ANSWER_BUDGET_SEC`); после исчерпания новый вызов не
начинается, пользователю предлагается повторить вопрос. Каждый запрос к LLM ограничен 40 с, каждый SQL — 20 с;
так обеспечивается жёсткий лимит 90 с.

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

**4.1. LLM не считает — считает SQLite.** Суммы, средние, топ-N, разницы дат — всё в SQL. Единственная
разрешённая арифметика для LLM, пишущей текст: кг → тонны (÷1000), и тогда показываются оба значения.
Проценты, суммирование, другие конвертации — запрещены (`ANSWER_SYSTEM`).

**4.2. Grounding verifier** (`app/verify.py`, кодом для каждого ответа):
- Каждое число в ответе обязано совпадать с какой-то ячейкой строк результата (или быть её округлением до
  0–2 знаков; при словах «тыс/млн/млрд» — делением на этот масштаб; при «тонн» — ÷1000). Также разрешены
  литералы из вопроса и SQL (год, номер сделки, ИНН, ТН ВЭД) и число строк.
- Коды брокеров `BKxxx` и даты (ISO или `DD.MM.YYYY`) обязаны быть в строках или в вопросе.
- Названия компаний (в кавычках или оканчивающиеся на MChJ/OOO/AJ…) через `company_key` обязаны содержаться
  в какой-то текстовой ячейке строк.
- Не прошло → LLM получает список отсутствующих значений и переписывает (2 попытки); снова нет → текст LLM
  отбрасывается целиком, ответом становятся сами строки («Результат (напрямую из данных)»). Выдуманное число до
  пользователя не доходит.

**4.3. Политика «данных нет».** Планирующая LLM ставит `answerable=false`, если вопрос вне периода (2021,
ноябрь 2026), о том, чего нет в схеме (директор, телефон, причины, прогнозы), о товаре вне списка (золото).
Пустой результат (несуществующий номер сделки) тоже возвращается как «такой записи нет»; ни код, ни LLM не
подставляют близкое значение. Если entity resolution не нашла названную компанию, она сообщает это LLM, и та не
берёт похожую.

**4.4. Допущения проговариваются.** `interpretation` в JSON плана — одно предложение на языке вопроса: период,
товар (ТН ВЭД), исключены ли аннулированные, формула (объём = количество × лот). Оно показывается под ответом как
«🔎 Как понят вопрос», SQL — в сворачиваемом блоке. Комиссия видит основание каждого ответа.

**4.5. Безопасность SQL.** База открывается с `mode=ro`; один `SELECT`/`WITH`; `insert/update/delete/drop/
attach/pragma/…` запрещены; без `LIMIT` добавляется 50; таймаут 20 с через progress-handler.

**4.6. Время и надёжность.** 50 с бюджета на LLM, 40 с на запрос, 20 с на SQL — лимит 90 с не превышается.
Цепочка моделей `LLM_MODELS=gemini:…,anthropic:…,openai:…` — каждая модель 2 попытки (429/5xx/таймаут), затем
следующая; при ошибке авторизации — сразу следующая. Отказ одного вендора бот переживает. Очередь на чат
(asyncio.Lock), отдельное соединение с БД на вопрос — параллельные чаты не мешают друг другу.

**4.7. Тесты.**
- `tests/` — 124 офлайн-теста pytest (без LLM): нормализация, SQL guard, verifier, entity resolution,
  разбиение сообщений бота, цепочка LLM (с фиктивными провайдерами), форматирование.
- `tests/golden.jsonl` — 40 вопросов (20 uz / 20 ru; сделки, контракты, товары, брокеры, экспорт, сорт/класс,
  топ-N, 6 ловушек), для каждого — написанный вручную SQL и ожидаемые числа/строки.
  `tests/test_golden_offline.py` проверяет, что эти SQL на текущей базе дают ожидаемые значения (регрессия).
  `scripts/golden_check.py` проверяет, что в ответе живого агента есть ожидаемые числа.
- `scripts/run_questions.py` — прогоняет `tests/questions.txt` через живого агента и пишет отчёт.

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

## 6. Ограничения (честно)

- **Неоднозначность интерпретации.** «Средняя цена» может быть простой (`AVG(unit_price)`) или взвешенной
  (`SUM(amount)/SUM(volume)`) — агент обычно даёт обе, но ожидание комиссии может отличаться. «Продано» по
  умолчанию без аннулированных; «сколько сделок» — все статусы. Допущение всегда в строке «Как понят вопрос».
- **Границы entity resolution.** Короткие или общие названия («Invest», «Savdo») подходят многим компаниям —
  показывается не более 10 кандидатов; при неоднозначности нужен ИНН. «Ташкент» может быть городом или
  областью. При транслитерации русских названий буквы вроде `ц/щ` могут давать одинаковый ключ.
- **Только то, что есть в данных.** Прогнозы, причины, руководитель/телефон компании, другие биржи — ответа
  нет. Период: 2022-01-03 .. 2026-10-30 (курс до 2026-10-31).
- **Зависимость от LLM.** Логику SQL пишет LLM: verifier гарантирует *наличие* числа в данных, но не
  соответствие SQL вопросу — это контролируется golden-тестами и строкой «Как понят вопрос». Результаты длиннее
  50 строк усекаются (`truncated`), большие списки выводятся не полностью.
- **Время.** При замедлении вендоров ответ может превысить 30 с; при исчерпании бюджета пользователю нужно
  повторить вопрос. Контекст — только последние 2 вопроса (для уточнений вида «а в 2023?»).

## 7. Технологии

Python 3.12; SQLite (стандартная библиотека, read-only URI, таймаут через progress-handler); aiogram 3
(Telegram, long polling); цепочка LLM — google-genai (Gemini), anthropic (Claude Messages API), openai (включая
любой OpenAI-совместимый endpoint: Groq, Ollama, OpenRouter); rapidfuzz (fuzzy-сопоставление сущностей);
python-dotenv; pytest (124 офлайн-теста + 40 golden). Внешней инфраструктуры нет: один процесс, один файл `.db`
(~335 МБ).
