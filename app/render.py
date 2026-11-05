"""Fill the LLM-written answer template with query rows — the only place numbers enter the text.

Template language (written by the planner, filled here):
  {col}         value of a result column (numbers formatted with thin spaces, max 2 decimals)
  {col:t}       kilograms -> tonnes (÷ 1000)       {col:int}  no decimals      {col:date}  DD.MM.YYYY
  {row_count}   number of rows                      {C1} {B1} {INN1}  entity placeholders (unmasked by caller)
Blocks: headline (uses the first row), line (one per row, max 10), empty (no rows), note (assumptions).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from app.dictionaries import CONTRACT_FORMS, CONTRACT_TYPES, CURRENCIES, DEAL_STATUSES, TRADE_TYPES, UNITS
from app.script import UZ_CYR, base_lang, lat_to_cyr
from app.verify import extract_numbers

MAX_LINES = 10
THIN = " "
_PLACEHOLDER_RE = re.compile(r"\{([A-Za-z_][\w]*)(?::(t|int|date|raw))?\}")
_ENTITY_RE = re.compile(r"^(C\d+|B\d+|INN\d+)$")

_UZ_SHORT_STATUS = {k: v.split(" (")[0].split(" —")[0] for k, v in DEAL_STATUSES.items()}
_UZ_LABELS = {**UNITS, **CURRENCIES, **_UZ_SHORT_STATUS, **CONTRACT_TYPES, **CONTRACT_FORMS,
              **{k: v.split(" (")[0] for k, v in TRADE_TYPES.items()},
              "килограмм": "kg", "Узбекский сум": "so'm", "Продавец": "Sotuvchi", "Покупатель": "Xaridor"}
_RU_LABELS = {"Узбекский сум": "сум", "Доллар США": "долл. США", "тонна": "т", "килограмм": "кг"}
_ID_COLUMN_RE = re.compile(r"(^|_)(no|num|number|inn|code|year|month|day|tnved|id)$", re.I)


class TemplateError(ValueError):
    pass


@dataclass(frozen=True)
class RenderSpec:
    headline: str = ""
    line: str = ""
    empty: str = ""
    note: str = ""

    @classmethod
    def from_plan(cls, raw: object) -> "RenderSpec":
        if not isinstance(raw, dict):
            return cls()
        return cls(**{k: str(raw.get(k) or "") for k in ("headline", "line", "empty", "note")})

    def texts(self) -> list[str]:
        return [t for t in (self.headline, self.line, self.empty, self.note) if t]


@dataclass(frozen=True)
class Rendered:
    text: str
    used_template: bool
    problems: list[str] = field(default_factory=list)


# ----------------------------------------------------------------------------- formatting
def format_number(value: float | int, *, decimals: int | None = None) -> str:
    if isinstance(value, bool):
        return str(value)
    if decimals is None:
        decimals = 0 if float(value).is_integer() else 2
    text = f"{value:,.{decimals}f}".replace(",", THIN)
    if decimals and "." in text:
        text = text.rstrip("0").rstrip(".")
    return text


def format_date(value: str) -> str:
    m = re.match(r"^(\d{4})-(\d{2})-(\d{2})", str(value))
    return f"{m.group(3)}.{m.group(2)}.{m.group(1)}" if m else str(value)


def format_value(value: object, modifier: str | None, lang: str, column: str = "") -> str:
    if value is None:
        return "—"
    if modifier == "raw" or (modifier is None and _ID_COLUMN_RE.search(column) and not isinstance(value, str)):
        return str(int(value)) if isinstance(value, float) and value.is_integer() else str(value)
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        if modifier == "t":
            return format_number(value / 1000)
        if modifier == "int":
            return format_number(round(value), decimals=0)
        return format_number(value)
    text = str(value)
    if modifier == "date" or (modifier is None and "date" in column.lower()):
        return format_date(text)
    if lang == UZ_CYR:
        return lat_to_cyr(_UZ_LABELS[text]) if text in _UZ_LABELS else text  # our label, not data
    if lang == "uz":
        return _UZ_LABELS.get(text, text)
    return _RU_LABELS.get(text, text)


# ----------------------------------------------------------------------------- guard
def check_template(spec: RenderSpec, columns: list[str], context: str) -> list[str]:
    """Reject templates that smuggle values in: unknown columns, digits not in the question/SQL."""
    problems: list[str] = []
    allowed_numbers = set(extract_numbers(context))
    known = set(columns) | {"row_count"}
    for text in spec.texts():
        for m in _PLACEHOLDER_RE.finditer(text):
            name = m.group(1)
            if name not in known and not _ENTITY_RE.match(name):
                problems.append(f"unknown column {{{name}}}")
        stripped = _PLACEHOLDER_RE.sub(" ", text)
        for value in extract_numbers(stripped):
            if value <= 12 and value.is_integer():
                continue
            if value not in allowed_numbers:
                problems.append(f"literal number {value:g} in template")
    if not spec.headline and not spec.line:
        problems.append("template has neither headline nor line")
    return problems


# ----------------------------------------------------------------------------- rendering
def _fill(template: str, row: dict, row_count: int, lang: str) -> str:
    def repl(m: re.Match) -> str:
        name, modifier = m.group(1), m.group(2)
        if name == "row_count":
            return format_number(row_count, decimals=0)
        if _ENTITY_RE.match(name):
            return m.group(0)  # unmasked later by the caller
        if name not in row:
            raise TemplateError(f"unknown column {name}")
        return format_value(row[name], modifier, lang, name)
    return _PLACEHOLDER_RE.sub(repl, template)


def render_template(spec: RenderSpec, columns: list[str], rows: list[tuple], lang: str) -> str:
    records = [dict(zip(columns, r)) for r in rows]
    if not records:
        return spec.empty or _own("Ma'lumotlarda mos yozuv topilmadi.", lang) if base_lang(lang) == "uz" \
            else (spec.empty or "В данных подходящих записей нет.")
    parts: list[str] = []
    # several rows but no per-row template: repeat the headline per row so no row is silently dropped
    line = spec.line or (spec.headline if len(records) > 1 else "")
    if spec.headline and spec.line:
        parts.append(_fill(spec.headline, records[0], len(records), lang))
    elif spec.headline and len(records) == 1:
        parts.append(_fill(spec.headline, records[0], len(records), lang))
    if line and (len(records) > 1 or not spec.headline):
        parts.extend(_fill(line, rec, len(records), lang) for rec in records[:MAX_LINES])
        if len(records) > MAX_LINES:
            parts.append("…")
    if spec.note:
        parts.append("")
        parts.append(_fill(spec.note, records[0], len(records), lang))
    return "\n".join(parts).strip()


# Human labels for common column names (substring match on the snake_case name, first hit wins).
_COLUMN_LABELS: list[tuple[str, str, str]] = [
    ("cancel", "Bekor qilingan", "Аннулировано"),
    ("active", "Amaldagi", "Действующих"),
    ("deal_count", "Bitimlar soni", "Сделок"), ("deals_total", "Bitimlar soni", "Сделок"),
    ("total_deals", "Bitimlar soni", "Сделок"), ("deals", "Bitimlar", "Сделок"),
    ("contract_count", "Shartnomalar soni", "Контрактов"), ("contracts", "Shartnomalar", "Контрактов"),
    ("weighted", "O'rtacha vaznli narx", "Средневзвешенная цена"),
    ("avg_price", "O'rtacha narx", "Средняя цена"), ("avg", "O'rtacha", "Среднее"),
    ("min", "Eng kichik", "Минимум"), ("max", "Eng katta", "Максимум"),
    ("unit_price", "Narx (birlik uchun)", "Цена за единицу"), ("start_price", "Boshlang'ich narx", "Стартовая цена"),
    ("price", "Narx", "Цена"), ("rate", "Kurs", "Курс"),
    ("amount_uzs", "Summa (so'm)", "Сумма (сум)"), ("amount", "Summa", "Сумма"),
    ("volume", "Hajm", "Объём"), ("quantity", "Miqdor", "Количество"), ("lot", "Lot", "Лот"),
    ("deal_no", "Bitim №", "Сделка №"), ("contract_no", "Shartnoma №", "Контракт №"),
    ("deal_date", "Sana", "Дата"), ("date", "Sana", "Дата"),
    ("seller_name", "Sotuvchi", "Продавец"), ("buyer_name", "Xaridor", "Покупатель"),
    ("seller_inn", "Sotuvchi STIR", "ИНН продавца"), ("buyer_inn", "Xaridor STIR", "ИНН покупателя"),
    ("inn", "STIR", "ИНН"), ("code", "Kod", "Код"), ("name", "Nomi", "Название"),
    ("product", "Tovar", "Товар"), ("region", "Hudud", "Регион"), ("status", "Holati", "Статус"),
    ("year", "Yil", "Год"), ("month", "Oy", "Месяц"), ("count", "Soni", "Количество"),
]
_TITLE_COLUMNS = ("code", "name", "seller_name", "buyer_name", "product", "region", "inn")


def _label(column: str, lang: str) -> str:
    low = column.lower()
    for key, uz, ru in _COLUMN_LABELS:
        if key in low:
            return _own(uz, lang) if base_lang(lang) == "uz" else ru
    return column.replace("_", " ").capitalize()


def _pair_units(columns: list[str]) -> dict[str, str]:
    """volume -> unit, amount -> currency: print '1 234 kg' instead of two separate fields."""
    pairs: dict[str, str] = {}
    if "unit" in columns:
        for c in columns:
            if "volume" in c.lower() or "quantity" in c.lower():
                pairs[c] = "unit"
    if "currency" in columns:
        for c in columns:
            if c.lower().startswith("amount") and "uzs" not in c.lower():
                pairs[c] = "currency"
    return pairs


def render_generic(columns: list[str], rows: list[tuple], lang: str) -> str:
    """Readable fallback when the template is unusable: numbered rows, human labels, bold figures.

    Never wrong (values only from rows), just less fluent than a template.
    """
    if not rows:
        return _own("Ma'lumotlarda mos yozuv topilmadi.", lang) if base_lang(lang) == "uz" else "В данных подходящих записей нет."
    pairs = _pair_units(columns)
    hidden = set(pairs.values())
    titles = [c for c in columns if c in _TITLE_COLUMNS and c not in hidden][:2]
    head = (_own("__Natija (ma'lumotlardan to'g'ridan-to'g'ri):__", lang) if base_lang(lang) == "uz"
            else "__Результат (напрямую из данных):__")
    lines = [head]
    for i, row in enumerate(rows[:MAX_LINES], 1):
        rec = dict(zip(columns, row))
        title = " — ".join(format_value(rec[c], None, lang, c) for c in titles if rec[c] is not None)
        facts = []
        for c in columns:
            if c in titles or c in hidden:
                continue
            value = format_value(rec[c], None, lang, c)
            if c in pairs and rec.get(pairs[c]) is not None:
                value = f"{value} {format_value(rec[pairs[c]], None, lang, pairs[c])}"
            facts.append(f"{_label(c, lang)}: **{value}**")
        body = " · ".join(facts)
        prefix = f"{i}. " if len(rows) > 1 else ""
        lines.append(f"{prefix}{title}" + (f" · {body}" if title and body else body))
    if len(rows) > MAX_LINES:
        lines.append("…")
    return "\n".join(lines)


def _own(text: str, lang: str) -> str:
    """Our own Uzbek wording, converted to Cyrillic when the question was written in Cyrillic."""
    return lat_to_cyr(text) if lang == UZ_CYR else text


def render(spec: RenderSpec, columns: list[str], rows: list[tuple], lang: str, context: str) -> Rendered:
    if lang == UZ_CYR:  # convert the template wording before the data values are filled in
        spec = RenderSpec(*(lat_to_cyr(t) for t in (spec.headline, spec.line, spec.empty, spec.note)))
    problems = check_template(spec, columns, context)
    if problems:
        return Rendered(render_generic(columns, rows, lang), False, problems)
    try:
        return Rendered(render_template(spec, columns, rows, lang), True)
    except TemplateError as exc:
        return Rendered(render_generic(columns, rows, lang), False, [str(exc)])
