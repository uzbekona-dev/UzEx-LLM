"""Agent behaviour with a scripted LLM: grounding retry, fallback, time budget, history, QA log."""

from __future__ import annotations

import json
import time

import pytest

from app import agent as agent_mod
from app.agent import Agent, record_qa
from app.llm import LlmDeadline, LlmResponse
from app.sql_guard import open_db
from app.verify import verify_answer

DB = "data/uzex.db"
pytestmark = pytest.mark.skipif(not __import__("os").path.exists(DB), reason="data/uzex.db not built")

PLAN = {"language": "uz", "answerable": True, "interpretation": "100001-bitim", "sql": "SELECT deal_no, seller_inn, buyer_inn, amount FROM deals WHERE deal_no = 100001"}


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


def test_answer_rewritten_then_fallback_when_unverifiable() -> None:
    llm = ScriptedLlm([json.dumps(PLAN), "Summa **999 999** so'm", "Summa **888 888** so'm"])
    ans = Agent(None, llm, db_path=DB).ask("100001-bitim summasi?")
    assert ans.answerable and ans.verified
    assert ans.answer.startswith("Natija")  # template fallback, nothing invented
    assert "not present in the rows" in llm.calls[2]


def test_time_budget_returns_timeout_message(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(agent_mod, "START_BUDGET_SEC", 0.05)
    llm = ScriptedLlm([json.dumps(PLAN), "x"], slow=0.1)
    ans = Agent(None, llm, db_path=DB).ask("100001-bitim summasi?")
    assert ans.timed_out and not ans.answerable is False
    assert "qayta yuboring" in ans.answer


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
