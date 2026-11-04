"""Grounding check: every number in the answer must come from the query result (or the question)."""

from __future__ import annotations

import re
from dataclasses import dataclass

_NUM_RE = re.compile(r"(?<![\w.])[-+]?\d[\d\s ]*(?:[.,]\d+)?(?![\w])")


def extract_numbers(text: str) -> list[float]:
    out = []
    for m in _NUM_RE.finditer(text):
        raw = m.group(0).replace(" ", "").replace(" ", "").replace(",", ".")
        if raw.count(".") > 1:
            raw = raw.replace(".", "", raw.count(".") - 1)
        try:
            out.append(float(raw))
        except ValueError:
            continue
    return out


def _allowed_values(rows: list[tuple], context: str) -> set[float]:
    allowed: set[float] = {float(len(rows))}
    for row in rows:
        for cell in row:
            if isinstance(cell, (int, float)) and cell is not None:
                allowed.add(float(cell))
            elif isinstance(cell, str):
                allowed.update(extract_numbers(cell))
    allowed.update(extract_numbers(context))
    return allowed


def _matches(value: float, allowed: set[float]) -> bool:
    """Exact value, or a rounding of it (0-2 decimals), optionally scaled to thousands/millions/billions."""
    for a in allowed:
        for scale in (1.0, 1e3, 1e6, 1e9):
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


def verify_answer(answer: str, rows: list[tuple], context: str) -> Verification:
    """`context` = question + interpretation + SQL: numbers quoted from there (years, codes, INN) are fine."""
    allowed = _allowed_values(rows, context)
    unsupported = []
    for value in extract_numbers(answer):
        if abs(value) <= 12 and float(value).is_integer():
            continue  # ordinals / small counters like "1)", "2-sort", months
        if not _matches(value, allowed):
            unsupported.append(value)
    return Verification(ok=not unsupported, unsupported=unsupported)
