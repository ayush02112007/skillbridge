#!/usr/bin/env bash
# Start an API instance for the Playwright suite.
#
# Deliberately isolated from your development database: e2e tests register
# accounts and move applications through their lifecycle, and those writes
# should not land in the data you were looking at. The database file is
# recreated from scratch on every run so the suite starts from a known seed.
set -euo pipefail

cd "$(dirname "$0")/.."

# Playwright starts this script itself, so it cannot rely on a virtualenv
# having been activated in the calling shell. Find an interpreter that has the
# project's dependencies, in order of specificity.
if [ -n "${PYTHON:-}" ]; then
  PY="$PYTHON"
elif [ -x ".venv/bin/python" ]; then
  PY=".venv/bin/python"
elif [ -x "../.venv/bin/python" ]; then
  PY="../.venv/bin/python"
elif [ -x "env/bin/python" ]; then
  PY="env/bin/python"
elif command -v python3 >/dev/null 2>&1; then
  PY="python3"
else
  echo "[e2e] no Python interpreter found. Create backend/.venv and install" >&2
  echo "      requirements.txt, or set PYTHON=/path/to/python." >&2
  exit 1
fi

echo "[e2e] using interpreter: $PY"

export ENVIRONMENT=development
export DEBUG=false
export DATABASE_URL="sqlite+aiosqlite:///./var/e2e.db"
export CACHE_ENABLED=false
export CELERY_TASK_ALWAYS_EAGER=true
export EMAIL_PROVIDER=console
export STORAGE_PROVIDER=local
export STORAGE_LOCAL_PATH=./var/e2e-uploads
export AI_PROVIDER=deterministic
export REQUIRE_EMAIL_VERIFICATION=false
# The suite makes many requests in a short window; the limiter is exercised
# by its own backend test rather than throttling every page load here.
export RATE_LIMIT_AUTH_PER_MINUTE=1000
export RATE_LIMIT_DEFAULT_PER_MINUTE=10000

if ! "$PY" -c "import app.main" >/dev/null 2>&1; then
  echo "[e2e] $PY cannot import the application with the e2e settings." >&2
  echo "      Install the backend first:" >&2
  echo "      python3 -m venv .venv && .venv/bin/pip install -r requirements.txt" >&2
  "$PY" -c "import app.main" 2>&1 | tail -5 >&2
  exit 1
fi

mkdir -p var
if [ "${E2E_KEEP_DB:-false}" != "true" ]; then
  # -wal and -shm must go too, or SQLite reports a disk I/O error.
  rm -f var/e2e.db var/e2e.db-wal var/e2e.db-shm
fi

if [ ! -f var/e2e.db ]; then
  echo "[e2e] creating and seeding the test database ..."
  "$PY" -m alembic upgrade head
  "$PY" -m seeds.seed --students 12
fi

echo "[e2e] starting API on :8000"
exec "$PY" -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --log-level warning
