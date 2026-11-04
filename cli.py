"""Ask one question from the terminal:  python cli.py "2024-yilda qancha paxta sotilgan?" """

from __future__ import annotations

import logging
import os
import sys

from dotenv import load_dotenv

from app.agent import Agent
from app.llm import Llm
from app.sql_guard import open_db

load_dotenv()
logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")


def main() -> None:
    question = " ".join(sys.argv[1:]).strip()
    if not question:
        print('usage: python cli.py "<question>"')
        sys.exit(1)
    agent = Agent(open_db(os.environ.get("DB_PATH", "data/uzex.db")), Llm())
    ans = agent.ask(question)
    print("\n=== ANSWER ===\n" + ans.answer)
    print("\n=== INTERPRETATION ===\n" + ans.interpretation)
    print("\n=== SQL ===\n" + (ans.sql or "-"))
    print(f"\nrows={len(ans.rows)} verified={ans.verified} answerable={ans.answerable} time={ans.elapsed_sec:.1f}s")
    if os.environ.get("DEBUG"):
        print("\n=== DEBUG ===")
        print("\n".join(ans.debug))


if __name__ == "__main__":
    main()
