"""Minimal web UI for the UZEX deals agent (FastAPI):

    python -X utf8 -m uvicorn web:app --host 0.0.0.0 --port 8080

GET  /            static page web/index.html (vanilla JS, no build step)
POST /api/ask     {"question": str, "session": str} -> answer + basis (interpretation, SQL, rows)
GET  /api/health  {"status": "ok", "model": "<provider:model>"}

Same Agent as bot.py; the answer HTML comes from app.format so numbers / bold markers look identical.
"""

from __future__ import annotations

import asyncio
import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel

from app.agent import Agent, AgentAnswer, record_qa
from app.entities import EntityResolver
from app.format import LABELS, answer_html, escape_html
from app.history import ChatHistory
from app.llm import Llm
from app.sql_guard import open_db

load_dotenv()
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log = logging.getLogger("web")

MAX_QUESTION_CHARS = 500
MAX_SESSION_CHARS = 64
INDEX_HTML = Path(__file__).resolve().parent / "web" / "index.html"
ERROR_MSG = (
    "Texnik xatolik yuz berdi, iltimos bir ozdan keyin qayta urinib ko'ring. / "
    "Произошла техническая ошибка, попробуйте ещё раз через минуту."
)
BUSY_MSG = "Oldingi savolga javob kutilmoqda. / Дождитесь ответа на предыдущий вопрос."

agent: Agent | None = None  # built on startup; tests replace it with a fake
history: ChatHistory[str] = ChatHistory()
_in_flight: set[str] = set()  # sessions with a question being answered right now


class AskRequest(BaseModel):
    question: str
    session: str


def build_agent() -> Agent:
    db_path = os.environ.get("DB_PATH", "data/uzex.db")
    return Agent(None, Llm(), db_path=db_path, resolver=EntityResolver(open_db(db_path)))


def _get_agent() -> Agent:
    if agent is None:
        raise HTTPException(status_code=503, detail="agent is not ready")
    return agent


def answer_payload(ans: AgentAnswer) -> dict[str, Any]:
    """JSON view of an AgentAnswer; text formatting is delegated to app.format."""
    labels = LABELS["uz" if ans.language == "uz" else "ru"]
    return {
        "answer_html": answer_html(ans.answer),
        "interpretation": escape_html(ans.interpretation),
        "sql": ans.sql or "",
        "columns": list(ans.columns),
        "rows": [list(r) for r in ans.rows],
        "row_count": len(ans.rows),
        "elapsed_sec": round(ans.elapsed_sec, 1),
        "answerable": ans.answerable,
        "verified": ans.verified,
        "timed_out": ans.timed_out,
        "language": ans.language,
        "labels": labels,
    }


def validate_request(req: AskRequest) -> tuple[str, str]:
    question = req.question.strip()
    session = req.session.strip()
    if not question:
        raise HTTPException(status_code=400, detail="question is empty")
    if len(question) > MAX_QUESTION_CHARS:
        raise HTTPException(status_code=400, detail=f"question is longer than {MAX_QUESTION_CHARS} characters")
    if not session or len(session) > MAX_SESSION_CHARS:
        raise HTTPException(status_code=400, detail="session id is missing or too long")
    return question, session


@asynccontextmanager
async def lifespan(_: FastAPI):
    global agent
    if agent is None:
        agent = build_agent()
        log.info("web started, model=%s", agent.llm.model)
    yield


app = FastAPI(title="UZEX deals agent", lifespan=lifespan)


@app.get("/")
async def index() -> FileResponse:
    return FileResponse(INDEX_HTML, media_type="text/html")


@app.get("/api/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "model": _get_agent().llm.model}


@app.post("/api/ask")
async def ask(req: AskRequest) -> JSONResponse:
    question, session = validate_request(req)
    current = _get_agent()
    if session in _in_flight:
        raise HTTPException(status_code=429, detail=BUSY_MSG)
    _in_flight.add(session)
    try:
        ans = await asyncio.to_thread(current.ask, question, history.get(session))
    except Exception:  # one failed question must not take the server down
        log.exception("failed on %r", question)
        raise HTTPException(status_code=500, detail=ERROR_MSG)
    finally:
        _in_flight.discard(session)
    log.info("Q=%r | sql=%r | rows=%d | %.1fs", question, ans.sql, len(ans.rows), ans.elapsed_sec)
    record_qa(ans, {"channel": "web", "session": session})
    if ans.answerable and not ans.timed_out:
        history.add(session, question, ans.interpretation)
    return JSONResponse(answer_payload(ans))
