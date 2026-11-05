"""Render an AgentAnswer for Telegram (HTML) or CLI: answer first, then a short human-readable basis.

Layout (Telegram):
    <answer, key figures in bold>

    ✅ Ma'lumotlar asosida · 1 qator · 12.9 s
    🔎 Talqin: <how the question was understood>
    ▸ SQL (collapsed, expandable quote)
"""

from __future__ import annotations

import re

from app.agent import AgentAnswer
from app.script import UZ_CYR, lat_to_cyr

MAX_SQL_CHARS = 700
EVIDENCE_OPEN = "<blockquote expandable>"
_BOLD_RE = re.compile(r"\*\*(.+?)\*\*", re.S)
_ITALIC_RE = re.compile(r"(?<![\w_])__(.+?)__(?![\w_])", re.S)

LABELS = {
    "uz": {
        "verified": "Ma'lumotlar asosida",
        "no_data": "Ma'lumotlarda javob topilmadi",
        "rows": "qator",
        "interp": "Talqin",
        "sql": "So'rov (SQL)",
        "rephrase": "Savolni boshqacha ifodalab ko'ring, masalan: «2024-yilda qancha paxta sotilgan?»",
    },
    "ru": {
        "verified": "По данным биржи",
        "no_data": "В данных ответа нет",
        "rows": "строк",
        "interp": "Как понят вопрос",
        "sql": "Запрос (SQL)",
        "rephrase": "Попробуйте переформулировать, например: «Сколько хлопка продано в 2024 году?»",
    },
}


def _labels(lang: str) -> dict[str, str]:
    if lang == UZ_CYR:
        return {k: lat_to_cyr(v) for k, v in LABELS["uz"].items()}
    return LABELS["uz" if lang == "uz" else "ru"]


def escape_html(text: str) -> str:
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def answer_html(text: str) -> str:
    """Escape user-visible text, then turn **x** into <b>x</b> and __x__ into <i>x</i>."""
    return _ITALIC_RE.sub(r"<i>\1</i>", _BOLD_RE.sub(r"<b>\1</b>", escape_html(text)))


def render(ans: AgentAnswer, *, show_sql: bool = True) -> str:
    labels = _labels(ans.language)
    parts = [answer_html(ans.answer)]
    if not ans.answerable:
        parts.append(f"\nℹ️ {labels['no_data']} · {ans.elapsed_sec:.1f} s")
        return "\n".join(parts)
    if not ans.sql:
        return "\n".join(parts)
    if not ans.rows:
        parts.append(f"\n🔍 {labels['no_data']} · {ans.elapsed_sec:.1f} s")
        parts.append(f"💡 {labels['rephrase']}")
    else:
        parts.append(f"\n✅ {labels['verified']} · {len(ans.rows)} {labels['rows']} · {ans.elapsed_sec:.1f} s")
    if ans.interpretation:
        parts.append(f"🔎 {labels['interp']}: <i>{escape_html(ans.interpretation)}</i>")
    if show_sql:
        sql = ans.sql if len(ans.sql) <= MAX_SQL_CHARS else ans.sql[:MAX_SQL_CHARS] + " …"
        parts.append(f"{EVIDENCE_OPEN}▸ {labels['sql']}\n<code>{escape_html(sql)}</code></blockquote>")
    return "\n".join(parts)


def render_plain(ans: AgentAnswer) -> str:
    """CLI variant without HTML."""
    labels = _labels(ans.language)
    out = [ans.answer.replace("**", "")]
    if ans.interpretation:
        out.append(f"{labels['interp']}: {ans.interpretation}")
    if ans.sql:
        out.append(ans.sql)
    out.append(f"{len(ans.rows)} {labels['rows']} · {ans.elapsed_sec:.1f} s")
    return "\n".join(out)
