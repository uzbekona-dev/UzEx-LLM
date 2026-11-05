"""Per-user activity report from logs/events.jsonl for a Tashkent-time window.

Usage:
  python -X utf8 scripts/user_report.py --from "2026-11-05 17:45" --to "2026-11-05 23:00" \
      [--events logs/events.jsonl] [--out logs/user_report.md] [--csv logs/user_events.csv]

For every user: Telegram id, @username, name, language, first event ever seen, first /start ever,
counts (questions, buttons, reports, errors), then the full timeline inside the window:
time, what they sent or pressed, and what the bot answered (with interpretation, SQL, rows, time).
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from collections import defaultdict
from datetime import datetime, timedelta, timezone

TASHKENT = timezone(timedelta(hours=5))


def parse_local(text: str) -> datetime:
    return datetime.strptime(text, "%Y-%m-%d %H:%M").replace(tzinfo=TASHKENT)


def load(path: str) -> list[dict]:
    out = []
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                e = json.loads(line)
                e["_t"] = datetime.fromisoformat(e["ts"]).astimezone(TASHKENT)
                out.append(e)
            except (ValueError, KeyError):
                continue
    return out


def local(t: datetime) -> str:
    return t.strftime("%Y-%m-%d %H:%M:%S")


def build_report(events: list[dict], start: datetime, end: datetime) -> tuple[str, list[dict]]:
    by_user: dict = defaultdict(list)
    for e in events:
        if e.get("user_id") is not None:
            by_user[e["user_id"]].append(e)
    lines = [f"# Bot activity {local(start)} — {local(end)} (Asia/Tashkent)", ""]
    rows: list[dict] = []
    active = {uid: evs for uid, evs in by_user.items() if any(start <= e["_t"] <= end for e in evs)}
    lines.append(f"Users active in the window: **{len(active)}**")
    lines.append("")
    lines.append("| # | user_id | username | name | lang | first seen | first /start | questions | buttons | reports | errors |")
    lines.append("|---|---|---|---|---|---|---|---|---|---|---|")
    order = sorted(active, key=lambda u: min(e["_t"] for e in active[u] if start <= e["_t"] <= end))
    for i, uid in enumerate(order, 1):
        evs = sorted(by_user[uid], key=lambda e: e["_t"])
        win = [e for e in evs if start <= e["_t"] <= end]
        last = evs[-1]
        starts = [e for e in evs if e.get("kind") == "message" and e.get("command") == "/start"]
        name = " ".join(x for x in (last.get("first_name"), last.get("last_name")) if x)
        lines.append(
            f"| {i} | {uid} | @{last.get('username') or '—'} | {name or '—'} | {last.get('language_code') or '—'} "
            f"| {local(evs[0]['_t'])} | {local(starts[0]['_t']) if starts else '—'} "
            f"| {sum(e['kind'] == 'answer' for e in win)} | {sum(e['kind'] == 'button' for e in win)} "
            f"| {sum(e['kind'] == 'report' for e in win)} | {sum(e['kind'] in ('error', 'report_error') for e in win)} |")
    for uid in order:
        evs = sorted(by_user[uid], key=lambda e: e["_t"])
        last = evs[-1]
        lines += ["", f"## {uid} @{last.get('username') or '—'} — {last.get('first_name') or ''} {last.get('last_name') or ''}".rstrip(), ""]
        for e in evs:
            if not (start <= e["_t"] <= end):
                continue
            t = e["_t"].strftime("%H:%M:%S")
            kind = e.get("kind")
            if kind == "message":
                what = e.get("text") if e.get("text") is not None else f"[{e.get('content_type')}]"
                lines.append(f"- **{t}** ✉️ {what}")
            elif kind == "button":
                lines.append(f"- **{t}** 🔘 button `{e.get('data')}`")
            elif kind == "answer":
                lines.append(f"  - **{t}** 🤖 answer ({e.get('language')}, {e.get('rows')} rows, {e.get('elapsed_sec')} s, "
                             f"answerable={e.get('answerable')}, template={e.get('used_template')}"
                             + (", TIMEOUT" if e.get("timed_out") else "") + ")")
                lines.append("    > " + str(e.get("answer", "")).replace("\n", "\n    > "))
                if e.get("interpretation"):
                    lines.append(f"    - interpretation: {e['interpretation']}")
                if e.get("sql"):
                    lines.append(f"    - sql: `{' '.join(str(e['sql']).split())}`")
                if e.get("buttons"):
                    lines.append(f"    - buttons offered: {', '.join(e['buttons'])}")
            elif kind == "report":
                first_line = str(e.get("text", "")).splitlines()[0] if e.get("text") else ""
                lines.append(f"  - **{t}** 📊 report `{e.get('what')}` — {first_line}")
            elif kind in ("error", "report_error"):
                lines.append(f"  - **{t}** ⚠️ {kind}: {str(e.get('error', ''))[-300:]}")
            rows.append({"time_tashkent": local(e["_t"]), "user_id": uid, "username": e.get("username"),
                         "first_name": e.get("first_name"), "last_name": e.get("last_name"), "kind": kind,
                         "text_or_data": e.get("text") or e.get("data") or e.get("question") or e.get("what"),
                         "answer": e.get("answer") or e.get("text") if kind in ("answer", "report") else None,
                         "language": e.get("language"), "rows": e.get("rows"), "elapsed_sec": e.get("elapsed_sec"),
                         "answerable": e.get("answerable"), "sql": e.get("sql")})
    return "\n".join(lines) + "\n", rows


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--from", dest="start", required=True, help='Tashkent time, "YYYY-MM-DD HH:MM"')
    ap.add_argument("--to", dest="end", required=True, help='Tashkent time, "YYYY-MM-DD HH:MM"')
    ap.add_argument("--events", default="logs/events.jsonl")
    ap.add_argument("--out", default="logs/user_report.md")
    ap.add_argument("--csv", default="logs/user_events.csv")
    args = ap.parse_args()
    report, rows = build_report(load(args.events), parse_local(args.start), parse_local(args.end))
    with open(args.out, "w", encoding="utf-8") as fh:
        fh.write(report)
    if rows:
        with open(args.csv, "w", encoding="utf-8-sig", newline="") as fh:
            writer = csv.DictWriter(fh, fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows(rows)
    print(f"{len(rows)} events -> {args.out}, {args.csv}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
