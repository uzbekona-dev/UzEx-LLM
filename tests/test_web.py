"""Offline tests for web.py: FastAPI endpoints with a fake agent (no LLM, no DB)."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

import web
from app.agent import AgentAnswer


class _FakeLlm:
    model = "fake:test-model"


class _FakeAgent:
    llm = _FakeLlm()

    def __init__(self) -> None:
        self.calls: list[tuple[str, list[tuple[str, str]]]] = []

    def ask(self, question: str, history: list[tuple[str, str]] | None = None) -> AgentAnswer:
        self.calls.append((question, list(history or [])))
        return AgentAnswer(
            question=question, language="ru", answer="Курс доллара на 15.06.2024 — **11 862.46** сум.",
            interpretation="Курс USD на дату 15.06.2024 <из таблицы usd_rates>",
            sql="SELECT rate FROM usd_rates WHERE rate_date = '2024-06-15'",
            rows=[(11862.46,)], columns=["rate"], answerable=True, verified=True, elapsed_sec=3.14159,
        )


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch, tmp_path) -> TestClient:
    fake = _FakeAgent()
    monkeypatch.setattr(web, "agent", fake)
    monkeypatch.setattr(web, "history", web.ChatHistory())
    monkeypatch.setattr(web, "_in_flight", set())
    monkeypatch.setattr(web, "record_qa", lambda ans, extra=None: None)
    with TestClient(web.app) as c:
        c.fake = fake  # type: ignore[attr-defined]
        yield c


def test_index_serves_html(client: TestClient) -> None:
    res = client.get("/")
    assert res.status_code == 200
    assert res.headers["content-type"].startswith("text/html")
    assert "AI-yordamchi" in res.text and "AI-ассистент" in res.text
    assert "/api/ask" in res.text


def test_health_reports_model(client: TestClient) -> None:
    res = client.get("/api/health")
    assert res.status_code == 200
    assert res.json() == {"status": "ok", "model": "fake:test-model"}


def test_ask_returns_answer_fields(client: TestClient) -> None:
    res = client.post("/api/ask", json={"question": "15.06.2024 dollar kursi", "session": "s1"})
    assert res.status_code == 200
    body = res.json()
    for key in ("answer_html", "interpretation", "sql", "rows", "row_count", "elapsed_sec", "answerable", "verified", "language"):
        assert key in body, key
    assert "<b>11 862.46</b>" in body["answer_html"]
    assert "**" not in body["answer_html"]
    assert "&lt;из таблицы usd_rates&gt;" in body["interpretation"]  # escaped for innerHTML
    assert body["rows"] == [[11862.46]] and body["row_count"] == 1
    assert body["elapsed_sec"] == 3.1
    assert body["language"] == "ru" and body["verified"] is True and body["answerable"] is True
    assert body["labels"]["verified"] == "По данным биржи"


def test_history_is_kept_per_session(client: TestClient) -> None:
    client.post("/api/ask", json={"question": "q1", "session": "a"})
    client.post("/api/ask", json={"question": "q2", "session": "a"})
    client.post("/api/ask", json={"question": "q3", "session": "b"})
    calls = client.fake.calls  # type: ignore[attr-defined]
    assert calls[0] == ("q1", [])
    assert calls[1][1] == [("q1", "Курс USD на дату 15.06.2024 <из таблицы usd_rates>")]
    assert calls[2] == ("q3", [])  # other session starts clean


def test_empty_question_rejected(client: TestClient) -> None:
    assert client.post("/api/ask", json={"question": "   ", "session": "s"}).status_code == 400
    assert client.post("/api/ask", json={"session": "s"}).status_code == 422


def test_too_long_question_rejected(client: TestClient) -> None:
    res = client.post("/api/ask", json={"question": "x" * 501, "session": "s"})
    assert res.status_code == 400
    assert "500" in res.json()["detail"]


def test_missing_session_rejected(client: TestClient) -> None:
    assert client.post("/api/ask", json={"question": "q", "session": ""}).status_code == 400


def test_second_in_flight_question_is_429(client: TestClient) -> None:
    web._in_flight.add("busy")
    res = client.post("/api/ask", json={"question": "q", "session": "busy"})
    assert res.status_code == 429


def test_agent_failure_is_500_and_releases_session(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    def boom(question: str, history: list | None = None) -> AgentAnswer:
        raise RuntimeError("llm down")

    monkeypatch.setattr(client.fake, "ask", boom)  # type: ignore[attr-defined]
    res = client.post("/api/ask", json={"question": "q", "session": "s"})
    assert res.status_code == 500
    assert "s" not in web._in_flight


def test_record_qa_gets_web_channel(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    seen: list[dict] = []
    monkeypatch.setattr(web, "record_qa", lambda ans, extra=None: seen.append(extra or {}))
    client.post("/api/ask", json={"question": "q", "session": "sess-42"})
    assert seen == [{"channel": "web", "session": "sess-42"}]


def test_health_without_agent_is_503(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(web, "agent", None)
    client = TestClient(web.app)  # no lifespan -> agent stays None
    assert client.get("/api/health").status_code == 503
