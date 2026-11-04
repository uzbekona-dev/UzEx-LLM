"""Read-only SQL execution with validation, timeout and row cap."""

from __future__ import annotations

import re
import sqlite3
import time
from dataclasses import dataclass, field

from app.normalize import company_key

FORBIDDEN = re.compile(
    r"\b(insert|update|delete|drop|alter|create|attach|detach|pragma|vacuum|replace|reindex)\b", re.I
)
MAX_ROWS = 50
TIMEOUT_SEC = 20


class SqlRejected(ValueError):
    pass


@dataclass(frozen=True)
class QueryResult:
    sql: str
    columns: list[str]
    rows: list[tuple]
    elapsed_sec: float
    truncated: bool = False
    error: str | None = None

    @property
    def ok(self) -> bool:
        return self.error is None

    def as_records(self) -> list[dict]:
        return [dict(zip(self.columns, r)) for r in self.rows]


def clean_sql(sql: str) -> str:
    sql = sql.strip()
    sql = re.sub(r"^```(?:sql)?\s*|\s*```$", "", sql, flags=re.I).strip()
    sql = sql.rstrip(";").strip()
    if ";" in sql:
        raise SqlRejected("multiple statements are not allowed")
    if not re.match(r"^(select|with)\b", sql, re.I):
        raise SqlRejected("only SELECT queries are allowed")
    if FORBIDDEN.search(sql):
        raise SqlRejected("forbidden keyword in query")
    if not re.search(r"\blimit\s+\d+", sql, re.I):
        sql = f"{sql}\nLIMIT {MAX_ROWS}"
    return sql


def open_db(path: str) -> sqlite3.Connection:
    con = sqlite3.connect(f"file:{path}?mode=ro", uri=True, check_same_thread=False)
    con.create_function("ckey", 1, company_key)
    return con


def run_query(con: sqlite3.Connection, sql: str) -> QueryResult:
    try:
        safe = clean_sql(sql)
    except SqlRejected as exc:
        return QueryResult(sql=sql, columns=[], rows=[], elapsed_sec=0.0, error=str(exc))
    started = time.monotonic()
    deadline = started + TIMEOUT_SEC
    con.set_progress_handler(lambda: 1 if time.monotonic() > deadline else 0, 10_000)
    try:
        cur = con.execute(safe)
        rows = cur.fetchmany(MAX_ROWS + 1)
        columns = [d[0] for d in cur.description or []]
    except sqlite3.Error as exc:
        return QueryResult(sql=safe, columns=[], rows=[], elapsed_sec=time.monotonic() - started, error=str(exc))
    finally:
        con.set_progress_handler(None, 0)
    truncated = len(rows) > MAX_ROWS
    return QueryResult(sql=safe, columns=columns, rows=rows[:MAX_ROWS], elapsed_sec=time.monotonic() - started,
                       truncated=truncated)
