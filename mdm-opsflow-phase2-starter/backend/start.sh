#!/bin/sh
set -e

export PYTHONPATH=/app

# Fail-closed: startup is blocked unless deterministic migrations succeed.
python /app/scripts/run_migrations_safely.py

exec python -m uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8080}
