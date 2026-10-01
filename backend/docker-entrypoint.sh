#!/usr/bin/env bash
# Wait for Postgres, apply migrations, optionally seed, then start the API.
set -euo pipefail

echo "[entrypoint] waiting for the database ..."
for attempt in $(seq 1 60); do
  if python -c "
import asyncio, sys
from app.core.database import ping_database
sys.exit(0 if asyncio.run(ping_database()) else 1)
" 2>/dev/null; then
    echo "[entrypoint] database is up"
    break
  fi
  if [ "$attempt" -eq 60 ]; then
    echo "[entrypoint] database did not become available in time" >&2
    exit 1
  fi
  sleep 2
done

echo "[entrypoint] applying migrations ..."
alembic upgrade head

if [ "${SEED_ON_START:-false}" = "true" ]; then
  echo "[entrypoint] seeding demo data ..."
  python -m seeds.seed || echo "[entrypoint] seed skipped or already applied"
fi

echo "[entrypoint] starting: $*"
exec "$@"
