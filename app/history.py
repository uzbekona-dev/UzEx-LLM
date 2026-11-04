"""Per-conversation memory of the last few turns, shared by the Telegram bot and the web UI."""

from __future__ import annotations

from collections import deque
from typing import Generic, Hashable, TypeVar

Key = TypeVar("Key", bound=Hashable)


class ChatHistory(Generic[Key]):
    """Last few (question, interpretation) pairs per chat so follow-ups like "va 2023-da?" resolve."""

    def __init__(self, turns: int = 2) -> None:
        self._turns = turns
        self._by_chat: dict[Key, deque[tuple[str, str]]] = {}

    def get(self, chat_id: Key) -> list[tuple[str, str]]:
        return list(self._by_chat.get(chat_id, ()))

    def add(self, chat_id: Key, question: str, interpretation: str) -> None:
        self._by_chat.setdefault(chat_id, deque(maxlen=self._turns)).append((question, interpretation))

    def clear(self, chat_id: Key) -> None:
        self._by_chat.pop(chat_id, None)
