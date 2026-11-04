# Build from the repository root:  docker build -t uzex-bot .
# data/uzex.db is built inside the image from data/raw (if present) — or mount ./data as a volume.
FROM python:3.12-slim

ENV PYTHONIOENCODING=utf-8 \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY app ./app
COPY scripts ./scripts
COPY bot.py cli.py web.py ./
COPY web ./web

# data/ (uzex.db, read-only) and logs/ (qa.jsonl) are volumes mounted by docker-compose
RUN mkdir -p /app/data /app/logs
VOLUME ["/app/data", "/app/logs"]

CMD ["python", "-X", "utf8", "bot.py"]
