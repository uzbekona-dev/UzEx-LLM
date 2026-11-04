# Deployment

The bot is a single Python process that long-polls Telegram. It needs three things next to it:

| What | Where | How to get it |
|---|---|---|
| `.env` | repo root | `cp .env.example .env`, fill `TELEGRAM_BOT_TOKEN` and at least one of `GEMINI_API_KEY` / `ANTHROPIC_API_KEY` / `OPENAI_API_KEY` |
| `data/uzex.db` (~335 MB) | repo root | unzip the CSVs to `data/raw/uzex_spot_data/`, then `python -X utf8 scripts/build_db.py` (the DB is git-ignored: build it on the server or copy the file) |
| `logs/` | repo root | created automatically; `logs/qa.jsonl` gets one line per answered question |

> **Only ONE instance may poll a bot token at a time.** Telegram returns `409 Conflict` ("terminated by other
> getUpdates request") when two processes poll the same token, and both stop receiving messages. Before starting
> the bot on a server, stop every local copy (`cli.py` is fine — it does not poll). If you must switch machines,
> stop the old one first and wait ~10 s.

Pick one of the three ways below.

## 0. Web version (no Telegram needed)

The same agent is also served as a small web page (FastAPI + uvicorn, `web.py` + `web/index.html`), useful when
a jury member has no Telegram. It needs `.env` with an LLM key and `data/uzex.db`, but **not** `TELEGRAM_BOT_TOKEN`,
and it does not poll the bot token, so it can run next to the bot.

```bash
python -X utf8 -m uvicorn web:app --host 0.0.0.0 --port 8080
# open http://<host>:8080   health: curl http://localhost:8080/api/health
```

Linux: `sudo cp deploy/uzex-web.service /etc/systemd/system/ && sudo systemctl enable --now uzex-web`
(same paths/user as `uzex-bot.service`). The page is plain HTTP; put nginx/caddy with TLS in front if it is
exposed publicly. Each browser tab keeps its own session (last 2 turns of context, one question in flight at a time);
every answered question is appended to `logs/qa.jsonl` with `"channel": "web"`.

## 1. Windows (PowerShell restart loop)

```powershell
cd C:\www\UZEX-LLM
python -m venv .venv
.venv\Scripts\pip install -r requirements.txt
python -X utf8 scripts\build_db.py            # if data\uzex.db is missing
powershell -ExecutionPolicy Bypass -File deploy\run_bot.ps1
```

`deploy/run_bot.ps1` restarts `bot.py` 5 s after any exit, timestamps every line into `logs\bot.log`, and
stops on Ctrl+C. Keep the window open, or run it in a detached session so it survives logging off:

```powershell
# as a Scheduled Task that starts at boot and restarts on failure
$action  = New-ScheduledTaskAction -Execute "powershell.exe" `
           -Argument "-ExecutionPolicy Bypass -WindowStyle Hidden -File C:\www\UZEX-LLM\deploy\run_bot.ps1"
$trigger = New-ScheduledTaskTrigger -AtStartup
$settings = New-ScheduledTaskSettingsSet -RestartCount 999 -RestartInterval (New-TimeSpan -Minutes 1) `
            -ExecutionTimeLimit ([TimeSpan]::Zero)
Register-ScheduledTask -TaskName "uzex-bot" -Action $action -Trigger $trigger -Settings $settings -RunLevel Highest
Start-ScheduledTask -TaskName "uzex-bot"
```

Disable Windows sleep/hibernate on the machine (`powercfg /change standby-timeout-ac 0`).

## 2. Linux (systemd)

```bash
sudo mkdir -p /opt/uzex-bot && sudo chown $USER /opt/uzex-bot
git clone <repo> /opt/uzex-bot && cd /opt/uzex-bot
python3.12 -m venv .venv && .venv/bin/pip install -r requirements.txt
cp .env.example .env && nano .env                     # token + keys
.venv/bin/python -X utf8 scripts/build_db.py          # or scp data/uzex.db from your machine

sudo useradd --system --home /opt/uzex-bot --shell /usr/sbin/nologin uzex
sudo chown -R uzex:uzex /opt/uzex-bot
sudo cp deploy/uzex-bot.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now uzex-bot
systemctl status uzex-bot
journalctl -u uzex-bot -f                             # live log
```

The unit has `Restart=always`, `RestartSec=5`, `EnvironmentFile=/opt/uzex-bot/.env`, and
`WorkingDirectory=/opt/uzex-bot`. Adjust the paths in the unit if you install elsewhere.

## 3. Docker Compose

```bash
cd <repo root>
cp .env.example .env && nano .env
docker compose run --rm build-db                     # builds data/uzex.db from data/raw (once)
docker compose up -d --build
docker compose logs -f
```

The image (`python:3.12-slim`) contains `app/`, `bot.py`, `cli.py`, `scripts/`; `./data` is mounted at
`/app/data` read-only and `./logs` at `/app/logs`; `restart: unless-stopped`. Ask a question inside the
container: `docker exec uzex-bot python -X utf8 cli.py "15.06.2024 dollar kursi"`.

## Jury-day checklist (bot must run from 2026-11-05 18:00 Tashkent until the evaluation)

- [ ] `.env` has `TELEGRAM_BOT_TOKEN` and at least one LLM key; the chain in `LLM_MODELS` lists a fallback
      vendor whose key is also set (one vendor outage must not stop the bot).
- [ ] `data/uzex.db` exists (~335 MB) and `python -X utf8 -m pytest tests -q` passes on the machine that runs the bot.
- [ ] Exactly one process polls the token (no local `bot.py` left running, no second server).
- [ ] The bot answers `/start` and one real question from a phone, e.g. `15.06.2024 dollar kursi` → `11 862.46`.
- [ ] `logs/qa.jsonl` grows with every question (`tail -f logs/qa.jsonl` / `Get-Content logs\qa.jsonl -Wait`);
      the `verified` field is `true` and `elapsed_sec` is well under 90.
- [ ] Supervisor in place: `run_bot.ps1` / `systemctl is-active uzex-bot` / `docker ps` shows `Up`;
      kill the process once and confirm it comes back within ~10 s.
- [ ] Machine will not sleep, reboot for updates, or lose network; power and internet are stable.
- [ ] LLM quota: check the vendor dashboards; one question costs 2–3 LLM calls (~10–20k input tokens).
- [ ] Clock is correct (relative dates like "this year" are computed against the data, not the clock, but logs
      and vendor auth depend on it).
- [ ] Someone can check `logs/bot.log` / `journalctl -u uzex-bot` during the evaluation window.
