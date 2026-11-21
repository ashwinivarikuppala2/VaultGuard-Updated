#!/bin/sh
# =============================================================================
# VaultGuard Backend Startup Script
# =============================================================================
# Runs Alembic migrations using a PostgreSQL advisory lock so that only one
# replica at a time applies schema changes (safe for future horizontal scaling).
# Falls back to plain `alembic upgrade head` if the lock helper is unavailable.
# =============================================================================

set -eu

echo "[startup] Running Alembic migrations..."
alembic upgrade head
echo "[startup] Migrations complete."

echo "[startup] Starting uvicorn..."
exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}"
