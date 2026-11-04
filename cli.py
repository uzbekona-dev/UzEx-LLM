"""Ask one question from the terminal:  python cli.py "2024-yilda qancha paxta sotilgan?" """

from __future__ import annotations

import logging
import os
import sys

from dotenv import load_dotenv

from app.agent import Agent
from app.entities import EntityResolver
from app.sql_guard import open_db
from app.llm import Llm

load_dotenv()
logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")


def main() -> None:
    question = " ".join(sys.argv[1:]).strip()
    if not question:
        print('usage: python cli.py "<question>"')
        sys.exit(1)
    db_path = os.environ.get("DB_PATH", "data/uzex.db")
    agent = Agent(None, Llm(), db_path=db_path, resolver=EntityResolver(open_db(db_path)))
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
