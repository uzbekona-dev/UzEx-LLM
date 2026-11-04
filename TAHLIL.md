# UZEX AI Hackathon — saralash: topshiriq va ma'lumotlar tahlili

Manba: hackathon.uzex.uz/saralash, `uzex_spot_data.zip` (README + 9 ta CSV). Tahlil sanasi: 2026-11-04.

## 1. Aniq talablar (rasmiy sahifadan)

| # | Talab | Manba matni / izoh |
|---|---|---|
| T1 | Birja bitimlari bo'yicha savollarga javob beradigan AI-agent | "Topshiriq" bo'limi |
| T2 | Savollar **RU yoki UZ** tilida keladi, javob **savol tilida** bo'lishi kerak | FAQ |
| T3 | Telegram-bot **yoki** veb-servis | FAQ: veb ham bo'ladi |
| T4 | **O'rnatishsiz va ro'yxatdan o'tishsiz** ishlashi kerak | "MUHIM" bloki |
| T5 | Javob aniq bo'ladi: raqam, nom, kod | "Aniq va ma'lumotga asoslangan" |
| T6 | Ma'lumotda javob yo'q bo'lsa, agent buni **ochiq aytadi** | "Javob yo'qmi — shuni ayting" |
| T7 | ❗ **O'ylab topilgan raqam, kompaniya yoki tovar = saralashdan chiqish** | "DIQQAT" bloki |
| T8 | Har bir javobga **≤ 90 soniya** | "Qanday tekshiramiz" |
| T9 | Prototip **doim ishlab turishi** kerak (5-noyabr 18:00 dan tekshiruv paytigacha) | Qoida 03 |
| T10 | Kod va prototipni boshqa jamoalarga bermaslik (o'xshashlik tekshiriladi) | Qoida 02 |
| T11 | Topshirish: Google Forma, 5-noyabr 18:00 gacha; qayta yuborish mumkin | "Natijani topshirish", FAQ |

### Baholash (100 ball) va undan chiqadigan talablar
| Mezon | Ball | Bizga nima kerak |
|---|---|---|
| To'g'ri javoblar | 60 (10 × 6) | Hisoblashlar aniq bo'lsin, ayniqsa tovar va kompaniya nomlarini to'g'ri moslashtirish |
| Prototip sifati | 20 | **Javob nimaga asoslangani ko'rinadi** (SQL / qatorlar / bitim raqamlari); RU+UZ; qulay; tez |
| Yechim tavsifi | 20 | Texnologiyalar **va javoblar qanday tekshirilgani** (validatsiya, testlar) aniq yozilgan bo'lsin |

> Xulosa: "yechim tavsifi" ham 20 ball beradi. Shuning uchun tekshiruv mexanizmi (anti-gallyutsinatsiya) **tavsifda alohida ko'rsatilishi** kerak.

### Hali noaniq qolgan narsalar (taxminlar)
- Savollar qay darajada murakkab? Bitta bitimni qidirish, agregatsiya (summa, top-N), bir nechta jadvalni birlashtirish — **hammasiga tayyor bo'lamiz**.
- Komissiya qanday qabul qilib olinadigan javobni kutadi: aniq raqammi yoki yaxlitlangan raqammi? → **Aniq raqam va birlik** beramiz, yonida yaxlitlangan shakli ham bo'ladi.
- Agar savol noaniq bo'lsa (masalan, bir xil nomli ikki kompaniya), komissiya qayta so'rashni yoqtiradimi? → Variantlarni STIR bilan ko'rsatamiz va **ikkalasi uchun ham** javob beramiz.

## 2. Ma'lumotlar: tuzilma

| Fayl | Qatorlar | Kalit | Bog'lanish |
|---|---|---|---|
| deals_2022..2026 | 500 000 (84 299 / 93 985 / 106 647 / 115 763 / 99 306) | Номер сделки (100001–604956) | → contracts, participants (2×), brokers (2×) |
| contracts | 6 616 | Номер контракта | → participants (sotuvchi) |
| participants | 14 392 (392 sotuvchi, 14 000 xaridor) | ИНН (9 raqam) | — |
| brokers | 120 (BK001–BK120) | Код брокера | — |
| usd_rates | 1 765 (01.01.2022–31.10.2026, har kun) | Дата | eksport bitimlari |

Davr: **03.01.2022 – 30.10.2026**. Savdo faqat ish kunlari (dushanba–juma), soat 10:00–16:59 oralig'ida bo'lgan.

## 3. Ma'lumot sifati — tekshirildi ✅ (yaxlitlik toza)

- Takrorlangan bitim raqami yo'q. Bitimlar ketma-ketligida **4 956 ta raqam yo'q** (README buni aytadi: "ba'zi raqamlar o'tkazib yuborilgan"). → "Bitim №X" so'ralsa va u yo'q bo'lsa, javob: **"bunday bitim yo'q"**.
- Har bir bitimning shartnomasi, sotuvchisi, xaridori va brokeri mavjud (0 ta yetim yozuv).
- Bitimdagi savdo turi, shartnoma turi va shakli, lot, birlik va sotuvchi shartnoma kartochkasi bilan **100% mos**.
- Bitimlar shartnomaning amal qilish muddati ichida tuzilgan.
- Valyuta: barcha Внутренний bitimlar so'mda (493 410), barcha Экспортный bitimlar dollarda (6 590). Har bir eksport sanasi uchun kurs bor.
- Bitim regioni = sotuvchi regioni = shartnoma regioni (100%).
- Holat va sanalar mantiqan izchil:
  - Исполнен → to'langan, yetkazilgan, Поставлено = Количество
  - Исполнен(Частично) → Поставлено < Количество
  - Оплачен → to'langan, yetkazilmagan
  - Аннулирован / Ждёт оплату / Заключен / Новый / Не подписан → sanalar bo'sh
- Narx mantig'i:
  - Английский аукцион: yakuniy narx ≥ boshlang'ich
  - Обратный va Двусторонний аукcion: yakuniy narx ≤ boshlang'ich
- **Yetkazish muddati 17 805 ta bitimda buzilgan** (yetkazish sanasi − to'lov sanasi > Срок поставки). Bu "kechikkan yetkazishlar" haqidagi savol uchun potentsial manba.
- 133 ta shartnoma va 3 ta ishtirokchida bitim yo'q. Barcha 120 broker ishlatilgan.
- Eng katta bitim: №247890, 30,19 mlrd so'm.

## 4. ⚠️ Tuzoqlar — bular to'g'ri javob uchun hal qiluvchi

### 4.1 Tovar nomlari tartibsiz yozilgan (eng xavfli joy)
- `Наименование продукта` ustunida 230 xil nom bor, katta-kichik harf farqi olib tashlanganda ham 188 ta qoladi.
- Bitimlardagi `Наименование товара` 697 xil satrdan iborat.
- Bir xil tovar turlicha yozilgan:
  - "Хлопок-сырец (спот)", "ХЛОПОК СЫРЕЦ (СПОТ)", "Хлопок сырец (спот)"
  - "Карбамид", "КАРБАМИД", "Мочевина (карбамид)"
  - "Масло хлопковое", "Хлопковое масло"
  - "Медный катод", "Катод медный М0к"
- Sort va klass ham turlicha yozilgan: "I сорт", "1-сорта", "первый сорт", "1 сорт"; "I класс", "1-класс", "1 класс".
- **Barqaror kalit: `Код ТН ВЭД`.** Jami 40 ta kod bor, ular tovar turini aniq ajratadi:
  - 520100 → paxta xomashyosi: **136 208 bitim**, eng ko'p
  - 252329 → sement
  - 100199 → bug'doy
  - 271019 → dizel/mazut
  - 110100 → un
  - va boshqalar
- → Yechim: **40 ta TN VED bo'yicha kanonik tovar lug'ati (RU + UZ + sinonimlar)** tuziladi. "Paxta", "хлопок", "cotton" so'rovi kod orqali barcha variantlarga moslanadi. Sort va klass alohida normallashtiriladi.

### 4.2 Deyarli bir xil nomli kompaniyalar (27 juft)
- Nomlar faqat apostrof `‘` va huquqiy shakl bilan farq qiladi, lekin bular **turli kompaniyalar, STIRlari turlicha**. Misollar:
  - "Qojo‘ Invest" OK (912004930) va "Qojo Invest" MChJ (915861525)
  - FO‘YO SAVDO MCHJ va FOYO SAVDO MCHJ
- → Agent kompaniyani **noaniq moslashtirsa, boshqa kompaniya uchun javob berib yuboradi** (T7 bo'yicha xavf). Yechim: noaniq moslik bo'lsa, barcha nomzodlarni STIR bilan ko'rsatish. STIR bilan qidirish ustuvor.

### 4.3 Uch xil yozuv tizimi
- Kompaniya nomlari: 12 325 ta lotin, 1 150 ta o'zbek kirill (Ҳ, Ў, Қ, Ғ), 917 ta rus kirill.
- Foydalanuvchi "Harayum Kimyo" deb yozishi mumkin, bazada esa "ҲАРАЙЎМ КИМЁ" turibdi.
- → Ikkala tomonni ham **lotinga transliteratsiya qilib** solishtirish kerak (fuzzy match).

### 4.4 Regionlar ikki tilda
- Bitim va ishtirokchilarda: "Namangan viloyati".
- Shartnomalarda: "Наманганская область".
- Moslik 1:1 (14 ta juft), lug'atga qo'shiladi. "Toshkent shahri" va "Toshkent viloyati" farq qiladi: "Ташкент" so'ralsa, aniqlashtirish kerak.

### 4.5 Raqam va sana formatlari
- `Сумма сделки` va `Стартовая цена` matn ko'rinishida: "304 547 938.4".
- Sanalar `DD.MM.YYYY` formatida. Import paytida turlarga o'tkaziladi.

### 4.6 Hisoblash qoidalari (README)
- Hajm = Количество × Лот (o'lchov birligida). Lot 1, 12, 100 yoki 1000 bo'lishi mumkin. Masalan, benzin 1000 litrlik lotlarda.
- Birlik narxi = Сумма ÷ (Количество × Лот). **"Стартовая цена" yakuniy narx emas.**
- Eksport bitimining so'mdagi qiymati = summa (USD) × bitim sanasidagi kurs.
- Turli birliklarni (tonna, kg, litr) **qo'shib bo'lmaydi**. Agent hajmni birlik bo'yicha guruhlab berishi kerak.
- Turli valyutalarni qo'shib bo'lmaydi. Umumiy summa so'ralsa, aniq qoida bilan so'mga o'tkaziladi va bu javobda aytiladi.

### 4.7 "Savdo hajmi" ta'rifi
- Аннулирован(Не оплачен) holatidagi 33 719 ta bitim **amalga oshmagan**.
- "Qancha sotildi" savoliga javob: barcha bitimlar va bekor qilinganlardan tashqari bitimlar, ikkalasi alohida. Javobda qaysi ta'rif ishlatilgani aytiladi.
- Исполнен(Частично): yetkazilgan miqdor = Поставлено × Лот.

### 4.8 Ma'lumot chegarasi
- Oxirgi bitim sanasi 30.10.2026, kurs esa 31.10.2026 gacha bor.
- Ma'lumotda **yo'q** narsalar haqidagi savollarga agent "yo'q" deyishi shart. Masalan:
  - 2021 yil yoki noyabr 2026
  - boshqa birjalar
  - shartnoma kartochkasida yo'q tovarlar ("oltin", "bug'doy uni 5-sort")
  - kompaniya rahbari, telefoni

## 5. Kutilayotgan savol turlari (taxmin) va ular uchun javob shakli

| Tur | Misol (UZ / RU) | Kerakli amal |
|---|---|---|
| Bitta bitim | "350000-bitim kim o'rtasida?" / "Кто покупатель по сделке 350000?" | ID bo'yicha qidiruv + JOIN |
| Shartnoma kartochkasi | "Shartnoma 101373 bo'yicha to'lov muddati?" | contracts |
| Kompaniya | "STIR 953758401 qaysi kompaniya, qayerda?" | participants |
| Agregatsiya | "2024-yilda qancha tonna paxta sotildi?" | SUM(Количество×Лот), TN VED, holat filtri |
| Top-N | "2025-yilda eng ko'p sotib olgan xaridor?" / "Топ-5 брокеров по сумме" | GROUP BY + ORDER |
| O'rtacha narx | "Mart 2023 da sementning o'rtacha narxi?" | Сумма/(Кол×Лот), birlik |
| Valyuta | "Eksport bitimlari so'mda qancha?" / "Курс доллара 15.06.2024?" | usd_rates JOIN |
| Holat | "Nechta bitim bekor qilingan?" / "Qisman bajarilganlar?" | Состояние |
| Muddat | "Yetkazish kechikkan bitimlar soni?" | sana farqi > Срок поставки |
| Region | "Namangan viloyatida eng ko'p sotilgan tovar?" | Регион |
| Broker | "BK045 brokeri nechta bitimda qatnashgan?" | 2 ustun (sotuvchi + xaridor) |
| Javobsiz | "2021-yildagi savdo?", "Oltin narxi?" | **"Ma'lumotlarda yo'q"** |
| Tuzoq | Mavjud bo'lmagan bitim raqami, o'xshash kompaniya nomi | yo'q / aniqlashtirish |

## 6. Bundan chiqadigan arxitektura talablari

1. **Deterministik hisoblash:** raqamlar faqat SQL natijasidan olinadi. LLM raqam yozmaydi, faqat natijani formatlaydi. Javobdagi har bir raqam natijada borligi kod bilan tekshiriladi.
2. **Normallashtirilgan baza:**
   - raqamli ustunlar
   - ISO sanalar
   - `product_canon` (TN VED → kanonik nom RU/UZ)
   - sort va klass normallashgan
   - `region_uz` / `region_ru`
   - kompaniya nomlarining lotin transliteratsiyasi
3. **Entity resolution:** tovar, kompaniya va regionni lug'at hamda fuzzy qidiruv bilan aniqlash. Noaniq bo'lsa, nomzodlar ko'rsatiladi.
4. **Javobsiz holatni aniqlash:** natija bo'sh, ma'lumot davri tashqarisi yoki sxemada bunday maydon yo'q bo'lsa, agent "yo'q" deydi.
5. **Shaffoflik:** javob ostida qanday filtr ishlatilgani, SQL va namunaviy bitim raqamlari ko'rsatiladi.
6. **Til:** savol tilini aniqlash, javob o'sha tilda.
7. **Tezlik:** 90 soniyadan ancha kam. Maqsad: < 15 soniya.
8. **Ishonchlilik:** doim ishlaydigan hosting va LLM xatosi bo'lsa qayta urinish.
9. **Test to'plami:** 40–60 ta RU/UZ savol, javoblari SQL bilan oldindan hisoblangan. Bu "javoblar qanday tekshirilgani" (tavsif, 20 ball) uchun dalil bo'ladi.
