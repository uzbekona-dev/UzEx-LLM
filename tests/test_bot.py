"""Offline tests for bot.py helpers: no Telegram network, no LLM."""

from __future__ import annotations

import asyncio

import pytest

from bot import ChatLocks, split_message

PRE = "<blockquote expandable>▸ SQL\n<code>SELECT 1</code></blockquote>"


def test_short_message_is_not_split() -> None:
    text = "answer\n\n📎 Основание: x\n" + PRE
    assert split_message(text) == [text]


def test_long_message_splits_before_pre_block() -> None:
    answer = "строка ответа\n" * 400  # > 4096 chars
    parts = split_message(answer + "\n📎 Основание: x\n" + PRE)
    assert all(len(p) <= 4096 for p in parts)
    assert parts[-1] == PRE  # evidence block is its own message, intact
    assert all("<blockquote" not in p for p in parts[:-1])
    assert "".join(parts).count("<blockquote") == 1


def test_long_text_without_pre_splits_at_newlines() -> None:
    lines = [f"line {i}" for i in range(1500)]
    parts = split_message("\n".join(lines))
    assert all(len(p) <= 4096 for p in parts)
    assert all(not p.startswith("\n") and not p.endswith("\n") for p in parts)
    assert [line for p in parts for line in p.split("\n")] == lines


def test_overlong_line_is_hard_cut() -> None:
    parts = split_message("x" * 10_000, limit=100)
    assert [len(p) for p in parts] == [100] * 100


def test_split_respects_custom_limit() -> None:
    parts = split_message("a\nb\nc" + PRE, limit=len(PRE))
    assert parts == ["a\nb\nc", PRE]


async def _run(locks: ChatLocks, chat_id: int, name: str, events: list[str], delay: float) -> None:
    async with locks.hold(chat_id):
        events.append(f"{name}:start")
        await asyncio.sleep(delay)
        events.append(f"{name}:end")


def test_same_chat_runs_sequentially() -> None:
    events: list[str] = []
    locks = ChatLocks()

    async def scenario() -> None:
        await asyncio.gather(*(_run(locks, 1, f"q{i}", events, 0.01) for i in range(3)))

    asyncio.run(scenario())
    assert events == ["q0:start", "q0:end", "q1:start", "q1:end", "q2:start", "q2:end"]
    assert not locks.is_busy(1)  # idle chat is forgotten


def test_different_chats_run_in_parallel() -> None:
    events: list[str] = []
    locks = ChatLocks()

    async def scenario() -> None:
        await asyncio.gather(_run(locks, 1, "a", events, 0.05), _run(locks, 2, "b", events, 0.05))

    asyncio.run(scenario())
    assert events[:2] == ["a:start", "b:start"]


def test_lock_is_released_after_exception() -> None:
    locks = ChatLocks()

    async def scenario() -> None:
        with pytest.raises(ValueError):
            async with locks.hold(7):
                raise ValueError("boom")
        assert not locks.is_busy(7)
        async with locks.hold(7):
            assert locks.is_busy(7)

    asyncio.run(scenario())
