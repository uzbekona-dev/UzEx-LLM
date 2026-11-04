"""Static dictionaries: regions, statuses, product canon (by TN VED code), UZ/RU terms.

Everything here is hand-written from the dataset (README + profiling) so the LLM never has
to guess a value that exists in the data.
"""

# deals/participants use Uzbek-Latin region names; contracts use Russian. 1:1 mapping.
REGIONS = [
    # (uz_latin, ru, aliases for matching)
    ("Toshkent shahri", "г. Ташкент", ["toshkent shahri", "tashkent city", "г. ташкент", "город ташкент", "ташкент город", "toshkent sh"]),
    ("Toshkent viloyati", "Ташкентская область", ["toshkent viloyati", "ташкентская область", "toshkent vil"]),
    ("Andijon viloyati", "Андижанская область", ["andijon", "андижан", "андижанская"]),
    ("Buxoro viloyati", "Бухарская область", ["buxoro", "бухара", "бухарская"]),
    ("Farg‘ona viloyati", "Ферганская область", ["farg'ona", "fargona", "farg‘ona", "фергана", "ферганская"]),
    ("Jizzax viloyati", "Джизакская область", ["jizzax", "джизак", "джизакская"]),
    ("Namangan viloyati", "Наманганская область", ["namangan", "наманган", "наманганская"]),
    ("Navoiy viloyati", "Навоийская область", ["navoiy", "навои", "навоийская"]),
    ("Qashqadaryo viloyati", "Кашкадарьинская область", ["qashqadaryo", "кашкадарья", "кашкадарьинская"]),
    ("Qoraqalpog‘iston Respublikasi", "Республика Каракалпакстан", ["qoraqalpog'iston", "qoraqalpogiston", "каракалпакстан", "каракалпакия"]),
    ("Samarqand viloyati", "Самаркандская область", ["samarqand", "самарканд", "самаркандская"]),
    ("Sirdaryo viloyati", "Сырдарьинская область", ["sirdaryo", "сырдарья", "сырдарьинская"]),
    ("Surxondaryo viloyati", "Сурхандарьинская область", ["surxondaryo", "сурхандарья", "сурхандарьинская"]),
    ("Xorazm viloyati", "Хорезмская область", ["xorazm", "хорезм", "хорезмская"]),
]
REGION_RU_TO_UZ = {ru: uz for uz, ru, _ in REGIONS}

DEAL_STATUSES = {
    "Новый": "Yangi (30.10.2026 kuni tuzilgan)",
    "Не подписан": "Imzolanmagan",
    "Заключен": "Tuzilgan (forvard/fyuchers imzolangan, to'lov muddati o'tmagan)",
    "Ждёт оплату": "To'lov kutilmoqda",
    "Оплачен": "To'langan (hali yetkazilmagan)",
    "Исполнен": "Bajarilgan (to'langan va to'liq yetkazilgan)",
    "Исполнен(Частично)": "Qisman bajarilgan",
    "Аннулирован(Не оплачен)": "Bekor qilingan (muddatida to'lanmagan) — bitim amalga oshmagan",
}

TRADE_TYPES = {
    "Английский аукцион": "Ingliz auksioni (narx boshlang'ichdan oshadi)",
    "Обратный аукцион": "Teskari auksion (narx boshlang'ichdan tushadi)",
    "Двусторонний аукцион": "Ikki tomonlama auksion",
}
CONTRACT_TYPES = {"Внутренний": "Ichki", "Экспортный": "Eksport"}
CONTRACT_FORMS = {"Спот": "Spot", "Форвард": "Forvard", "Фьючерс": "Fyuchers"}
UNITS = {"тонна": "tonna", "килограмм": "kilogramm", "литр": "litr", "штука": "dona",
         "куб.метр": "kub metr", "кв.метр": "kv. metr", "метр": "metr"}
CURRENCIES = {"Узбекский сум": "O'zbek so'mi", "Доллар США": "AQSh dollari"}

# TN VED code -> (canonical RU, canonical UZ, search aliases). Covers all 40 codes in contracts.csv.
PRODUCTS = {
    "520100": ("Хлопок-сырец", "Paxta xomashyosi", ["хлопок", "хлопок-сырец", "хлопок сырец", "paxta", "пахта", "cotton", "paxta xomashyosi"]),
    "252329": ("Портландцемент", "Portlandsement", ["цемент", "портландцемент", "sement", "цем", "cement"]),
    "100199": ("Пшеница продовольственная", "Oziq-ovqat bug'doyi", ["пшеница", "bug'doy", "bugdoy", "буғдой", "wheat"]),
    "271019": ("Дизельное топливо / Мазут", "Dizel yoqilg'isi / Mazut", ["дизель", "дизельное топливо", "дизтопливо", "мазут", "dizel", "mazut", "солярка"]),
    "110100": ("Мука пшеничная", "Bug'doy uni", ["мука", "un", "ун", "flour", "мука пшеничная"]),
    "271012": ("Бензин автомобильный", "Avtomobil benzini", ["бензин", "benzin", "бензин автомобильный", "аи-92", "аи-95", "аи-80", "ai-92", "ai-95"]),
    "390120": ("Полиэтилен", "Polietilen", ["полиэтиленовый", "полиэтилен", "polietilen", "pe", "hd-5502", "pe-3015"]),
    "271112": ("Сжиженный газ (пропан-бутан)", "Suyultirilgan gaz (propan-butan)", ["сжиженный газ", "газ", "пропан", "бутан", "gaz", "suyultirilgan gaz", "propan"]),
    "721420": ("Арматура стальная", "Po'lat armatura", ["арматура", "armatura", "арматура стальная"]),
    "170199": ("Сахар", "Shakar", ["сахар", "сахар-песок", "shakar", "qand", "шакар", "sugar"]),
    "151229": ("Масло хлопковое", "Paxta yog'i", ["хлопковое масло", "масло хлопковое", "paxta yog'i", "paxta yogi", "пахта ёғи"]),
    "310210": ("Карбамид (мочевина)", "Karbamid", ["карбамид", "мочевина", "karbamid", "urea"]),
    "390210": ("Полипропилен", "Polipropilen", ["полипропилен", "polipropilen", "pp"]),
    "310230": ("Аммиачная селитра", "Ammiakli selitra", ["селитра", "аммиачная селитра", "selitra", "ammiakli selitra"]),
    "230610": ("Шрот хлопковый", "Paxta shroti", ["шрот", "шрот хлопковый", "shrot", "paxta shroti", "кунжара"]),
    "271320": ("Битум нефтяной", "Neft bitumi", ["битум", "bitum"]),
    "390410": ("Поливинилхлорид (ПВХ)", "Polivinilxlorid (PVX)", ["пвх", "поливинилхлорид", "pvx", "pvc"]),
    "690410": ("Кирпич керамический", "Keramik g'isht", ["кирпич", "g'isht", "gisht", "ғишт", "brick"]),
    "280700": ("Кислота серная", "Sulfat kislota", ["серная кислота", "кислота серная", "sulfat kislota", "кислота"]),
    "151219": ("Масло подсолнечное", "Kungaboqar yog'i", ["подсолнечное масло", "масло подсолнечное", "kungaboqar yog'i", "kungaboqar"]),
    "740311": ("Катод медный", "Mis katodi", ["катод", "медный катод", "катод медный", "mis", "mis katodi", "медь", "copper"]),
    "440711": ("Пиломатериалы", "Yog'och materiallari (taxta)", ["пиломатериал", "пиломатериалы", "taxta", "yog'och", "доска", "lumber"]),
    "100630": ("Рис шлифованный", "Guruch", ["рис", "guruch", "гуруч", "rice"]),
    "700529": ("Стекло флоат / листовое", "Oyna (float)", ["стекло", "oyna", "ойна", "glass", "стекло флоат"]),
    "720853": ("Лист стальной горячекатаный", "Issiq prokat po'lat list", ["лист стальной", "стальной лист", "po'lat list", "лист"]),
    "520512": ("Пряжа хлопчатобумажная", "Paxta ipi (kalava)", ["пряжа", "ip", "kalava", "ип", "yarn"]),
    "230990": ("Комбикорм / кормосмесь", "Omuxta yem", ["комбикорм", "кормосмесь", "yem", "omuxta yem", "корм"]),
    "250100": ("Соль пищевая", "Osh tuzi", ["соль", "tuz", "туз", "salt"]),
    "252020": ("Гипс строительный", "Qurilish gipsi", ["гипс", "gips", "гипс строительный"]),
    "721710": ("Проволока арматурная", "Armatura simi", ["проволока", "sim", "проволока арматурная"]),
    "760421": ("Профиль алюминиевый", "Alyuminiy profil", ["алюминиевый профиль", "профиль алюминиевый", "профиль", "alyuminiy", "алюминий"]),
    "281511": ("Сода каустическая", "Kaustik soda", ["сода", "каустическая сода", "сода каустическая", "soda", "kaustik"]),
    "854449": ("Кабель силовой", "Kuch kabeli", ["кабель", "kabel", "кабель силовой"]),
    "320810": ("Эмаль", "Emal (bo'yoq)", ["эмаль", "краска", "emal", "bo'yoq", "пф-115"]),
    "252210": ("Известь", "Ohak", ["известь", "ohak", "оҳак"]),
    "280430": ("Азот", "Azot", ["азот", "azot"]),
    "220190": ("Вода питьевая", "Ichimlik suvi", ["вода", "питьевая вода", "suv", "ichimlik suvi"]),
    "848210": ("Подшипник", "Podshipnik", ["подшипник", "podshipnik"]),
    "391721": ("Трубы полиэтиленовые", "Polietilen quvurlar", ["труба", "трубы", "quvur", "труба пэ", "трубы полиэтиленовые"]),
    "280421": ("Аргон газообразный", "Argon gazi", ["аргон", "argon"]),
}

# How a "sort" / "class" is written in the data -> normalized integer
GRADE_WORDS = {
    "1": 1, "i": 1, "первый": 1, "первого": 1, "высший": 0, "высшего": 0, "высш": 0,
    "2": 2, "ii": 2, "второй": 2, "второго": 2,
    "3": 3, "iii": 3, "третий": 3, "третьего": 3,
    "4": 4, "iv": 4,
}

DATA_MIN_DATE = "2022-01-03"
DATA_MAX_DATE = "2026-10-30"
