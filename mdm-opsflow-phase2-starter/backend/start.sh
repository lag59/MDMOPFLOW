#!/bin/sh
set -e

export PYTHONPATH=/app

# Run schema migrations before API startup to keep DB changes migration-driven.
until alembic upgrade head; do
  echo "Waiting for database and retrying migrations..."
  sleep 2
done

exec python -m uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8080}
