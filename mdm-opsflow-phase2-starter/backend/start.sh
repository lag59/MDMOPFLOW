#!/bin/sh
set -e

export PYTHONPATH=/app

# Run schema migrations before API startup to keep DB changes migration-driven.
# Avoid an infinite crash loop if a non-critical migration fails in production.
attempt=1
max_retries=${MIGRATION_MAX_RETRIES:-20}
until alembic upgrade head; do
  if [ "$attempt" -ge "$max_retries" ]; then
    echo "Migrations failed after $max_retries attempts; starting API to keep auth and core routes available."
    break
  fi

  echo "Migration attempt $attempt failed; retrying..."
  attempt=$((attempt + 1))
  sleep 2
done

exec python -m uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8080}
