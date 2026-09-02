#!/usr/bin/env bash
#
# Run the backend test suite against a local Postgres database.
#
#   ./scripts/run-tests.sh                   # whole suite
#   ./scripts/run-tests.sh tests/test_auth.py -v
#   ./scripts/run-tests.sh -k "isolation"
#
# The suite DROPS AND RECREATES the public schema of its target database on
# every run, so it must never point at a database you care about. It defaults to
# a local `kastra_test`; override with TEST_DATABASE_URL to point elsewhere.
#
# No credentials live in this file. The database URL comes from the environment
# or is derived from .env; the JWT signing keys are throwaway values generated
# fresh for each run.

set -euo pipefail

cd "$(dirname "$0")/.."

# ── Database ────────────────────────────────────────────────────────────────
# Prefer an explicit TEST_DATABASE_URL. Otherwise reuse the credentials and host
# from .env's DATABASE_URL, swapping the database name for `kastra_test`.
if [[ -z "${TEST_DATABASE_URL:-}" ]]; then
  if [[ ! -f .env ]]; then
    echo "error: no TEST_DATABASE_URL set and no .env to derive one from." >&2
    echo "       export TEST_DATABASE_URL=postgresql+asyncpg://user:pass@host:5432/kastra_test" >&2
    exit 1
  fi
  base_url=$(grep -E '^DATABASE_URL=' .env | head -1 | cut -d= -f2-)
  if [[ -z "$base_url" ]]; then
    echo "error: DATABASE_URL not found in .env." >&2
    exit 1
  fi
  TEST_DATABASE_URL="${base_url%/*}/kastra_test"
fi
export TEST_DATABASE_URL

if [[ "$TEST_DATABASE_URL" != *_test* ]]; then
  echo "error: refusing to run — TEST_DATABASE_URL does not name a *_test database." >&2
  echo "       The suite drops the public schema of whatever it points at." >&2
  exit 1
fi

# ── Refuse to race another run ──────────────────────────────────────────────
# conftest drops and recreates the public schema at import time, so two suites
# pointed at one database silently corrupt each other: duplicate-key errors on
# registration, and cascading fixture failures that look like real regressions.
# Bail out instead of producing a misleading result.
db_name="${TEST_DATABASE_URL##*/}"
db_name="${db_name%%\?*}"
if command -v psql >/dev/null 2>&1; then
  # Credentials come from the URL we already have; never echoed.
  conn_no_driver="${TEST_DATABASE_URL/+asyncpg/}"
  active=$(psql "${conn_no_driver%/*}/postgres" -tAc \
    "select count(*) from pg_stat_activity where datname = '$db_name'" 2>/dev/null || echo 0)
  if [[ "${active:-0}" -gt 0 ]]; then
    echo "error: $active connection(s) are already using '$db_name'." >&2
    echo "       Another test run is in progress — it would be corrupted, and so would this one." >&2
    echo "       Wait for it to finish, or point TEST_DATABASE_URL at a different *_test database." >&2
    exit 1
  fi
fi

# ── Throwaway test config ───────────────────────────────────────────────────
# Generated per run: nothing here is a real secret, and nothing is committed.
export SECRET_KEY="${SECRET_KEY:-$(head -c 32 /dev/urandom | base64)}"
export REFRESH_SECRET_KEY="${REFRESH_SECRET_KEY:-$(head -c 32 /dev/urandom | base64)}"
export ENVIRONMENT=testing
export FRONTEND_URL="${FRONTEND_URL:-http://localhost:5200}"
export BACKEND_URL="${BACKEND_URL:-http://localhost:8080}"

echo "Running tests against ${TEST_DATABASE_URL%%:*}://…/${TEST_DATABASE_URL##*/}"
exec pytest "$@"
