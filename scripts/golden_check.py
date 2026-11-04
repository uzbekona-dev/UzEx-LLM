"""Run tests/golden.jsonl through the live agent and check every answer against ground truth.

Usage: python scripts/golden_check.py [--ids g01,g05] [--tags contracts,trap] [--limit N]
                                      [--golden tests/golden.jsonl] [--report tests/golden_report.md]
Exit code 1 if any entry fails. Each call costs LLM quota (2-3 LLM calls per question).
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from dataclasses import dataclass

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv  # noqa: E402

from app.agent import Agent, AgentAnswer  # noqa: E402
from app.entities import EntityResolver  # noqa: E402
from app.llm import Llm  # noqa: E402
from app.normalize import translit  # noqa: E402
from app.sql_guard import open_db  # noqa: E402
from app.verify import _matches, extract_numbers  # noqa: E402

load_dotenv()

ROUNDING_SCALES = (1.0, 1e3, 1e6, 1e9)
ROUNDING_DIGITS = (0, 1, 2)


@dataclass(frozen=True)
class GoldenEntry:
    id: str
    q: str
    sql: str | None
    numbers: list[float]
    strings: list[str]
    unanswerable: bool
    tags: list[str]
    forbidden: tuple[float, ...] = ()  # numbers that must NOT appear in the answer (prompt-injection bait)


@dataclass(frozen=True)
class CheckResult:
    entry: GoldenEntry
    ok: bool
    elapsed_sec: float
    missing: list[str]
    answer: str
    sql: str | None
    answerable: bool


def load_golden(path: str) -> list[GoldenEntry]:
    entries = []
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            raw = json.loads(line)
            expect = raw.get("expect", {})
            entries.append(GoldenEntry(
                id=raw["id"], q=raw["q"], sql=raw.get("sql"),
                numbers=[float(n) for n in expect.get("numbers", [])],
                strings=list(expect.get("strings", [])),
                unanswerable=bool(raw.get("unanswerable", False)),
                tags=list(raw.get("tags", [])),
                forbidden=tuple(float(n) for n in raw.get("forbidden", [])),
            ))
    return entries


def select_entries(entries: list[GoldenEntry], ids: str | None, tags: str | None, limit: int | None) -> list[GoldenEntry]:
    chosen = entries
    if ids:
        wanted = {i.strip() for i in ids.split(",") if i.strip()}
        chosen = [e for e in chosen if e.id in wanted]
    if tags:
        wanted_tags = {t.strip() for t in tags.split(",") if t.strip()}
        chosen = [e for e in chosen if wanted_tags & set(e.tags)]
    if limit is not None:
        chosen = chosen[:limit]
    return chosen


def number_present(expected: float, answer_numbers: list[float]) -> bool:
    """True if some number in the answer equals `expected`, a rounding of it, or a thousands/millions scaling.

    Mirrors app.verify._matches (answer value vs allowed DB value) and additionally tolerates the
    half-unit difference between float rounding and the decimal rounding the LLM prints."""
    for value in answer_numbers:
        if _matches(value, {expected}, ROUNDING_SCALES):
            return True
        for scale in ROUNDING_SCALES:
            scaled = expected / scale
            for digits in ROUNDING_DIGITS:
                if abs(value - scaled) <= 0.5 * 10 ** (-digits) + 1e-9:
                    return True
    return False


_DMY_RE = re.compile(r"\b(\d{2})\.(\d{2})\.(\d{4})\b")


def string_present(expected: str, answer: str) -> bool:
    """Case/script-insensitive substring; dates written as DD.MM.YYYY also match their ISO form."""
    haystack = translit(answer) + " " + _DMY_RE.sub(r"\3-\2-\1", answer)
    return translit(expected) in translit(haystack)


def forbidden_present(entry: GoldenEntry, answer: str) -> list[str]:
    """Problems for every forbidden number that the answer contains verbatim (no rounding/scaling leniency:
    the bait number is planted by the question, so any exact occurrence means the injection worked)."""
    answer_numbers = extract_numbers(answer)
    return [f"forbidden number {bad:g} present" for bad in entry.forbidden if bad in answer_numbers]


def check_entry(entry: GoldenEntry, ans: AgentAnswer) -> CheckResult:
    missing: list[str] = forbidden_present(entry, ans.answer)
    if entry.unanswerable:
        # Agent must either refuse (answerable=False) or run a query that finds nothing (e.g. a missing deal number).
        refused = not ans.answerable or (ans.sql is not None and not ans.rows)
        if not refused:
            missing.append("expected unanswerable, agent answered")
        return CheckResult(entry, not missing, ans.elapsed_sec, missing, ans.answer, ans.sql, ans.answerable)
    if not ans.answerable:
        missing.append("agent refused an answerable question")
    answer_numbers = extract_numbers(ans.answer)
    for expected in entry.numbers:
        if not number_present(expected, answer_numbers):
            missing.append(f"number {expected:g}")
    for expected in entry.strings:
        if not string_present(expected, ans.answer):
            missing.append(f"string {expected!r}")
    return CheckResult(entry, not missing, ans.elapsed_sec, missing, ans.answer, ans.sql, ans.answerable)


def run_entry(agent: Agent, entry: GoldenEntry) -> CheckResult:
    started = time.monotonic()
    try:
        ans = agent.ask(entry.q)
    except Exception as exc:  # noqa: BLE001 - any agent crash is a test failure, not a script crash
        return CheckResult(entry, False, time.monotonic() - started, [f"ERROR: {exc}"], "", None, False)
    return check_entry(entry, ans)


def format_row(r: CheckResult) -> str:
    status = "ok  " if r.ok else "FAIL"
    return f"{r.entry.id:<5}| {status} | {r.elapsed_sec:5.1f}s | {'; '.join(r.missing)}"


def write_report(path: str, results: list[CheckResult], model: str) -> None:
    passed = sum(1 for r in results if r.ok)
    lines = [f"# Golden check {time.strftime('%Y-%m-%d %H:%M')} model={model}",
             f"\n**{passed}/{len(results)} passed**\n",
             "| id | result | time | missing |", "|---|---|---|---|"]
    for r in results:
        lines.append(f"| {r.entry.id} | {'ok' if r.ok else 'FAIL'} | {r.elapsed_sec:.1f}s | {'; '.join(r.missing)} |")
    lines.append("")
    for r in results:
        lines += [f"## {r.entry.id}. {r.entry.q}", f"tags: {', '.join(r.entry.tags)}",
                  f"**Javob:** {r.answer}", f"```sql\n{r.sql or '-'}\n```",
                  f"answerable={r.answerable} ok={r.ok} time={r.elapsed_sec:.1f}s missing={r.missing}\n"]
    with open(path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--ids", help="comma-separated golden ids, e.g. g01,g05")
    parser.add_argument("--tags", help="comma-separated tags; entry runs if it has ANY of them")
    parser.add_argument("--limit", type=int, help="run only the first N selected entries")
    parser.add_argument("--golden", default="tests/golden.jsonl")
    parser.add_argument("--report", default="tests/golden_report.md")
    args = parser.parse_args(argv)

    entries = select_entries(load_golden(args.golden), args.ids, args.tags, args.limit)
    if not entries:
        print("no golden entries selected")
        return 1
    db_path = os.environ.get("DB_PATH", "data/uzex.db")
    agent = Agent(None, Llm(), db_path=db_path, resolver=EntityResolver(open_db(db_path)))
    print(f"{'id':<5}| res  | time   | missing")
    results: list[CheckResult] = []
    for entry in entries:
        result = run_entry(agent, entry)
        results.append(result)
        print(format_row(result), flush=True)
    write_report(args.report, results, agent.llm.model)
    failed = [r for r in results if not r.ok]
    print(f"\n{len(results) - len(failed)}/{len(results)} passed -> {args.report}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
