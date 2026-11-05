"""Activity log: every incoming message/button is recorded with who and when; logging never breaks the bot."""

from __future__ import annotations

import asyncio
import datetime as dt
import json

from aiogram.types import CallbackQuery, Chat, Message, User

import app.events as events
from bot import EventLogger

USER = User(id=777, is_bot=False, first_name="Ali", last_name="Valiyev", username="ali_v", language_code="uz")
CHAT = Chat(id=777, type="private")


def _read(path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


def test_message_and_button_are_logged(tmp_path, monkeypatch) -> None:
    path = tmp_path / "events.jsonl"
    monkeypatch.setattr(events, "EVENTS_LOG_PATH", str(path))
    msg = Message(message_id=1, date=dt.datetime.now(dt.timezone.utc), chat=CHAT, from_user=USER, text="/start")
    cb = CallbackQuery(id="1", from_user=USER, chat_instance="x", data="an|uz|p|520100", message=msg)

    async def handler(event, data):
        return "handled"

    async def run():
        assert await EventLogger()(handler, msg, {}) == "handled"
        assert await EventLogger()(handler, cb, {}) == "handled"

    asyncio.run(run())
    first, second = _read(path)
    assert first["kind"] == "message" and first["command"] == "/start" and first["user_id"] == 777
    assert first["username"] == "ali_v" and first["first_name"] == "Ali" and first["language_code"] == "uz"
    assert second["kind"] == "button" and second["data"] == "an|uz|p|520100" and second["chat_id"] == 777
    assert first["ts"].endswith("+00:00")


def test_log_event_never_raises(tmp_path) -> None:
    bad_dir = tmp_path / "file_not_dir"
    bad_dir.write_text("x")
    events.log_event("answer", USER, CHAT, path=str(bad_dir / "events.jsonl"), answer="a")  # cannot write: no exception


def test_user_report_window_and_first_start(tmp_path) -> None:
    import sys
    sys.path.insert(0, "scripts")
    from user_report import build_report, load, parse_local

    path = tmp_path / "events.jsonl"
    other = User(id=888, is_bot=False, first_name="Olga", username=None, language_code="ru")
    rows = [
        ("2026-11-05T12:00:00+00:00", "message", USER, {"text": "/start", "command": "/start"}),      # 17:00 Tashkent, outside
        ("2026-11-05T12:50:00+00:00", "message", USER, {"text": "2024 paxta?", "command": None}),     # 17:50 inside
        ("2026-11-05T12:50:09+00:00", "answer", USER, {"question": "2024 paxta?", "answer": "**28 079** ta", "language": "uz",
                                                       "rows": 1, "elapsed_sec": 8.5, "answerable": True, "sql": "SELECT 1"}),
        ("2026-11-05T12:51:00+00:00", "button", USER, {"data": "an|uz|p|520100"}),
        ("2026-11-05T13:00:00+00:00", "message", other, {"text": "/start", "command": "/start"}),
    ]
    with open(path, "w", encoding="utf-8") as fh:
        for ts, kind, user, data in rows:
            fh.write(json.dumps({"ts": ts, "kind": kind, **events.user_fields(user), "chat_id": user.id, **data},
                                ensure_ascii=False) + "\n")
    report, table = build_report(load(str(path)), parse_local("2026-11-05 17:45"), parse_local("2026-11-05 23:00"))
    assert "Users active in the window: **2**" in report
    assert "| 777 | @ali_v | Ali Valiyev | uz | 2026-11-05 17:00:00 | 2026-11-05 17:00:00 | 1 | 1 | 0 | 0 |" in report
    assert "| 888 | @— | Olga | ru |" in report
    assert "✉️ 2024 paxta?" in report and "🔘 button `an|uz|p|520100`" in report and "> **28 079** ta" in report
    assert len(table) == 4  # the 17:00 /start is outside the window
