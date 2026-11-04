"""Rendering tests: HTML safety, bold markers, basis block, no-data layout."""

from __future__ import annotations

from app.agent import AgentAnswer
from app.format import EVIDENCE_OPEN, answer_html, render, render_plain


def _ans(**kw) -> AgentAnswer:
    base = dict(question="q", language="uz", answer="Jami **12 345 kg** sotilgan", interpretation="2024-yil, bekor qilinganlarsiz",
                sql="SELECT 1", rows=[(12345,)], columns=["v"], answerable=True, verified=True, elapsed_sec=1.23)
    return AgentAnswer(**{**base, **kw})


def test_answer_html_escapes_then_bolds() -> None:
    assert answer_html('A & B <x> **5**') == "A &amp; B &lt;x&gt; <b>5</b>"


def test_render_has_answer_basis_and_collapsed_sql() -> None:
    out = render(_ans())
    assert out.startswith("Jami <b>12 345 kg</b> sotilgan")
    assert "✅ Ma'lumotlar asosida · 1 qator · 1.2 s" in out
    assert "🔎 Talqin: 2024-yil" in out
    assert out.endswith(f"{EVIDENCE_OPEN}▸ So'rov (SQL)\n<code>SELECT 1</code></blockquote>")


def test_render_russian_labels_and_sql_hidden() -> None:
    out = render(_ans(language="ru"), show_sql=False)
    assert "По данным биржи" in out and "<code>" not in out


def test_render_unanswerable_has_no_sql() -> None:
    out = render(_ans(answerable=False, sql=None, rows=[], answer="Ma'lumotlarda javob yo'q."))
    assert "ℹ️ Ma'lumotlarda javob topilmadi" in out and "<code>" not in out


def test_render_empty_result_suggests_rephrase() -> None:
    out = render(_ans(rows=[], language="ru"))
    assert "🔍 В данных ответа нет" in out and "переформулировать" in out


def test_render_plain_strips_markup() -> None:
    out = render_plain(_ans())
    assert "**" not in out and "<" not in out and "SELECT 1" in out
