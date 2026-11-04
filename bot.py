"""Telegram bot entry point (aiogram 3):  python bot.py"""

from __future__ import annotations

import asyncio
import logging
import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from aiogram import Bot, Dispatcher, F, Router
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import Command
from aiogram.types import BotCommand, KeyboardButton, Message, ReplyKeyboardMarkup
from aiogram.utils.chat_action import ChatActionSender
from dotenv import load_dotenv

from app.agent import Agent
from app.format import EVIDENCE_OPEN, render
from app.llm import Llm
from app.sql_guard import open_db

load_dotenv()
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log = logging.getLogger("bot")

TELEGRAM_MESSAGE_LIMIT = 4096

WELCOME = (
    "👋 <b>UZEX birja bitimlari bo'yicha yordamchi</b>\n"
    "Ma'lumotlar: 03.01.2022 — 30.10.2026, 500 000 bitim, 40 tovar, 14 hudud.\n"
    "Savolni o'zbek yoki rus tilida oddiy so'z bilan yozing — javob faqat ma'lumotlar asosida, "
    "har bir javob ostida u qanday topilgani ko'rsatiladi. Ma'lumotda javob bo'lmasa, shuni aytaman.\n\n"
    "👋 <b>Ассистент по биржевым сделкам UZEX</b>\n"
    "Данные: 03.01.2022 — 30.10.2026, 500 000 сделок, 40 товаров, 14 регионов.\n"
    "Задайте вопрос на узбекском или русском. Отвечаю только по данным и показываю, "
    "как получен ответ. Если ответа в данных нет — скажу об этом.\n\n"
    "⬇️ Misol savollar / Примеры — на кнопках ниже."
)
HELP = (
    "<b>Nima so'rash mumkin / Что можно спросить</b>\n"
    "• bitim raqami bo'yicha tafsilot / детали по номеру сделки\n"
    "• tovar hajmi, summasi, o'rtacha narxi (yil, oy, hudud bo'yicha)\n"
    "• kompaniya (nomi yoki STIR) bitimlari / сделки компании (название или ИНН)\n"
    "• brokerlar reytingi / топ брокеров\n"
    "• dollar kursi sanaga / курс доллара на дату\n"
    "• bekor qilingan, kechikkan bitimlar / аннулированные, просроченные сделки\n\n"
    "Har javob ostida: ✅ qatorlar soni, 🔎 savol qanday tushunilgani, ▸ SQL so'rov (bosib ochiladi).\n"
    "Под каждым ответом: ✅ число строк, 🔎 как понят вопрос, ▸ SQL-запрос (раскрывается по нажатию)."
)
EXAMPLES = [
    "2024-yilda qancha tonna paxta xomashyosi sotilgan?",
    "Кто покупатель и продавец по сделке 100001?",
    "2025-yilda eng ko'p bitim qilgan 5 ta broker",
    "Какая средняя цена портландцемента за тонну в марте 2023 года?",
    "15.06.2024 kuni dollar kursi qancha edi?",
    "Сколько сделок у компании Qojo Invest?",
]
PROGRESS = "⏳ Ma'lumotlarni qidiryapman… / Ищу в данных… (5–30 s)"
ERROR_MSG = (
    "⚠️ Texnik xatolik yuz berdi, iltimos bir ozdan keyin qayta urinib ko'ring.\n"
    "⚠️ Произошла техническая ошибка, попробуйте ещё раз через минуту."
)
COMMANDS = [
    BotCommand(command="start", description="Boshlash / Начать"),
    BotCommand(command="help", description="Nima so'rash mumkin / Что можно спросить"),
    BotCommand(command="examples", description="Misol savollar / Примеры вопросов"),
]

router = Router(name="main")


def examples_keyboard() -> ReplyKeyboardMarkup:
    rows = [[KeyboardButton(text=q)] for q in EXAMPLES]
    return ReplyKeyboardMarkup(keyboard=rows, resize_keyboard=True, input_field_placeholder="Savol / Вопрос…")


def split_message(text: str, limit: int = TELEGRAM_MESSAGE_LIMIT) -> list[str]:
    """Split rendered HTML into Telegram-sized parts without cutting inside the evidence block.

    If the whole text does not fit, the answer text goes first and the evidence block
    (everything from the expandable quote on) is sent as its own message.
    """
    if len(text) <= limit:
        return [text]
    pre_at = text.find(EVIDENCE_OPEN)
    sections = [text] if pre_at <= 0 else [text[:pre_at].rstrip(), text[pre_at:]]
    return [chunk for section in sections for chunk in _split_plain(section, limit)]


def _split_plain(text: str, limit: int) -> list[str]:
    """Chunk plain text at newline boundaries, hard-cutting only when a line is too long."""
    chunks: list[str] = []
    rest = text
    while len(rest) > limit:
        cut = rest.rfind("\n", 0, limit)
        cut = cut if cut > 0 else limit
        chunks.append(rest[:cut].rstrip())
        rest = rest[cut:].lstrip("\n")
    return chunks + ([rest] if rest else [])


class ChatLocks:
    """One asyncio.Lock per chat: a chat's questions run sequentially, chats run in parallel."""

    def __init__(self) -> None:
        self._locks: dict[int, asyncio.Lock] = {}
        self._waiting: dict[int, int] = {}

    @asynccontextmanager
    async def hold(self, chat_id: int) -> AsyncIterator[None]:
        lock = self._locks.setdefault(chat_id, asyncio.Lock())
        self._waiting[chat_id] = self._waiting.get(chat_id, 0) + 1
        try:
            async with lock:
                yield
        finally:
            self._waiting[chat_id] -= 1
            if self._waiting[chat_id] == 0:  # forget idle chats so the dict does not grow forever
                del self._waiting[chat_id], self._locks[chat_id]

    def is_busy(self, chat_id: int) -> bool:
        return chat_id in self._locks


@router.message(Command("start"))
async def on_start(message: Message) -> None:
    await message.answer(WELCOME, reply_markup=examples_keyboard())


@router.message(Command("help"))
async def on_help(message: Message) -> None:
    await message.answer(HELP, reply_markup=examples_keyboard())


@router.message(Command("examples"))
async def on_examples(message: Message) -> None:
    text = "\n".join(f"• {q}" for q in EXAMPLES)
    await message.answer(text, reply_markup=examples_keyboard(), parse_mode=None)


@router.message(F.text)
async def on_question(message: Message, agent: Agent, chat_locks: ChatLocks) -> None:
    question = (message.text or "").strip()
    if not question:
        return
    async with (
        chat_locks.hold(message.chat.id),
        ChatActionSender.typing(bot=message.bot, chat_id=message.chat.id),
    ):
        await _answer(message, agent, question)


async def _answer(message: Message, agent: Agent, question: str) -> None:
    progress = await message.answer(PROGRESS, parse_mode=None)
    try:
        ans = await asyncio.to_thread(agent.ask, question)
        log.info("Q=%r | sql=%r | rows=%d | %.1fs", question, ans.sql, len(ans.rows), ans.elapsed_sec)
        parts = split_message(render(ans))
        await _edit_or_resend(progress, parts[0])
        for part in parts[1:]:
            await message.answer(part)
    except Exception:  # never let one question kill the polling loop
        log.exception("failed on %r", question)
        await _edit_or_resend(progress, ERROR_MSG, parse_mode=None)


async def _edit_or_resend(progress: Message, text: str, parse_mode: str | None = ParseMode.HTML) -> None:
    """Replace the ⏳ message with the answer; if editing fails (deleted, too old), send a new one."""
    try:
        await progress.edit_text(text, parse_mode=parse_mode)
    except TelegramBadRequest as exc:
        log.warning("edit failed (%s), sending a new message", exc)
        await progress.answer(text, parse_mode=parse_mode)


def build_agent() -> Agent:
    return Agent(open_db(os.environ.get("DB_PATH", "data/uzex.db")), Llm())


def build_dispatcher(agent: Agent) -> Dispatcher:
    dp = Dispatcher(agent=agent, chat_locks=ChatLocks())
    dp.include_router(router)
    return dp


async def run() -> None:
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    if not token:
        raise RuntimeError("TELEGRAM_BOT_TOKEN is not set (put it in .env or the environment)")
    bot = Bot(token=token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = build_dispatcher(build_agent())
    await bot.set_my_commands(COMMANDS)
    log.info("bot started")
    try:
        await dp.start_polling(bot, drop_pending_updates=True)
    finally:
        await bot.session.close()
        log.info("bot stopped")


def main() -> None:
    try:
        asyncio.run(run())
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
