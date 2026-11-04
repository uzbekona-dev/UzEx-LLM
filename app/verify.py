"""Grounding check: every number, code, date and company name in the answer must come from the query result.

What is checked
- numbers: exact match with a cell (or a rounding of it; scaled to thousands/millions only when the
  answer says so with a scale word); numbers typed in the question or used as literals in the SQL are
  allowed too (years, deal numbers, INN, TN VED codes);
- broker codes BKxxx and dates (ISO or DD.MM.YYYY): must appear in the rows or the question;
- company names (quoted, or ending with a legal form such as MChJ/OOO/AJ): their normalised key must be
  contained in some string cell of the rows.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from app.normalize import company_key, translit

_NUM_RE = re.compile(r"(?<![\w.])[-+]?\d[\d\s ]*(?:[.,]\d+)?(?![\w])")
_SCALE_WORD_RE = re.compile(r"\b(ming|тыс|тысяч\w*|mln|млн|миллион\w*|mlrd|млрд|миллиард\w*|trln|трлн|триллион\w*|k)\b", re.I)
_TONNE_RE = re.compile(r"\b(tonna|tonn\w*|тонн\w*|т)\b", re.I)  # kg -> tonne is the one allowed conversion
_DMY_RE = re.compile(r"\b\d{2}\.\d{2}\.\d{4}\b")
_BROKER_RE = re.compile(r"\bBK\d{3}\b")
_DATE_RE = re.compile(r"\b(\d{4}-\d{2}-\d{2}|\d{2}\.\d{2}\.\d{4})\b")
_LEGAL_FORMS = (
    r"MCHJ|MChJ|OOO|ООО|МЧЖ|AJ|АЖ|АО|XK|ХК|QK|ҚК|OK|ОК|ЧП|XICHJ|FERMER|Fermer|JAMIYATI|KLASTER|Klaster|BROKER|Broker"
)
_QUOTED_RE = re.compile(r"[«\"“„']([^«»\"“”„']{3,80})[»\"”']")
_LEGAL_NAME_RE = re.compile(rf"((?:[\w'‘’`\-\.]+\s+){{1,5}}(?:{_LEGAL_FORMS}))(?![\w])")
SMALL_INT_MAX = 12


def extract_numbers(text: str) -> list[float]:
    out = []
    text = _DMY_RE.sub(" ", text)  # dates are checked separately, not as numbers
    for m in _NUM_RE.finditer(text):
        raw = m.group(0).replace(" ", "").replace(" ", "").replace(",", ".")
        if raw.count(".") > 1:
            raw = raw.replace(".", "", raw.count(".") - 1)
        try:
            out.append(abs(float(raw)))
        except ValueError:
            continue
    return out


def extract_company_names(text: str) -> list[list[str]]:
    """Each item is a list of candidate spellings (longest first); one of them must be in the rows.

    Quoted names give one candidate; names anchored on a legal form give the suffixes
    "<1..5 words> <form>" because the regex cannot know where the name starts.
    """
    names: list[list[str]] = [[m.group(1)] for m in _QUOTED_RE.finditer(text)]
    for m in _LEGAL_NAME_RE.finditer(text):
        words = m.group(1).split()
        names.append([" ".join(words[i:]) for i in range(len(words) - 1)])
    return [[c for c in cands if len(company_key(c)) >= 3] for cands in names if cands]


def _allowed_numbers(rows: list[tuple], context: str) -> set[float]:
    allowed: set[float] = {float(len(rows))}
    for row in rows:
        for cell in row:
            if isinstance(cell, bool):
                continue
            if isinstance(cell, (int, float)):
                allowed.add(abs(float(cell)))
            elif isinstance(cell, str):
                allowed.update(extract_numbers(cell))
    allowed.update(extract_numbers(context))
    return allowed


def _row_strings(rows: list[tuple]) -> list[str]:
    return [cell for row in rows for cell in row if isinstance(cell, str)]


def _matches(value: float, allowed: set[float], scales: tuple[float, ...]) -> bool:
    """Exact value, or a rounding of it (0-2 decimals), optionally scaled when the answer uses scale words."""
    for a in allowed:
        for scale in scales:
            scaled = a / scale
            if value == scaled:
                return True
            for digits in (0, 1, 2):
                if value == round(scaled, digits):
                    return True
    return False


@dataclass(frozen=True)
class Verification:
    ok: bool
    unsupported: list[float]
    unsupported_strings: list[str] = field(default_factory=list)

    @property
    def problems(self) -> list[str]:
        return [str(v) for v in self.unsupported] + self.unsupported_strings


def verify_answer(answer: str, rows: list[tuple], context: str) -> Verification:
    """`context` = question + SQL: numbers quoted from there (years, codes, INN) are fine."""
    allowed = _allowed_numbers(rows, context)
    if _SCALE_WORD_RE.search(answer):
        scales: tuple[float, ...] = (1.0, 1e3, 1e6, 1e9, 1e12)
    elif _TONNE_RE.search(answer):
        scales = (1.0, 1e3)
    else:
        scales = (1.0,)
    unsupported = []
    for value in extract_numbers(answer):
        if value <= SMALL_INT_MAX and value.is_integer() and value <= len(rows):
            continue  # ordinals of a list / small counters bounded by the rows shown
        if not _matches(value, allowed, scales):
            unsupported.append(value)
    bad_strings = _verify_strings(answer, rows, context)
    return Verification(ok=not unsupported and not bad_strings, unsupported=unsupported,
                        unsupported_strings=bad_strings)


def _verify_strings(answer: str, rows: list[tuple], context: str) -> list[str]:
    haystack = "\n".join(_row_strings(rows)) + "\n" + context
    bad: list[str] = []
    for code in _BROKER_RE.findall(answer):
        if code not in haystack:
            bad.append(code)
    for date in _DATE_RE.findall(answer):
        iso = date if "-" in date else "-".join(reversed(date.split(".")))
        if iso not in haystack:
            bad.append(date)
    row_keys = [company_key(s) for s in _row_strings(rows)]
    ctx_key = company_key(context)
    for candidates in extract_company_names(answer):
        if not candidates:
            continue
        keys = [company_key(c) for c in candidates]
        if any(k in ctx_key or any(k in rk or rk in k for rk in row_keys if rk) for k in keys if k):
            continue
        bad.append(candidates[-1])
    return bad


__all__ = ["Verification", "extract_company_names", "extract_numbers", "translit", "verify_answer"]
