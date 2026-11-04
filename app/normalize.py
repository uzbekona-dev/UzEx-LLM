"""Pure normalization helpers: numbers, dates, grades, transliteration."""

from __future__ import annotations

import datetime as dt
import re

from app.dictionaries import GRADE_WORDS

_CYR_TO_LAT = {
    "а": "a", "б": "b", "в": "v", "г": "g", "д": "d", "е": "e", "ё": "yo", "ж": "j", "з": "z",
    "и": "i", "й": "y", "к": "k", "л": "l", "м": "m", "н": "n", "о": "o", "п": "p", "р": "r",
    "с": "s", "т": "t", "у": "u", "ф": "f", "х": "x", "ц": "ts", "ч": "ch", "ш": "sh", "щ": "sh",
    "ъ": "", "ы": "i", "ь": "", "э": "e", "ю": "yu", "я": "ya",
    "қ": "q", "ғ": "g", "ў": "o", "ҳ": "h",
}


def parse_number(text: str) -> float | None:
    """'304 547 938.4' -> 304547938.4 ; '' -> None."""
    if text is None:
        return None
    cleaned = text.replace(" ", "").replace(" ", "").replace(",", ".")
    if cleaned == "":
        return None
    return float(cleaned)


def parse_date(text: str) -> str | None:
    """'03.01.2022' -> '2022-01-03' (ISO, sortable in SQLite)."""
    if not text:
        return None
    return dt.datetime.strptime(text, "%d.%m.%Y").date().isoformat()


def parse_percent(text: str) -> float | None:
    """'10 %' -> 10.0"""
    if not text:
        return None
    return float(text.replace("%", "").strip())


def translit(text: str) -> str:
    """Lowercase Latin search key: strips quotes/apostrophes, maps Cyrillic (RU + UZ) to Latin."""
    out = []
    for ch in text.lower():
        if ch in "‘’'`\"«»":
            continue
        out.append(_CYR_TO_LAT.get(ch, ch))
    key = "".join(out)
    key = key.replace("o‘", "o").replace("g‘", "g")
    key = re.sub(r"[^a-z0-9]+", " ", key)
    return re.sub(r"\s+", " ", key).strip()


_LEGAL_FORMS = re.compile(
    r"\b(mchj|mas uliyati cheklangan jamiyati|masuliyati cheklangan jamiyati|ooo|aj|ok|xk|qk|ip|yatt|broker)\b"
)


def company_key(name: str) -> str:
    """Search key without legal form: '"Qojo‘ Invest" MChJ' -> 'qojo invest'."""
    return _LEGAL_FORMS.sub(" ", translit(name)).strip()


_GRADE_RE = re.compile(r"(?:сорт[а-я]*\s*([0-9ivх]+|высш[а-я]*|перв[а-я]*|втор[а-я]*|трет[а-я]*)|([0-9ivх]+|высш[а-я]*|перв[а-я]*|втор[а-я]*|трет[а-я]*)[\s-]*сорт)", re.I)
_CLASS_RE = re.compile(r"(?:класс[а-я]*\s*([0-9ivх]+)|([0-9ivх]+)[\s-]*класс)", re.I)


def _grade_value(word: str | None) -> int | None:
    if not word:
        return None
    w = word.lower().replace("х", "x")
    w = re.sub(r"[^a-zа-я0-9]", "", w)
    for key, val in GRADE_WORDS.items():
        if w == key or (len(key) > 3 and w.startswith(key[:4])):
            return val
    return None


def parse_grade_class(text: str) -> tuple[int | None, int | None]:
    """Extract (sort, class) from a product string like 'Хлопок-сырец (спот) I сорт 1-класс'."""
    sort = None
    cls = None
    m = _GRADE_RE.search(text)
    if m:
        sort = _grade_value(m.group(1) or m.group(2))
    m = _CLASS_RE.search(text)
    if m:
        cls = _grade_value(m.group(1) or m.group(2))
    return sort, cls
