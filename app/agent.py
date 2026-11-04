"""Question -> SQL -> verified answer. The LLM never computes numbers; SQLite does."""

from __future__ import annotations

import json
import logging
import re
import sqlite3
import time
from dataclasses import dataclass, field

from app.llm import Llm
from app.schema_prompt import RULES, SCHEMA_DOC
from app.sql_guard import QueryResult, run_query
from app.verify import verify_answer

log = logging.getLogger(__name__)

MAX_SQL_ATTEMPTS = 3

PLAN_SYSTEM = f"""You translate questions about exchange deals (Russian or Uzbek) into SQLite SQL.
{SCHEMA_DOC}
{RULES}
Respond ONLY with JSON:
{{"language": "ru" | "uz", "answerable": true|false, "reason": "<why not, if false>",
  "interpretation": "<one short sentence IN THE LANGUAGE OF THE QUESTION (uz = Latin script), for the end user: how you understood it, incl. assumptions (period, product, cancelled excluded...). No column names.>",
  "sql": "<single SELECT>" }}
"""

ANSWER_SYSTEM = """You write the final answer for a user of an exchange-deals assistant.
You receive: the question, how it was interpreted, the SQL, and the result rows (JSON).
STRICT RULES:
- Use ONLY numbers, names, codes that appear in the result rows. Never add numbers from memory. Never explain causes.
- If the result is empty, say clearly that the data contains no such record (do not guess).
- Answer in the language given (ru or uz). Uzbek must be in Latin script, fully: translate unit and currency labels from the rows ('Узбекский сум' -> so'm, 'Доллар США' -> AQSh dollari, 'тонна' -> tonna, 'килограмм' -> kg, 'Исполнен' -> Bajarilgan, 'Аннулирован' -> Bekor qilingan); keep company names and codes exactly as in the rows. Keep product names also in Russian in parentheses if useful.
- Be concise: 1-4 sentences with the key figures, then if there are several rows a short list (max 10 lines).
- Format big numbers with thin spaces for thousands (e.g. 1 234 567.89). Give units and currency.
- The ONLY arithmetic you may do: kilogram -> tonna (divide by 1000) when the user asked in tonnes; then show both: "1 672 494.96 tonna (1 672 494 955 kg)". No other conversions, no percentages, no sums.
- If several companies matched the name, present each with its INN.
- If the interpretation contains assumptions (e.g. cancelled deals excluded), state them in ONE short sentence at the end.
- Mark the 1-3 key figures the user asked for with **double asterisks** (e.g. **1 672 494.96 tonna**). No other markdown: no tables, headings, code blocks.
- Start directly with the answer; no greetings, no "according to the data"."""


@dataclass(frozen=True)
class AgentAnswer:
    question: str
    language: str
    answer: str
    interpretation: str
    sql: str | None
    rows: list[tuple]
    columns: list[str]
    answerable: bool
    verified: bool
    elapsed_sec: float
    debug: list[str] = field(default_factory=list)


def _parse_json(text: str) -> dict:
    text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text.strip(), flags=re.I)
    return json.loads(text)


def _no_data_message(lang: str, reason: str) -> str:
    if lang == "uz":
        return f"Ma'lumotlarda bu savolga javob yo'q. {reason}".strip()
    return f"В данных нет ответа на этот вопрос. {reason}".strip()


def _fallback_answer(lang: str, result: QueryResult) -> str:
    """Template answer used when the LLM prose fails verification twice."""
    if not result.rows:
        return _no_data_message(lang, "")
    head = "Natija (ma'lumotlardan to'g'ridan-to'g'ri):" if lang == "uz" else "Результат (напрямую из данных):"
    lines = [head]
    for row in result.rows[:10]:
        lines.append("; ".join(f"{c}: {v}" for c, v in zip(result.columns, row)))
    return "\n".join(lines)


class Agent:
    def __init__(self, con: sqlite3.Connection, llm: Llm) -> None:
        self.con = con
        self.llm = llm

    def _plan(self, question: str, feedback: str | None) -> dict:
        user = f"QUESTION: {question}"
        if feedback:
            user += f"\n\nPREVIOUS ATTEMPT FAILED: {feedback}\nFix the SQL."
        resp = self.llm.complete(PLAN_SYSTEM, user, json_mode=True)
        return _parse_json(resp.text)

    def _query_with_retries(self, question: str, debug: list[str]) -> tuple[dict, QueryResult | None]:
        feedback = None
        plan: dict = {}
        for attempt in range(1, MAX_SQL_ATTEMPTS + 1):
            plan = self._plan(question, feedback)
            debug.append(f"plan#{attempt}: {json.dumps(plan, ensure_ascii=False)[:800]}")
            if not plan.get("answerable", False) or not plan.get("sql"):
                return plan, None
            result = run_query(self.con, plan["sql"])
            if result.ok:
                return plan, result
            feedback = f"SQL error: {result.error}"
            debug.append(feedback)
        return plan, QueryResult(sql=plan.get("sql", ""), columns=[], rows=[], elapsed_sec=0, error="gave up")

    def _write_answer(self, question: str, plan: dict, result: QueryResult, note: str | None) -> str:
        payload = {
            "question": question, "language": plan.get("language", "ru"),
            "interpretation": plan.get("interpretation", ""), "sql": result.sql,
            "row_count": len(result.rows), "truncated": result.truncated,
            "rows": result.as_records(),
        }
        user = json.dumps(payload, ensure_ascii=False, default=str)
        if note:
            user += f"\n\nIMPORTANT: {note}"
        return self.llm.complete(ANSWER_SYSTEM, user).text.strip()

    def ask(self, question: str) -> AgentAnswer:
        started = time.monotonic()
        debug: list[str] = []
        plan, result = self._query_with_retries(question, debug)
        lang = plan.get("language", "ru")
        if result is None:
            return AgentAnswer(question, lang, _no_data_message(lang, plan.get("reason", "")),
                               plan.get("interpretation", ""), None, [], [], False, True,
                               time.monotonic() - started, debug)
        if not result.ok:
            msg = ("So'rovni tuza olmadim, iltimos savolni boshqacha ifodalang." if lang == "uz"
                   else "Не удалось построить запрос, пожалуйста, переформулируйте вопрос.")
            return AgentAnswer(question, lang, msg, plan.get("interpretation", ""), result.sql, [], [],
                               True, False, time.monotonic() - started, debug)

        note = None
        verified = False
        answer = ""
        for _ in range(2):
            answer = self._write_answer(question, plan, result, note)
            context = f"{question}\n{plan.get('interpretation', '')}\n{result.sql}"
            check = verify_answer(answer, result.rows, context)
            debug.append(f"verify: ok={check.ok} unsupported={check.unsupported[:5]}")
            if check.ok:
                verified = True
                break
            note = (f"Your previous answer contained numbers not present in the rows: {check.unsupported[:5]}. "
                    "Rewrite using only values from the rows, copied exactly.")
        if not verified:
            answer = _fallback_answer(lang, result)
            verified = True
        return AgentAnswer(question, lang, answer, plan.get("interpretation", ""), result.sql, result.rows,
                           result.columns, True, verified, time.monotonic() - started, debug)
