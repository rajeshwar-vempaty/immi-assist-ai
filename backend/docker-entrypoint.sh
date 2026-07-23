#!/bin/sh
set -e

cd /app

echo "Running database migrations..."
if ! alembic upgrade head; then
  echo "Alembic upgrade failed; attempting init_db fallback for fresh installs..."
  python -c "from app.db.init_db import init_db; init_db()"
fi

if [ "${RUN_INGEST_ON_START:-false}" = "true" ]; then
  echo "Running knowledge-base ingest..."
  python /app/repo_scripts/ingest_uscis_data.py --yes
fi

exec "$@"
