"""Bot activity log: one JSON line per incoming update and per outgoing answer/report (logs/events.jsonl).

Who (Telegram user id, username, names, language), where (chat), what (text / command / button data)
and what the bot answered, with timestamps in UTC. Written on the server only (logs/ is not in git).
Never raises: logging must not break the bot.
"""

from __future__ import annotations

import json
import logging
import os
import threading
from datetime import datetime, timezone
from typing import Any

EVENTS_LOG_PATH = os.environ.get("EVENTS_LOG", "logs/events.jsonl")
_lock = threading.Lock()
log = logging.getLogger(__name__)


def user_fields(user: Any) -> dict:
    if user is None:
        return {}
    return {
        "user_id": getattr(user, "id", None),
        "username": getattr(user, "username", None),
        "first_name": getattr(user, "first_name", None),
        "last_name": getattr(user, "last_name", None),
        "language_code": getattr(user, "language_code", None),
        "is_premium": getattr(user, "is_premium", None),
        "is_bot": getattr(user, "is_bot", None),
    }


def chat_fields(chat: Any) -> dict:
    if chat is None:
        return {}
    return {"chat_id": getattr(chat, "id", None), "chat_type": getattr(chat, "type", None),
            "chat_title": getattr(chat, "title", None)}


def log_event(kind: str, user: Any = None, chat: Any = None, path: str | None = None, **data: Any) -> None:
    entry = {"ts": datetime.now(timezone.utc).isoformat(timespec="seconds"), "kind": kind,
             **user_fields(user), **chat_fields(chat), **data}
    target = path or EVENTS_LOG_PATH
    try:
        os.makedirs(os.path.dirname(target) or ".", exist_ok=True)
        line = json.dumps(entry, ensure_ascii=False, default=str)
        with _lock, open(target, "a", encoding="utf-8") as fh:
            fh.write(line + "\n")
    except Exception:  # noqa: BLE001
        log.exception("could not write event log")
