"""Question -> SQL -> verified answer. The LLM never computes numbers; SQLite does.

Safety nets, in order:
  entity resolution in code (candidates only) -> SQL guard (read-only, timeout) ->
  grounding verification of numbers/names/codes/dates -> template fallback ->
  overall time budget so one answer never exceeds the 90 s limit.
"""

from __future__ import annotations

import json
import logging
import os
import re
import sqlite3
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Protocol

from app.llm import Llm, LlmDeadline
from app.schema_prompt import RULES, SCHEMA_DOC
from app.sql_guard import QueryResult, open_db, run_query
from app.verify import verify_answer

log = logging.getLogger(__name__)

MAX_SQL_ATTEMPTS = 3
MAX_ANSWER_ATTEMPTS = 2
START_BUDGET_SEC = float(os.environ.get("ANSWER_BUDGET_SEC", "45"))  # no new LLM call after this (+40 s call timeout < 90 s)
HISTORY_TURNS = 2
QA_LOG_PATH = os.environ.get("QA_LOG", "logs/qa.jsonl")

PLAN_SYSTEM = f"""You translate questions about exchange deals (Russian or Uzbek) into SQLite SQL.
{SCHEMA_DOC}
{RULES}
If RESOLVED ENTITIES are given, use exactly those codes / INNs; if the entity the user named is not among
them, set answerable=false and say which name was not found. If PREVIOUS TURNS are given, treat a short
follow-up ("and in 2023?", "va xaridlari-chi?") as the previous question with that change applied.
Respond ONLY with JSON:
{{"language": "ru" | "uz", "answerable": true|false, "reason": "<why not, if false>",
  "interpretation": "<one short sentence IN THE LANGUAGE OF THE QUESTION (uz = Latin script), for the end user: how you understood it, incl. assumptions (period, product, cancelled excluded, formula used e.g. volume = quantity x lot). No column names.>",
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


class Resolver(Protocol):
    def resolve(self, question: str) -> object: ...  # object has .prompt_block() -> str


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
    timed_out: bool = False


Turn = tuple[str, str]  # (question, interpretation)


def _parse_json(text: str) -> dict:
    text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text.strip(), flags=re.I)
    return json.loads(text)


def _no_data_message(lang: str, reason: str) -> str:
    if lang == "uz":
        return f"Ma'lumotlarda bu savolga javob yo'q. {reason}".strip()
    return f"В данных нет ответа на этот вопрос. {reason}".strip()


def _timeout_message(lang: str) -> str:
    if lang == "uz":
        return "Kechirasiz, javobni vaqtida tayyorlay olmadim (model javob bermadi). Iltimos, savolni qayta yuboring."
    return "Извините, не успел подготовить ответ (модель не ответила вовремя). Пожалуйста, отправьте вопрос ещё раз."


def _fallback_answer(lang: str, result: QueryResult) -> str:
    """Template answer used when the LLM prose fails verification twice."""
    if not result.rows:
        return _no_data_message(lang, "")
    head = "Natija (ma'lumotlardan to'g'ridan-to'g'ri):" if lang == "uz" else "Результат (напрямую из данных):"
    lines = [head]
    for row in result.rows[:10]:
        lines.append("; ".join(f"{c}: {v}" for c, v in zip(result.columns, row)))
    return "\n".join(lines)


def _guess_language(question: str) -> str:
    return "ru" if re.search(r"[а-яё]", question, re.I) and not re.search(r"[qoʻ'‘ʼ]", question) else "uz"


def record_qa(ans: AgentAnswer, extra: dict | None = None, path: str = QA_LOG_PATH) -> None:
    """Append one JSON line per answered question (for later analysis); never raises."""
    if not path:
        return
    entry = {
        "ts": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "question": ans.question, "language": ans.language, "answerable": ans.answerable,
        "verified": ans.verified, "timed_out": ans.timed_out, "rows": len(ans.rows),
        "elapsed_sec": round(ans.elapsed_sec, 1), "sql": ans.sql, "interpretation": ans.interpretation,
        "answer": ans.answer, **(extra or {}),
    }
    try:
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        with open(path, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(entry, ensure_ascii=False) + "\n")
    except OSError:
        log.exception("could not write QA log")


class Agent:
    """One instance per process; `ask` is thread-safe (fresh DB connection per call)."""

    def __init__(
        self,
        con: sqlite3.Connection | None,
        llm: Llm,
        *,
        db_path: str | None = None,
        resolver: Resolver | None = None,
    ) -> None:
        if con is None and db_path is None:
            raise ValueError("Agent needs a connection or db_path")
        self.con = con
        self.db_path = db_path
        self.llm = llm
        self.resolver = resolver

    # -- plumbing -----------------------------------------------------------------------------
    def _connection(self) -> tuple[sqlite3.Connection, bool]:
        if self.db_path:
            return open_db(self.db_path), True
        assert self.con is not None
        return self.con, False

    def _plan(self, question: str, feedback: str | None, entities: str, history: list[Turn], deadline: float) -> dict:
        user = ""
        if history:
            user += "PREVIOUS TURNS:\n" + "\n".join(f"Q: {q}\nInterpretation: {i}" for q, i in history) + "\n\n"
        if entities:
            user += entities + "\n\n"
        user += f"QUESTION: {question}"
        if feedback:
            user += f"\n\nPREVIOUS ATTEMPT FAILED: {feedback}\nFix the SQL."
        resp = self.llm.complete(PLAN_SYSTEM, user, json_mode=True, deadline=deadline)
        return _parse_json(resp.text)

    def _query_with_retries(
        self, con: sqlite3.Connection, question: str, entities: str, history: list[Turn], deadline: float, debug: list[str]
    ) -> tuple[dict, QueryResult | None]:
        feedback = None
        plan: dict = {}
        for attempt in range(1, MAX_SQL_ATTEMPTS + 1):
            plan = self._plan(question, feedback, entities, history, deadline)
            debug.append(f"plan#{attempt}: {json.dumps(plan, ensure_ascii=False)[:800]}")
            if not plan.get("answerable", False) or not plan.get("sql"):
                return plan, None
            result = run_query(con, plan["sql"])
            if result.ok:
                return plan, result
            feedback = f"SQL error: {result.error}"
            debug.append(feedback)
        return plan, QueryResult(sql=plan.get("sql", ""), columns=[], rows=[], elapsed_sec=0, error="gave up")

    def _write_answer(self, question: str, plan: dict, result: QueryResult, note: str | None, deadline: float) -> str:
        payload = {
            "question": question, "language": plan.get("language", "ru"),
            "interpretation": plan.get("interpretation", ""), "sql": result.sql,
            "row_count": len(result.rows), "truncated": result.truncated,
            "rows": result.as_records(),
        }
        user = json.dumps(payload, ensure_ascii=False, default=str)
        if note:
            user += f"\n\nIMPORTANT: {note}"
        return self.llm.complete(ANSWER_SYSTEM, user, deadline=deadline).text.strip()

    def _resolve(self, question: str, debug: list[str]) -> str:
        if self.resolver is None:
            return ""
        try:
            block = self.resolver.resolve(question).prompt_block()  # type: ignore[attr-defined]
        except Exception:  # noqa: BLE001 - resolution is a helper, never a blocker
            log.exception("entity resolution failed")
            return ""
        if block:
            debug.append(block)
        return block

    # -- main entry ---------------------------------------------------------------------------
    def ask(self, question: str, history: list[Turn] | None = None) -> AgentAnswer:
        started = time.monotonic()
        deadline = started + START_BUDGET_SEC
        debug: list[str] = []
        con, owned = self._connection()
        try:
            return self._ask(con, question, list(history or [])[-HISTORY_TURNS:], started, deadline, debug)
        except LlmDeadline as exc:
            debug.append(str(exc))
            lang = _guess_language(question)
            return AgentAnswer(question, lang, _timeout_message(lang), "", None, [], [], True, False,
                               time.monotonic() - started, debug, timed_out=True)
        finally:
            if owned:
                con.close()

    def _ask(self, con: sqlite3.Connection, question: str, history: list[Turn], started: float, deadline: float,
             debug: list[str]) -> AgentAnswer:
        entities = self._resolve(question, debug)
        plan, result = self._query_with_retries(con, question, entities, history, deadline, debug)
        lang = plan.get("language", "ru")
        interpretation = plan.get("interpretation", "")
        if result is None:
            return AgentAnswer(question, lang, _no_data_message(lang, plan.get("reason", "")),
                               interpretation, None, [], [], False, True, time.monotonic() - started, debug)
        if not result.ok:
            msg = ("So'rovni tuza olmadim, iltimos savolni boshqacha ifodalang." if lang == "uz"
                   else "Не удалось построить запрос, пожалуйста, переформулируйте вопрос.")
            return AgentAnswer(question, lang, msg, interpretation, result.sql, [], [],
                               True, False, time.monotonic() - started, debug)

        note = None
        verified = False
        answer = ""
        context = f"{question}\n{result.sql}"
        for _ in range(MAX_ANSWER_ATTEMPTS):
            answer = self._write_answer(question, plan, result, note, deadline)
            check = verify_answer(answer, result.rows, context)
            debug.append(f"verify: ok={check.ok} unsupported={check.problems[:5]}")
            if check.ok:
                verified = True
                break
            note = (f"Your previous answer contained values not present in the rows: {check.problems[:5]}. "
                    "Rewrite using only values from the rows, copied exactly (names, codes, dates, numbers).")
        if not verified:
            answer = _fallback_answer(lang, result)
            verified = True
        return AgentAnswer(question, lang, answer, interpretation, result.sql, result.rows,
                           result.columns, True, verified, time.monotonic() - started, debug)
