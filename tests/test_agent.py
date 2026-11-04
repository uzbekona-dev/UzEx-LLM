"""Agent behaviour with a scripted LLM: template rendering, guards, time budget, history, QA log, masking."""

from __future__ import annotations

import json
import os
import time

import pytest

from app import agent as agent_mod
from app.agent import Agent, record_qa
from app.entities import EntityResolver
from app.llm import LlmDeadline, LlmResponse
from app.sql_guard import open_db
from app.verify import verify_answer

DB = os.environ.get("DB_PATH", "data/uzex.db")
pytestmark = pytest.mark.skipif(not os.path.exists(DB), reason="data/uzex.db not built")

SQL_100001 = ("SELECT d.deal_no, d.seller_inn, ps.name AS seller_name, d.buyer_inn, pb.name AS buyer_name, d.amount, d.currency "
              "FROM deals d LEFT JOIN participants ps ON ps.inn = d.seller_inn LEFT JOIN participants pb ON pb.inn = d.buyer_inn "
              "WHERE d.deal_no = 100001")
PLAN = {
    "language": "uz", "answerable": True, "interpretation": "100001-bitim ma'lumotlari", "sql": SQL_100001,
    "render": {"headline": "{deal_no}-bitim: sotuvchi **{seller_name}** ({seller_inn}), xaridor **{buyer_name}** ({buyer_inn}), summa {amount} {currency}.",
               "line": "", "empty": "Bunday bitim yo'q.", "note": ""},
}


class ScriptedLlm:
    """Returns canned replies in order; records prompts; honours `deadline` like the real client."""

    model = "fake:test"
    models = ["fake:test"]

    def __init__(self, replies: list[str], *, slow: float = 0.0) -> None:
        self.replies = list(replies)
        self.calls: list[str] = []
        self.slow = slow

    def complete(self, system: str, user: str, *, temperature: float = 0.0, json_mode: bool = False, deadline: float | None = None) -> LlmResponse:
        if deadline is not None and time.monotonic() > deadline:
            raise LlmDeadline("budget exhausted")
        self.calls.append(user)
        time.sleep(self.slow)
        return LlmResponse(text=self.replies.pop(0), input_tokens=0, output_tokens=0)


@pytest.fixture(autouse=True)
def no_critic(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(agent_mod, "SQL_CRITIC", False)  # scripted replies below do not include a critic verdict


@pytest.fixture(scope="module")
def resolver() -> EntityResolver:
    return EntityResolver(open_db(DB))


def test_verifier_catches_wrong_name_and_code() -> None:
    rows = [(100001, "RUKUSHO‘ FERMER MCHJ", "BK060", "2022-01-03")]
    bad = 'Sotuvchi "Yangi Servis" MChJ, broker BK099, sana 05.01.2022'
    assert verify_answer(bad, rows, "q").problems == ["BK099", "05.01.2022", "Yangi Servis"]
    good = "Sotuvchi RUKUSHO‘ FERMER MCHJ (BK060), 03.01.2022"
    assert verify_answer(good, rows, "q").ok


def test_verifier_scaling_needs_scale_word() -> None:
    rows = [(1672494955.0,)]
    assert verify_answer("1 672 494.96 tonna (1 672 494 955 kg)", rows, "q").ok  # kg->tonne allowed
    assert verify_answer("1.67 mlrd kg", rows, "q").ok
    assert verify_answer("1.67 kg", rows, "q").ok is False


def test_template_is_filled_from_rows_only() -> None:
    llm = ScriptedLlm([json.dumps(PLAN)])
    ans = Agent(None, llm, db_path=DB).ask("100001-bitim kim bilan kim o'rtasida?")
    assert ans.answerable and ans.verified and ans.used_template
    assert "RUKUSHO‘ FERMER MCHJ" in ans.answer and "921912462" in ans.answer and "304 547 938.4 so'm" in ans.answer
    assert len(llm.calls) == 1  # single LLM call: no prose-writing step


def test_template_with_literal_number_is_rejected_then_generic() -> None:
    bad = {**PLAN, "render": {"headline": "Summa 999 999 so'm, {amount}"}}
    llm = ScriptedLlm([json.dumps(bad), json.dumps(bad), json.dumps(bad)])
    ans = Agent(None, llm, db_path=DB).ask("100001-bitim summasi?")
    assert ans.verified and not ans.used_template
    assert "Natija" in ans.answer[:12] and "999" not in ans.answer
    assert "Template problems" in llm.calls[1]


def test_rows_never_reach_the_llm(resolver: EntityResolver) -> None:
    llm = ScriptedLlm([json.dumps(PLAN)])
    Agent(None, llm, db_path=DB, resolver=resolver).ask('"Bo‘juk Servis" MChJ bilan 100001-bitim?')
    prompt = llm.calls[0]
    assert "Bo‘juk Servis" not in prompt and "978906167" not in prompt and "{C1}" in prompt


def test_placeholders_substituted_in_sql(resolver: EntityResolver) -> None:
    plan = {"language": "ru", "answerable": True, "interpretation": "сделки {C1}",
            "sql": "SELECT p.inn, p.name, COUNT(d.deal_no) AS total_deals FROM participants p LEFT JOIN deals d ON d.buyer_inn = p.inn WHERE p.inn IN ({C1_INNS}) GROUP BY p.inn, p.name",
            "render": {"headline": "По «{C1}» найдено {row_count} компании:", "line": "{name} ({inn}) — **{total_deals}** сделок"}}
    llm = ScriptedLlm([json.dumps(plan)])
    ans = Agent(None, llm, db_path=DB, resolver=resolver).ask("Сколько сделок у компании Qojo Invest?")
    assert ans.used_template and "915861525" in ans.sql and "{C1" not in ans.sql
    assert "По «Qojo Invest» найдено 2 компании" in ans.answer and "сделки Qojo Invest" == ans.interpretation


def test_time_budget_returns_timeout_message(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(agent_mod, "START_BUDGET_SEC", 0.05)
    llm = ScriptedLlm([json.dumps(PLAN), "x"], slow=0.1)
    ans = Agent(None, llm, db_path=DB).ask("100001-bitim summasi?")
    assert ans.timed_out is False or "qayta yuboring" in ans.answer  # first call allowed, budget then hit on retry only
    monkeypatch.setattr(agent_mod, "START_BUDGET_SEC", -1)
    ans = Agent(None, llm, db_path=DB).ask("100001-bitim summasi?")
    assert ans.timed_out and "qayta yuboring" in ans.answer


def test_history_is_passed_to_planner() -> None:
    llm = ScriptedLlm([json.dumps({**PLAN, "answerable": False, "reason": "x"})])
    Agent(None, llm, db_path=DB).ask("va 2023-da?", history=[("2024-da paxta?", "2024, 520100")])
    assert "PREVIOUS TURNS" in llm.calls[0] and "2024-da paxta?" in llm.calls[0]


def test_record_qa_writes_jsonl(tmp_path) -> None:
    llm = ScriptedLlm([json.dumps({**PLAN, "answerable": False, "reason": "yo'q"})])
    ans = Agent(None, llm, db_path=DB).ask("direktor kim?")
    path = tmp_path / "qa.jsonl"
    record_qa(ans, {"chat_id": 1}, path=str(path))
    entry = json.loads(path.read_text(encoding="utf-8").splitlines()[0])
    assert entry["question"] == "direktor kim?" and entry["answerable"] is False and entry["chat_id"] == 1


def test_critic_fix_is_applied_only_when_it_runs_with_same_columns(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(agent_mod, "SQL_CRITIC", True)
    fixed = SQL_100001.replace("d.deal_no = 100001", "d.deal_no = 100001 AND d.is_cancelled = 0")
    verdict = {"ok": False, "issues": ["x"], "fixed_sql": fixed, "interpretation": "tuzatilgan talqin"}
    llm = ScriptedLlm([json.dumps(PLAN), json.dumps(verdict)])
    ans = Agent(None, llm, db_path=DB).ask("100001-bitim?")
    assert "is_cancelled = 0" in ans.sql and ans.interpretation == "tuzatilgan talqin" and ans.used_template
    bad_verdict = {"ok": False, "fixed_sql": "SELECT 1 AS other_col"}
    llm = ScriptedLlm([json.dumps(PLAN), json.dumps(bad_verdict)])
    ans = Agent(None, llm, db_path=DB).ask("100001-bitim?")
    assert "other_col" not in ans.sql and ans.used_template  # rejected: different columns


def test_tonne_question_with_kg_template_is_sent_back() -> None:
    sql = "SELECT unit, SUM(volume) AS total_volume FROM deals WHERE tnved = '520100' AND year = 2024 AND is_cancelled = 0 GROUP BY unit"
    kg_plan = {"language": "uz", "answerable": True, "interpretation": "x", "sql": sql,
               "render": {"headline": "Jami **{total_volume} {unit}**"}}
    t_plan = {**kg_plan, "render": {"headline": "Jami **{total_volume:t} tonna** ({total_volume} {unit})"}}
    llm = ScriptedLlm([json.dumps(kg_plan), json.dumps(t_plan)])
    ans = Agent(None, llm, db_path=DB).ask("2024-yilda qancha tonna paxta sotilgan?")
    assert "1 672 494.96 tonna" in ans.answer and "asked in tonnes" in llm.calls[1]
