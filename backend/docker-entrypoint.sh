#!/bin/sh
set -e

cd /app
alembic upgrade head 2>/dev/null || python -c "from app.db.init_db import init_db; init_db()"

if [ "${RUN_INGEST_ON_START:-false}" = "true" ]; then
  python /app/repo_scripts/ingest_uscis_data.py --yes || true
fi

exec "$@"
