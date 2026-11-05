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
from aiogram.types import (
    BotCommand,
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
    ReplyKeyboardRemove,
)
from aiogram.utils.chat_action import ChatActionSender
from dotenv import load_dotenv

from app import analytics
from app.agent import Agent, AgentAnswer, record_qa
from app.entities import EntityResolver
from app.format import EVIDENCE_OPEN, answer_html, render
from app.history import ChatHistory
from app.llm import Llm
from app.sql_guard import open_db

load_dotenv()
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log = logging.getLogger("bot")

TELEGRAM_MESSAGE_LIMIT = 4096
# Deterministic analytics (fixed SQL, no LLM): button under answers + /statistika. Off unless ANALYTICS=1.
ANALYTICS = os.environ.get("ANALYTICS", "0") in ("1", "true", "yes")
BUTTON_TEXT = {"uz": "📊 Analitika", "uz_cyr": "📊 Аналитика", "ru": "📊 Аналитика"}
ANALYTICS_ERROR = "Analitika hozircha mavjud emas. / Аналитика временно недоступна."

WELCOME = (
    "🤖 <b>UZEX birja bitimlari bo'yicha AI-yordamchi</b>\n"
    "Ma'lumotlar: 03.01.2022 – 30.10.2026, 500 000 bitim.\n\n"
    "<b>Nima qila olaman</b>\n"
    "• Bitim raqami bo'yicha: kim sotgan, kim olgan, narx, hajm, status\n"
    "• Tovar bo'yicha hajm, summa, o'rtacha narx — yil / oy / hudud kesimida\n"
    "• Kompaniya (nomi yoki STIR) va brokerlar statistikasi\n"
    "• Dollar kursi, bekor qilingan va kechikkan bitimlar\n\n"
    "<b>Qanday sinash</b>\n"
    "1. Savolni o'zbek yoki rus tilida yozing (misollar: /examples)\n"
    "2. 5–30 soniya kuting — javob ostida ✅ asos va ▸ SQL ko'rinadi\n"
    "3. Ma'lumotda yo'q narsani so'rab ko'ring — «javob yo'q» deyman, o'ylab topmayman\n\n"
    "🤖 <b>AI-ассистент по биржевым сделкам UZEX</b>\n"
    "Данные: 03.01.2022 – 30.10.2026, 500 000 сделок.\n\n"
    "<b>Что умею</b>\n"
    "• По номеру сделки: продавец, покупатель, цена, объём, статус\n"
    "• По товару: объём, сумма, средняя цена — по годам / месяцам / регионам\n"
    "• Статистика по компании (название или ИНН) и брокерам\n"
    "• Курс доллара, аннулированные и просроченные сделки\n\n"
    "<b>Как проверить</b>\n"
    "1. Напишите вопрос на узбекском или русском (примеры: /examples)\n"
    "2. Подождите 5–30 секунд — под ответом будут ✅ основание и ▸ SQL\n"
    "3. Спросите то, чего нет в данных — скажу «ответа нет», ничего не придумаю"
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
    "2024-yilda qancha paxta sotilgan?",
    "Кто покупатель по сделке 100001?",
    "2025-yil top-5 broker",
    "Цена цемента в марте 2023",
    "15.06.2024 dollar kursi",
    "Сделки компании Qojo Invest",
]
PROGRESS = "⏳ Ma'lumotlarni qidiryapman… / Ищу в данных… (5–30 s)"
ERROR_MSG = (
    "⚠️ Texnik xatolik yuz berdi, iltimos bir ozdan keyin qayta urinib ko'ring.\n"
    "⚠️ Произошла техническая ошибка, попробуйте ещё раз через минуту."
)
# Shown on the bot's profile / empty chat before /start (Telegram limits: 512 and 120 chars).
DESCRIPTION = (
    "UZEX birja bitimlari bo'yicha AI-yordamchi: 2022–2026, 500 000 bitim. O'zbek yoki rus tilida savol "
    "bering — javob faqat ma'lumotlardan, asosi va SQL bilan; ma'lumotda bo'lmasa, o'ylab topmaydi.\n\n"
    "AI-ассистент по биржевым сделкам UZEX: 2022–2026, 500 000 сделок. Спросите на русском или узбекском — "
    "ответ только по данным, с основанием и SQL; чего нет в данных, не придумывает."
)
SHORT_DESCRIPTION = "UZEX bitimlari bo'yicha AI-yordamchi · AI-ассистент по сделкам UZEX (uz / ru)"

COMMANDS = [
    BotCommand(command="start", description="Boshlash / Начать"),
    BotCommand(command="help", description="Nima so'rash mumkin / Что можно спросить"),
    BotCommand(command="examples", description="Misol savollar / Примеры вопросов"),
]
if ANALYTICS:
    COMMANDS.append(BotCommand(command="statistika", description="Umumiy statistika / Общая статистика"))

router = Router(name="main")


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
async def on_start(message: Message, chat_history: ChatHistory) -> None:
    chat_history.clear(message.chat.id)
    await message.answer(WELCOME, reply_markup=ReplyKeyboardRemove())  # also clears the old example-button keyboard


@router.message(Command("help"))
async def on_help(message: Message) -> None:
    await message.answer(HELP, reply_markup=ReplyKeyboardRemove())


@router.message(Command("examples"))
async def on_examples(message: Message) -> None:
    text = "\n".join(f"• {q}" for q in EXAMPLES)
    await message.answer(text, reply_markup=ReplyKeyboardRemove(), parse_mode=None)


@router.message(F.text)
async def on_question(message: Message, agent: Agent, chat_locks: ChatLocks, chat_history: ChatHistory) -> None:
    question = (message.text or "").strip()
    if not question:
        return
    async with (
        chat_locks.hold(message.chat.id),
        ChatActionSender.typing(bot=message.bot, chat_id=message.chat.id),
    ):
        await _answer(message, agent, chat_history, question)


async def _answer(message: Message, agent: Agent, chat_history: ChatHistory, question: str) -> None:
    progress = await message.answer(PROGRESS, parse_mode=None)
    chat_id = message.chat.id
    try:
        ans = await asyncio.to_thread(agent.ask, question, chat_history.get(chat_id))
        log.info("Q=%r | sql=%r | rows=%d | %.1fs", question, ans.sql, len(ans.rows), ans.elapsed_sec)
        record_qa(ans, {"chat_id": chat_id, "user": message.from_user.id if message.from_user else None})
        if ans.answerable and not ans.timed_out:
            chat_history.add(chat_id, question, ans.interpretation)
        parts = split_message(render(ans))
        markup = _analytics_markup(agent, ans)
        await _edit_or_resend(progress, parts[0], reply_markup=markup if len(parts) == 1 else None)
        for i, part in enumerate(parts[1:], 2):
            await message.answer(part, reply_markup=markup if i == len(parts) else None)
    except Exception:  # never let one question kill the polling loop
        log.exception("failed on %r", question)
        await _edit_or_resend(progress, ERROR_MSG, parse_mode=None)


async def _edit_or_resend(progress: Message, text: str, parse_mode: str | None = ParseMode.HTML,
                          reply_markup: InlineKeyboardMarkup | None = None) -> None:
    """Replace the ⏳ message with the answer; if editing fails (deleted, too old), send a new one."""
    try:
        await progress.edit_text(text, parse_mode=parse_mode, reply_markup=reply_markup)
    except TelegramBadRequest as exc:
        log.warning("edit failed (%s), sending a new message", exc)
        await progress.answer(text, parse_mode=parse_mode, reply_markup=reply_markup)


def _analytics_markup(agent: Agent, ans: AgentAnswer) -> InlineKeyboardMarkup | None:
    """A button per confidently resolved entity of the question; never fails the answer itself."""
    if not ANALYTICS or not ans.answerable or ans.timed_out or not ans.rows or agent.resolver is None:
        return None
    try:
        targets = analytics.pick_targets(agent.resolver.resolve(ans.question))
    except Exception:  # noqa: BLE001
        log.warning("analytics target resolution failed", exc_info=True)
        return None
    if not targets:
        return None
    label = BUTTON_TEXT.get(ans.language, BUTTON_TEXT["ru"])
    rows = [[InlineKeyboardButton(text=f"{label}: {t.title[:28]}", callback_data=t.callback(ans.language))]
            for t in targets]
    return InlineKeyboardMarkup(inline_keyboard=rows)


@router.callback_query(F.data.startswith("an|"))
async def on_analytics(callback: CallbackQuery, agent: Agent) -> None:
    await callback.answer()
    parsed = analytics.parse_callback(callback.data or "")
    if not parsed or callback.message is None or not agent.db_path:
        return
    lang, target = parsed
    await _send_report(callback.message, lambda: _run_report(agent.db_path, target, lang))


@router.message(Command("statistika", "stats"))
async def on_statistics(message: Message, agent: Agent) -> None:
    if not ANALYTICS or not agent.db_path:
        return
    lang = "ru" if message.from_user and (message.from_user.language_code or "").startswith("ru") else "uz"
    await _send_report(message, lambda: analytics.overview_report(agent.db_path, lang))


def _run_report(db_path: str, target: analytics.Target, lang: str) -> str:
    con = open_db(db_path)
    try:
        return analytics.report(con, target, lang)
    finally:
        con.close()


async def _send_report(message: Message, build) -> None:
    async with ChatActionSender.typing(bot=message.bot, chat_id=message.chat.id):
        try:
            text = await asyncio.to_thread(build)
        except Exception:  # noqa: BLE001 - analytics must never break the bot
            log.exception("analytics report failed")
            await message.answer(ANALYTICS_ERROR, parse_mode=None)
            return
    for part in split_message(answer_html(text)):
        await message.answer(part)


async def _set_profile(bot: Bot) -> None:
    """Profile texts are cosmetic: never let a Telegram hiccup here stop the bot."""
    try:
        await bot.set_my_description(DESCRIPTION)
        await bot.set_my_short_description(SHORT_DESCRIPTION)
    except Exception:  # noqa: BLE001
        log.warning("could not set bot description", exc_info=True)


def build_agent() -> Agent:
    db_path = os.environ.get("DB_PATH", "data/uzex.db")
    return Agent(None, Llm(), db_path=db_path, resolver=build_resolver(db_path))


def build_resolver(db_path: str) -> EntityResolver:
    return EntityResolver(open_db(db_path))


def build_dispatcher(agent: Agent) -> Dispatcher:
    dp = Dispatcher(agent=agent, chat_locks=ChatLocks(), chat_history=ChatHistory())
    dp.include_router(router)
    return dp


async def run() -> None:
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    if not token:
        raise RuntimeError("TELEGRAM_BOT_TOKEN is not set (put it in .env or the environment)")
    bot = Bot(token=token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = build_dispatcher(build_agent())
    await bot.set_my_commands(COMMANDS)
    await _set_profile(bot)
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
