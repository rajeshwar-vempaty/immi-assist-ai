# Scheduler — periodic USCIS scrape + ingest
# Build from repository root:
#   docker build -f deploy/scheduler/Dockerfile .

FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential curl && \
    rm -rf /var/lib/apt/lists/*

COPY backend/requirements.txt ./backend/requirements.txt
RUN pip install --no-cache-dir -r backend/requirements.txt

COPY backend/ ./backend/
COPY scripts/ ./scripts/

ENV PYTHONPATH=/app/backend
ENV INGEST_INTERVAL_HOURS=168
ENV RUN_REFRESH_ON_START=false

CMD ["python", "scripts/scheduled_refresh.py"]
