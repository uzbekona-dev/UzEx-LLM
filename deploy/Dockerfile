# Build from the repository root:  docker build -f deploy/Dockerfile -t uzex-bot .
# data/uzex.db is NOT baked in: mount ./data as a volume (see docker-compose.yml).
FROM python:3.12-slim

ENV PYTHONIOENCODING=utf-8 \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY app ./app
COPY bot.py cli.py ./
COPY scripts ./scripts

# data/ (uzex.db, read-only) and logs/ (qa.jsonl, bot.log) are volumes
RUN mkdir -p /app/data /app/logs
VOLUME ["/app/data", "/app/logs"]

CMD ["python", "-X", "utf8", "bot.py"]
