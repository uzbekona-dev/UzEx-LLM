"""Run every question in tests/questions.txt through the agent and write a report.

Usage: python scripts/run_questions.py [questions_file] [report_file]
"""

from __future__ import annotations

import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv  # noqa: E402

from app.agent import Agent  # noqa: E402
from app.entities import EntityResolver  # noqa: E402
from app.sql_guard import open_db  # noqa: E402
from app.llm import Llm  # noqa: E402

load_dotenv()


def main(questions_file: str, report_file: str) -> None:
    db_path = os.environ.get("DB_PATH", "data/uzex.db")
    agent = Agent(None, Llm(), db_path=db_path, resolver=EntityResolver(open_db(db_path)))
    with open(questions_file, encoding="utf-8") as fh:
        questions = [q.strip() for q in fh if q.strip() and not q.startswith("#")]
    with open(report_file, "w", encoding="utf-8") as fh:
        fh.write(f"# Report {time.strftime('%Y-%m-%d %H:%M')} model={agent.llm.model}\n\n")
        for i, q in enumerate(questions, 1):
            print(f"[{i}/{len(questions)}] {q}", flush=True)
            try:
                a = agent.ask(q)
                block = [f"## {i}. {q}", f"**Javob:** {a.answer}", f"*Talqin:* {a.interpretation}",
                         f"```sql\n{a.sql or '-'}\n```",
                         f"rows={len(a.rows)} verified={a.verified} answerable={a.answerable} time={a.elapsed_sec:.1f}s\n"]
            except Exception as exc:  # noqa: BLE001
                block = [f"## {i}. {q}", f"**ERROR:** {exc}\n"]
            fh.write("\n".join(block) + "\n")
            fh.flush()
    print("report ->", report_file)


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "tests/questions.txt",
         sys.argv[2] if len(sys.argv) > 2 else "tests/report.md")
