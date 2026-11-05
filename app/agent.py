"""Question -> SQL + answer template (one LLM call) -> rows filled in locally -> verified answer.

Privacy by construction (mode B):
  * the LLM never sees result rows; company names / INNs / broker codes in the question are replaced
    by placeholders before the call and substituted back into the SQL on this machine;
  * the LLM writes an answer *template* with {column} slots; numbers and names enter the text only
    from SQLite rows, so there is nothing to invent.
Safety nets: entity resolution in code -> SQL guard (read-only, timeout) -> template guard (no literal
numbers, only known columns) -> grounding verifier on the final text -> generic rendering fallback ->
overall time budget.
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

from app.entities import EntityResolver
from app.llm import Llm, LlmDeadline
from app.pseudonym import Masked, Pseudonymizer
from app.render import RenderSpec, check_template, render
from app.schema_prompt import RULES, SCHEMA_DOC
from app.sql_guard import QueryResult, open_db, run_query
from app.verify import verify_answer

log = logging.getLogger(__name__)

MAX_SQL_ATTEMPTS = 3
START_BUDGET_SEC = float(os.environ.get("ANSWER_BUDGET_SEC", "45"))  # no new LLM call after this (+40 s call timeout < 90 s)
HISTORY_TURNS = 2
SQL_CRITIC = os.environ.get("SQL_CRITIC", "1") not in ("0", "false", "no")

CRITIC_SYSTEM = f"""You review ONE SQLite query written for a question about exchange deals. You do not see data.
{SCHEMA_DOC}
Check ONLY these points and answer with JSON {{"ok": true|false, "issues": ["..."], "fixed_sql": "<full corrected SQL or empty>", "interpretation": "<corrected one-sentence interpretation in the question's language, or empty>"}}:
1. "sold / traded / volume / turnover" questions must have is_cancelled = 0; "how many deals" (count) must NOT filter cancelled unless asked. All aggregates in one query use the same cancelled filter.
2. Volumes summed only within one unit (GROUP BY unit); amounts only in one currency (amount_uzs or GROUP BY currency).
3. A broker is counted once per deal (COUNT(DISTINCT deal_no) / UNION, never UNION ALL) and on both sides unless a side is named.
4. deals.region is the SELLER warehouse region; a buyer's region must come from participants.region joined on buyer_inn.
5. Period: year/month columns or deal_date match the question; relative periods are relative to 2026-10-30; a number after shartnoma/договор is contracts.contract_no, after bitim/сделка it is deals.deal_no.
6. Product filtered by tnved; grade/class via sort_no/class_no when asked; "average price" returns both AVG(unit_price) and SUM(amount)/SUM(volume).
7. Placeholders {{C1_INNS}} {{INN1}} {{B1}} must stay exactly as written.
If the SQL is acceptable, return ok=true and empty fixed_sql. If you fix it, keep the SAME column aliases (the answer template depends on them) and keep it a single SELECT with LIMIT."""
QA_LOG_PATH = os.environ.get("QA_LOG", "logs/qa.jsonl")

TEMPLATE_RULES = """
ANSWER TEMPLATE (field "render") — you never see the data, so you write a template and the server fills it:
  {col}       value of a column from YOUR SELECT (numbers are formatted by the server: 1 234 567.89)
  {col:t}     kilograms -> tonnes (÷1000) — use when the user asked in tonnes: "{v:t} tonna ({v} kg)"
  {col:int}   whole number;  {col:date}  DD.MM.YYYY;  {row_count}  number of result rows
  {C1} {B1} {INN1}  the placeholders from the question (the server restores the user's wording)
  headline: 1-2 full sentences for the FIRST row (or for the single aggregate row). Put ** around the 1-2 key figures asked for.
  line:     one line per row when several rows are expected (rankings, several companies, per-year): "{name} ({inn}) — **{total} ta** bitim"
  empty:    what to say when the SQL returns no rows (be specific: which product/company/period was not found)
  note:     one short sentence with assumptions (cancelled excluded, which price formula, period). Empty if none.
  Alias every selected column with a descriptive snake_case name and use exactly those names in the template.
  NEVER put digits, company names, product names you were not given, or any value in the template — only slots.
  Units/currency/status words from the data (тонна, Узбекский сум, Исполнен) are translated by the server; just place the slot: "{amount} {currency}".
  Write the template in the language of the question; Uzbek in Latin script; natural, friendly, complete sentences; no greetings.
  Translate "{row_count}" wording correctly: uz "{row_count} ta", ru "{row_count}".

EXAMPLES
Q: "2024-yilda qancha tonna paxta xomashyosi sotilgan?"
{"language":"uz","answerable":true,"interpretation":"2024-yilda paxta xomashyosi (TN VED 520100) bo'yicha bekor qilinmagan bitimlar hajmi; hajm = miqdor × lot.",
 "sql":"SELECT unit, SUM(volume) AS total_volume, COUNT(*) AS deal_count, SUM(amount_uzs) AS total_amount_uzs FROM deals WHERE tnved = '520100' AND year = 2024 AND is_cancelled = 0 GROUP BY unit",
 "render":{"headline":"2024-yilda jami **{total_volume:t} tonna** ({total_volume} {unit}) paxta xomashyosi sotilgan — **{deal_count} ta** bitim, umumiy summasi {total_amount_uzs} so'm.",
           "line":"", "empty":"2024-yilda paxta xomashyosi bo'yicha bajarilgan bitim topilmadi.",
           "note":"Bekor qilingan bitimlar hisobga olinmadi."}}
Q: "Кто покупатель и продавец по сделке 100001?"
{"language":"ru","answerable":true,"interpretation":"Данные сделки № 100001: продавец, покупатель, товар, объём, сумма, статус.",
 "sql":"SELECT d.deal_no, d.deal_date, d.product_canon_ru AS product, d.volume, d.unit, d.amount, d.currency, d.status, d.seller_inn, ps.name AS seller_name, d.buyer_inn, pb.name AS buyer_name FROM deals d LEFT JOIN participants ps ON ps.inn = d.seller_inn LEFT JOIN participants pb ON pb.inn = d.buyer_inn WHERE d.deal_no = 100001",
 "render":{"headline":"По сделке № {deal_no} от {deal_date:date} продавец — **{seller_name}** (ИНН {seller_inn}), покупатель — **{buyer_name}** (ИНН {buyer_inn}). Товар: {product}, объём {volume} {unit}, сумма {amount} {currency}, статус «{status}».",
           "line":"", "empty":"Сделки с номером 100001 в данных нет (в нумерации есть пропуски).", "note":""}}
Q: "2025-yil top-5 broker"
{"language":"uz","answerable":true,"interpretation":"2025-yilda sotuvchi yoki xaridor tomonida qatnashgan bitimlar soni bo'yicha 5 ta yetakchi broker (har bitim bir marta).",
 "sql":"WITH bd AS (SELECT seller_broker AS code, deal_no FROM deals WHERE year = 2025 UNION SELECT buyer_broker, deal_no FROM deals WHERE year = 2025) SELECT b.code, b.name, COUNT(*) AS deal_count FROM bd JOIN brokers b ON b.code = bd.code GROUP BY b.code, b.name ORDER BY deal_count DESC LIMIT 5",
 "render":{"headline":"2025-yilda eng ko'p bitim tuzgan brokerlar:", "line":"{code} — {name}: **{deal_count} ta** bitim",
           "empty":"2025-yil uchun broker bitimlari topilmadi.", "note":"Broker sotuvchi yoki xaridor tomonida qatnashgan bitimlar hisoblandi, har bitim bir marta."}}
Q: "Сколько сделок у компании {C1}?"   (placeholder legend says {C1} matched 2 participants)
{"language":"ru","answerable":true,"interpretation":"Число сделок компании {C1} (найдено несколько участников с таким названием) как продавца и как покупателя, все статусы.",
 "sql":"SELECT p.inn, p.name, COUNT(d.deal_no) AS total_deals, SUM(CASE WHEN d.seller_inn = p.inn THEN 1 ELSE 0 END) AS as_seller, SUM(CASE WHEN d.buyer_inn = p.inn THEN 1 ELSE 0 END) AS as_buyer FROM participants p LEFT JOIN deals d ON d.seller_inn = p.inn OR d.buyer_inn = p.inn WHERE p.inn IN ({C1_INNS}) GROUP BY p.inn, p.name",
 "render":{"headline":"По названию «{C1}» найдено {row_count} компании:", "line":"{name} (ИНН {inn}) — **{total_deals}** сделок: {as_seller} как продавец, {as_buyer} как покупатель",
           "empty":"Компания «{C1}» в данных не найдена.", "note":"Учтены сделки во всех статусах."}}
Q: "Кто директор компании с ИНН {INN1}?"
{"language":"ru","answerable":false,"reason":"В данных нет сведений о руководителях компаний (есть только ИНН, название, регион, вид деятельности).","interpretation":"Запрошен руководитель компании {INN1} — таких данных нет.","sql":"","render":{}}
"""

PLAN_SYSTEM = f"""You translate questions about exchange deals (Russian or Uzbek) into SQLite SQL and an answer template.
{SCHEMA_DOC}
{RULES}
{TEMPLATE_RULES}
If PLACEHOLDERS are given, write the tokens literally in SQL ({{C1_INNS}}, {{INN1}}, {{B1}}, {{C1_KEY}}); if the entity named
was not matched, prefer answerable=false and say which name was not found. If PREVIOUS TURNS are given, treat a short
follow-up ("and in 2023?", "va xaridlari-chi?") as the previous question with that change applied.
Respond ONLY with JSON:
{{"language": "ru" | "uz", "answerable": true|false, "reason": "<why not, if false>",
  "interpretation": "<one short sentence IN THE LANGUAGE OF THE QUESTION (uz = Latin script), for the end user: how you understood it, incl. assumptions (period, product, cancelled excluded, formula used e.g. volume = quantity x lot). No column names.>",
  "sql": "<single SELECT>",
  "render": {{"headline": "...", "line": "...", "empty": "...", "note": "..."}} }}
"""


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
    used_template: bool = True


Turn = tuple[str, str]  # (question, interpretation)


class PlanError(ValueError):
    """The model reply was not usable JSON; the planner loop retries with feedback."""


# a backslash that does not start a valid JSON escape (e.g. "\u12" or "C:\path") -> doubled
_BAD_ESCAPE_RE = re.compile(r"\\(?![\\/\"bfnrt]|u[0-9a-fA-F]{4})")


def _parse_json(text: str) -> dict:
    text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text.strip(), flags=re.I)
    start, end = text.find("{"), text.rfind("}")
    if start >= 0 and end > start:
        text = text[start:end + 1]
    for candidate in (text, _BAD_ESCAPE_RE.sub(r"\\\\", text)):  # second try: repair bad escapes
        try:
            data = json.loads(candidate)
        except json.JSONDecodeError:
            continue
        if isinstance(data, dict):
            return data
    raise PlanError("reply is not a JSON object")


def _no_data_message(lang: str, reason: str) -> str:
    if lang == "uz":
        return f"Ma'lumotlarda bu savolga javob yo'q. {reason}".strip()
    return f"В данных нет ответа на этот вопрос. {reason}".strip()


def _timeout_message(lang: str) -> str:
    if lang == "uz":
        return "Kechirasiz, javobni vaqtida tayyorlay olmadim (model javob bermadi). Iltimos, savolni qayta yuboring."
    return "Извините, не успел подготовить ответ (модель не ответила вовремя). Пожалуйста, отправьте вопрос ещё раз."


def _guess_language(question: str) -> str:
    return "ru" if re.search(r"[а-яё]", question, re.I) and not re.search(r"[qoʻ'‘ʼ]", question) else "uz"


def record_qa(ans: AgentAnswer, extra: dict | None = None, path: str = QA_LOG_PATH) -> None:
    """Append one JSON line per answered question (for later analysis); never raises."""
    if not path:
        return
    entry = {
        "ts": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "question": ans.question, "language": ans.language, "answerable": ans.answerable,
        "verified": ans.verified, "timed_out": ans.timed_out, "used_template": ans.used_template,
        "rows": len(ans.rows), "elapsed_sec": round(ans.elapsed_sec, 1), "sql": ans.sql,
        "interpretation": ans.interpretation, "answer": ans.answer, **(extra or {}),
    }
    try:
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        with open(path, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(entry, ensure_ascii=False) + "\n")
    except OSError:
        log.exception("could not write QA log")


_TONNE_ASKED_RE = re.compile(r"\b(tonna\w*|tonn\w*|тонн\w*|тонна\w*)\b", re.I)


def _tonne_problems(question: str, spec: RenderSpec, result: QueryResult) -> list[str]:
    """User asked in tonnes but the volume is in kilograms and the template prints raw kg only."""
    if not _TONNE_ASKED_RE.search(question) or not result.rows:
        return []
    kg_columns = [c for c in result.columns if c.lower() in ("unit", "unit_name")]
    has_kg = any(dict(zip(result.columns, r)).get(c) == "килограмм" for r in result.rows for c in kg_columns)
    if not has_kg or ":t}" in "".join(spec.texts()):
        return []
    return ["the user asked in tonnes and the unit is kilogram: show the volume as {volume_column:t} tonna ({volume_column} kg)"]


_EXCLUDES_CANCELLED_RE = re.compile(r"is_cancelled\s*=\s*0", re.I)
_AGGREGATE_RE = re.compile(r"\b(SUM|COUNT|AVG)\s*\(", re.I)


def _cancelled_problems(sql: str, spec: RenderSpec, result: QueryResult) -> list[str]:
    """An aggregate that silently drops cancelled deals must also report how many were dropped (rule 7)."""
    if not result.rows or not _EXCLUDES_CANCELLED_RE.search(sql) or not _AGGREGATE_RE.search(sql):
        return []
    if any("cancel" in c.lower() for c in result.columns):
        if any("cancel" in t for t in spec.texts()):
            return []
        return ["the cancelled-deals column is selected but not shown: add it to the note, e.g. '{cancelled_deals} ta bitim bekor qilingan'"]
    return ["the sums exclude cancelled deals: also return the cancelled count as a column (e.g. "
            "(SELECT COUNT(*) FROM deals WHERE <same filters> AND is_cancelled = 1) AS cancelled_deals) and show it in the note"]


class _NullMasked:
    """Used when no resolver is configured: nothing is masked."""

    def __init__(self, question: str) -> None:
        self.question = question
        self.entity_block = ""
        self.leaked: list[str] = []

    def substitute_sql(self, sql: str) -> str:
        return sql

    def unmask(self, text: str) -> str:
        return text


class Agent:
    """One instance per process; `ask` is thread-safe (fresh DB connection per call)."""

    def __init__(
        self,
        con: sqlite3.Connection | None,
        llm: Llm,
        *,
        db_path: str | None = None,
        resolver: EntityResolver | None = None,
    ) -> None:
        if con is None and db_path is None:
            raise ValueError("Agent needs a connection or db_path")
        self.con = con
        self.db_path = db_path
        self.llm = llm
        self.resolver = resolver
        self.pseudonymizer = Pseudonymizer(resolver) if resolver else None

    # -- plumbing -----------------------------------------------------------------------------
    def _connection(self) -> tuple[sqlite3.Connection, bool]:
        if self.db_path:
            return open_db(self.db_path), True
        assert self.con is not None
        return self.con, False

    def _mask(self, question: str, debug: list[str]) -> Masked | _NullMasked:
        if not self.resolver or not self.pseudonymizer:
            return _NullMasked(question)
        try:
            resolution = self.resolver.resolve(question)
            masked = self.pseudonymizer.mask(question, resolution)
        except Exception:  # noqa: BLE001 - never block an answer on the helper
            log.exception("entity resolution failed")
            return _NullMasked(question)
        products = resolution.prompt_block()
        if products:
            products = "\n".join(l for l in products.splitlines() if l.startswith("- products") or l.startswith("- 6+"))
        block = "\n".join(b for b in (masked.entity_block, products and "RESOLVED: " + products) if b)
        masked = Masked(masked.question, block, masked.mapping, masked.inns, masked.companies, masked.unmatched, masked.leaked)
        debug.append(f"masked: {masked.question}")
        if block:
            debug.append(block)
        if masked.leaked:
            log.warning("could not mask phrase(s) %s", masked.leaked)
        return masked

    def _plan(self, masked: Masked | _NullMasked, feedback: str | None, history: list[Turn], deadline: float) -> dict:
        user = ""
        if history:
            user += "PREVIOUS TURNS:\n" + "\n".join(f"Q: {q}\nInterpretation: {i}" for q, i in history) + "\n\n"
        if masked.entity_block:
            user += masked.entity_block + "\n\n"
        user += f"QUESTION: {masked.question}"
        if feedback:
            user += f"\n\nPREVIOUS ATTEMPT FAILED: {feedback}\nFix it."
        resp = self.llm.complete(PLAN_SYSTEM, user, json_mode=True, deadline=deadline)
        return _parse_json(resp.text)

    def _plan_and_query(
        self, con: sqlite3.Connection, masked: Masked | _NullMasked, history: list[Turn], deadline: float, debug: list[str]
    ) -> tuple[dict, QueryResult | None, RenderSpec]:
        feedback = None
        plan: dict = {}
        spec = RenderSpec()
        for attempt in range(1, MAX_SQL_ATTEMPTS + 1):
            try:
                plan = self._plan(masked, feedback, history, deadline)
            except PlanError as exc:
                feedback = f"{exc}. Reply with ONE valid JSON object only."
                debug.append(feedback)
                continue
            debug.append(f"plan#{attempt}: {json.dumps(plan, ensure_ascii=False)[:1200]}")
            if not plan.get("answerable", False) or not plan.get("sql"):
                return plan, None, spec
            sql = masked.substitute_sql(str(plan["sql"]))
            result = run_query(con, sql)
            if not result.ok:
                feedback = f"SQL error: {result.error}"
                debug.append(feedback)
                continue
            spec = RenderSpec.from_plan(plan.get("render"))
            problems = check_template(spec, result.columns, f"{masked.question}\n{plan['sql']}")
            problems += _tonne_problems(masked.question, spec, result)
            problems += _cancelled_problems(str(plan["sql"]), spec, result)
            if problems and attempt < MAX_SQL_ATTEMPTS:
                feedback = f"Template problems: {problems}. Columns available: {result.columns}. Use only slots, no literal values."
                debug.append(feedback)
                continue
            if SQL_CRITIC:
                plan, result = self._criticise(con, masked, plan, result, deadline, debug)
            return plan, result, spec
        return plan, QueryResult(sql=plan.get("sql", ""), columns=[], rows=[], elapsed_sec=0, error="gave up"), spec

    def _criticise(self, con: sqlite3.Connection, masked: Masked | _NullMasked, plan: dict, result: QueryResult,
                   deadline: float, debug: list[str]) -> tuple[dict, QueryResult]:
        """Second opinion on the SQL logic only; a fix is accepted only if it runs and keeps the column aliases."""
        user = (f"QUESTION: {masked.question}\nINTERPRETATION: {plan.get('interpretation', '')}\n"
                f"SQL:\n{plan['sql']}\nRESULT COLUMNS: {result.columns}  ROWS RETURNED: {len(result.rows)}")
        try:
            verdict = _parse_json(self.llm.complete(CRITIC_SYSTEM, user, json_mode=True, deadline=deadline).text)
        except (PlanError, LlmDeadline) as exc:
            debug.append(f"critic skipped: {exc}")
            return plan, result
        debug.append(f"critic: {json.dumps(verdict, ensure_ascii=False)[:600]}")
        fixed = str(verdict.get("fixed_sql") or "").strip()
        if verdict.get("ok", True) or not fixed or fixed == plan["sql"]:
            return plan, result
        new_result = run_query(con, masked.substitute_sql(fixed))
        if not new_result.ok or set(new_result.columns) != set(result.columns):
            debug.append("critic fix rejected (error or different columns)")
            return plan, result
        new_plan = {**plan, "sql": fixed}
        if verdict.get("interpretation"):
            new_plan["interpretation"] = str(verdict["interpretation"])
        return new_plan, new_result

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
        masked = self._mask(question, debug)
        plan, result, spec = self._plan_and_query(con, masked, history, deadline, debug)
        lang = plan.get("language") or _guess_language(question)
        interpretation = masked.unmask(str(plan.get("interpretation", "")))
        if result is None:
            reason = masked.unmask(str(plan.get("reason", "")))
            return AgentAnswer(question, lang, _no_data_message(lang, reason), interpretation, None, [], [],
                               False, True, time.monotonic() - started, debug)
        if not result.ok:
            msg = ("So'rovni tuza olmadim, iltimos savolni boshqacha ifodalang." if lang == "uz"
                   else "Не удалось построить запрос, пожалуйста, переформулируйте вопрос.")
            return AgentAnswer(question, lang, msg, interpretation, result.sql, [], [],
                               True, False, time.monotonic() - started, debug)

        rendered = render(spec, result.columns, result.rows, lang, f"{masked.question}\n{result.sql}")
        answer = masked.unmask(rendered.text)
        debug.append(f"render: template={rendered.used_template} problems={rendered.problems}")
        check = verify_answer(answer, result.rows, f"{question}\n{result.sql}")
        debug.append(f"verify: ok={check.ok} unsupported={check.problems[:5]}")
        used_template = rendered.used_template
        if not check.ok and used_template:  # belt and braces: never ship unverified prose
            from app.render import render_generic
            answer = render_generic(result.columns, result.rows, lang)
            used_template = False
        return AgentAnswer(question, lang, answer, interpretation, result.sql, result.rows, result.columns,
                           True, True, time.monotonic() - started, debug, used_template=used_template)
