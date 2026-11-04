"""Render an AgentAnswer for Telegram / CLI, with the evidence block."""

from __future__ import annotations

from app.agent import AgentAnswer

MAX_SQL_CHARS = 700


def render(ans: AgentAnswer, *, show_sql: bool = True) -> str:
    parts = [ans.answer]
    if ans.sql and show_sql:
        lang_uz = ans.language == "uz"
        head = "📎 Asos" if lang_uz else "📎 Основание"
        interp = ans.interpretation
        rows_label = "topilgan qatorlar" if lang_uz else "строк найдено"
        parts.append(f"\n{head}: {interp}\n{rows_label}: {len(ans.rows)} · {ans.elapsed_sec:.1f}s")
        sql = ans.sql if len(ans.sql) <= MAX_SQL_CHARS else ans.sql[:MAX_SQL_CHARS] + " …"
        parts.append(f"<pre>{_escape(sql)}</pre>")
    return "\n".join(parts)


def _escape(text: str) -> str:
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
