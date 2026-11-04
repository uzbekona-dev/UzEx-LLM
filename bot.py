"""Telegram bot entry point:  python bot.py"""

from __future__ import annotations

import asyncio
import logging
import os

from dotenv import load_dotenv
from telegram import Update
from telegram.constants import ChatAction, ParseMode
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters

from app.agent import Agent
from app.format import render
from app.llm import Llm
from app.sql_guard import open_db

load_dotenv()
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log = logging.getLogger("bot")

WELCOME = (
    "Salom! Men birja bitimlari (2022-01-03 — 2026-10-30, 500 000 bitim) bo'yicha savollarga javob beraman.\n"
    "Savolni o'zbek yoki rus tilida yozing. Javob faqat ma'lumotlar asosida beriladi; ma'lumotda javob bo'lmasa, shuni aytaman.\n\n"
    "Здравствуйте! Я отвечаю на вопросы о биржевых сделках (03.01.2022 — 30.10.2026, 500 000 сделок).\n"
    "Пишите на русском или узбекском. Отвечаю только по данным; если ответа в данных нет — скажу об этом.\n\n"
    "Misol / Пример: «2024-yilda qancha paxta sotilgan?», «Кто покупатель по сделке 350000?»"
)
ERROR_MSG = "Texnik xatolik yuz berdi, iltimos qayta urinib ko'ring. / Произошла техническая ошибка, попробуйте ещё раз."


def build_agent() -> Agent:
    return Agent(open_db(os.environ.get("DB_PATH", "data/uzex.db")), Llm())


async def start(update: Update, _: ContextTypes.DEFAULT_TYPE) -> None:
    if update.message:
        await update.message.reply_text(WELCOME)


async def handle(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message or not update.message.text:
        return
    question = update.message.text.strip()
    await update.message.chat.send_action(ChatAction.TYPING)
    agent: Agent = context.bot_data["agent"]
    try:
        ans = await asyncio.to_thread(agent.ask, question)
        log.info("Q=%r | sql=%r | rows=%d | %.1fs", question, ans.sql, len(ans.rows), ans.elapsed_sec)
        await update.message.reply_text(render(ans), parse_mode=ParseMode.HTML)
    except Exception:  # noqa: BLE001
        log.exception("failed on %r", question)
        await update.message.reply_text(ERROR_MSG)


def main() -> None:
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    if not token:
        raise RuntimeError("TELEGRAM_BOT_TOKEN is not set")
    app = Application.builder().token(token).concurrent_updates(True).build()
    app.bot_data["agent"] = build_agent()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle))
    log.info("bot started")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
