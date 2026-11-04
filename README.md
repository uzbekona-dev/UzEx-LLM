# UZEX deals agent

Telegram bot (and CLI) that answers questions about commodity-exchange deals in **Uzbek or Russian**, strictly
from the provided CSV data (500 000 deals, 6 616 contracts, 14 392 participants, 120 brokers, daily USD rate,
2022-01-03 .. 2026-10-30). Built for the UZEX AI Hackathon qualifying round.

How it works in one line: entity resolution in code → LLM writes **one read-only SQL** → SQLite computes →
LLM writes prose → a **grounding verifier** rejects any number / name / code / date that is not in the result
rows → answer with an "evidence" block (row count, interpretation, SQL). The LLM never calculates and never
recalls data. Full description for the jury: [docs/SOLUTION.md](docs/SOLUTION.md) (uz + ru).

## Quick start

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate      Linux/macOS: source .venv/bin/activate
pip install -r requirements.txt

# 1. Data: unzip uzex_spot_data.zip so the CSVs are in data/raw/uzex_spot_data/
#    (README.md, brokers.csv, contracts.csv, deals_2022..2026.csv, participants.csv, usd_rates.csv)
python -X utf8 scripts/build_db.py            # -> data/uzex.db (~335 MB, ~1-2 min)
#    optional: python -X utf8 scripts/build_db.py <raw_dir> <db_path>

# 2. Config
cp .env.example .env                           # fill in at least one LLM key and TELEGRAM_BOT_TOKEN

# 3. Run
python -X utf8 bot.py                          # Telegram bot (long polling)
python -X utf8 cli.py "2024-yilda qancha paxta sotilgan?"   # one question from the terminal
DEBUG=1 python -X utf8 cli.py "Кто покупатель по сделке 100001?"   # + planner/verifier debug trail
```

`-X utf8` (or `PYTHONIOENCODING=utf-8`) matters on Windows: the data and answers are Cyrillic/Uzbek.

## Configuration (`.env`)

| Variable | Default | Meaning |
|---|---|---|
| `LLM_MODELS` | `gemini:gemini-3.5-flash,gemini:gemini-flash-latest,gemini:gemini-3.8-flash,gemini:gemini-2.5-flash` | Fallback chain, comma-separated `provider:model`. Providers: `gemini`, `anthropic`, `openai`. A bare name means `gemini`. |
| `GEMINI_MODEL` | same as above | Legacy chain used only when `LLM_MODELS` is unset (Gemini model names). |
| `RETRIES_PER_MODEL` | `2` | Attempts per chain entry on 429 / 5xx / timeout before moving to the next entry. |
| `GEMINI_API_KEY` | — | Google AI Studio key. Entries of a provider whose key is empty are skipped with a warning. |
| `ANTHROPIC_API_KEY` | — | Anthropic key (Claude Messages API). |
| `OPENAI_API_KEY` | — | OpenAI key — or the key of any OpenAI-compatible service. |
| `OPENAI_BASE_URL` | — | Optional base URL for the `openai` provider (Groq, Ollama, OpenRouter, ...). |
| `TELEGRAM_BOT_TOKEN` | — | Bot token from @BotFather. Required by `bot.py` only. |
| `DB_PATH` | `data/uzex.db` | SQLite file built by `scripts/build_db.py`. Opened read-only. |
| `ANSWER_BUDGET_SEC` | `50` | *(not in .env.example)* Time budget for LLM calls per question; no new LLM call starts after it. |
| `QA_LOG` | `logs/qa.jsonl` | *(not in .env.example)* Where every answered question is appended (JSON lines). Empty string disables. |
| `DEBUG` | — | *(cli.py only)* Any value prints the planner / verifier debug trail. |

At least one vendor key must be set, otherwise startup fails with a clear message.

### LLM configuration details

The agent talks to LLM vendors only through `app/llm/`. The chain of models is tried in order; each entry is
retried `RETRIES_PER_MODEL` times (default 2) on 429 / 503 / 5xx / timeouts, then the next entry is used. Auth
or invalid-request errors skip the entry at once. Every request has a 40 s timeout.

```
LLM_MODELS=gemini:gemini-3.5-flash,anthropic:claude-sonnet-5-5,openai:gpt-5-mini
GEMINI_API_KEY=...
ANTHROPIC_API_KEY=...
OPENAI_API_KEY=...
```

Supported providers: `gemini` (google-genai), `anthropic` (Claude Messages API) and `openai` (chat
completions; set `OPENAI_BASE_URL` to use Groq, Ollama or any other OpenAI-compatible endpoint). Entries whose
API key is empty are skipped with a warning, so you can list fallbacks before you have the keys. A bare model
name means `gemini`. If `LLM_MODELS` is unset the legacy `GEMINI_MODEL` list is used.

Time limits per question: 50 s LLM budget (`ANSWER_BUDGET_SEC`), 40 s per LLM request, 20 s per SQL query,
3 SQL attempts, 2 answer-writing attempts, then a template answer built directly from the rows.

## Tests

```bash
python -X utf8 -m pytest tests -q                 # 124 offline tests, no LLM, ~10 s (needs data/uzex.db for a few)
python -X utf8 -m pytest tests/test_llm.py -q     # only the LLM chain logic (fake providers)
python -X utf8 -m pytest tests/test_golden_offline.py -q   # golden SQL still gives the expected values on the DB

python -X utf8 scripts/run_questions.py [tests/questions.txt] [tests/report.md]
#   runs every question through the live agent, writes a Markdown report (answer, interpretation, SQL, timing)

python -X utf8 scripts/golden_check.py [--ids g01,g05] [--tags trap,brokers] [--limit N]
#   runs tests/golden.jsonl through the live agent and checks each answer contains the expected
#   numbers / strings (or correctly refuses); exit code 1 on any failure; costs LLM quota
```

`tests/golden.jsonl` holds 40 questions (20 uz / 20 ru) with hand-written ground-truth SQL and expected values,
including 6 traps (missing deal number, data outside the period, people/phones, gold, forecasts).

## Project layout

```
.
├── bot.py                     Telegram bot entry point (aiogram 3): commands, per-chat queue, evidence block
├── cli.py                     Ask one question from the terminal
├── requirements.txt           google-genai, aiogram, python-dotenv, rapidfuzz, anthropic, openai
├── .env.example               All configuration variables with comments
├── TAHLIL.md                  Requirements, scoring and data-trap analysis (uz)
├── docs/
│   └── SOLUTION.md            Solution description for the jury (uz + ru)
├── app/
│   ├── agent.py               Question -> plan JSON -> SQL -> rows -> prose -> verify -> fallback; time budget; QA log
│   ├── schema_prompt.py       DB schema + SQL rules shown to the LLM (single source of truth)
│   ├── sql_guard.py           Read-only SQL execution: SELECT-only, forbidden keywords, 20 s timeout, LIMIT 50
│   ├── verify.py              Grounding check: numbers / BK codes / dates / company names must exist in rows
│   ├── entities.py            Entity resolution in code: products (TN VED), companies (INN), brokers, deal numbers
│   ├── dictionaries.py        40 TN VED products (ru/uz/aliases), regions, statuses, grade words, data period
│   ├── normalize.py           Number/date parsing, grade/class parsing, Cyrillic->Latin translit, company_key
│   ├── format.py              Telegram HTML / plain rendering of an answer with its evidence block
│   └── llm/
│       ├── client.py          Fallback chain over providers, retries, deadline
│       ├── providers.py       Gemini / Anthropic / OpenAI adapters (lazy SDK import)
│       └── base.py            LlmResponse, Provider protocol, retryable-error classification, 40 s timeout
├── scripts/
│   ├── build_db.py            CSV -> normalized SQLite with derived columns and indexes
│   ├── run_questions.py       Live run of tests/questions.txt -> tests/report.md
│   └── golden_check.py        Live run of tests/golden.jsonl with pass/fail per entry
├── tests/
│   ├── test_offline.py        normalize, sql_guard, verify
│   ├── test_agent.py          agent flow with a fake LLM (retry, fallback, deadline)
│   ├── test_entities.py       entity resolution
│   ├── test_llm.py            provider chain logic
│   ├── test_bot.py            message splitting, chat locks/history
│   ├── test_format.py         rendering
│   ├── test_golden_offline.py golden SQL vs DB
│   ├── golden.jsonl           40 golden questions with ground-truth SQL and expected values
│   ├── questions.txt          Questions for run_questions.py
│   └── report.md              Last live run (git-ignored)
├── deploy/                    Dockerfile, docker-compose.yml, systemd unit, Windows restart loop, deploy README
├── data/
│   ├── raw/uzex_spot_data/    Source CSVs (git-ignored)
│   └── uzex.db                Built database (git-ignored)
└── logs/qa.jsonl              One JSON line per answered question (git-ignored)
```

## Deployment

See [deploy/README.md](deploy/README.md): Windows PowerShell restart loop, Linux systemd unit, Docker Compose,
and the jury-day checklist. Only one process may poll a bot token at a time.
