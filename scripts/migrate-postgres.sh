#!/bin/bash
# One-shot Postgres 9.6 -> 15 migration for PyDDNS.
#
# Brings up postgres-old (9.6) and postgres (15) side by side, runs
# pg_dump from the former and psql restore into the latter, then exits.
# Safe to re-run: prep-migration is idempotent and pg_dump uses --clean.
#
# Before touching the data, the script validates that .env contains the
# variables required for PyDDNS v3 to start after the migration completes.
# This avoids the situation where the DB migrates fine but the app then
# fails to boot because of a missing DJANGO_SECRET_KEY etc.

set -euo pipefail
cd "$(dirname "$0")/.."

# ── pre-flight ──────────────────────────────────────────────────────────────

preflight() {
    if [ ! -f .env ]; then
        echo "✗ .env not found. Copy .env-demo to .env and configure it before running this." >&2
        exit 1
    fi

    # Required for the v3 runtime to start. DJANGO_SECRET_KEY and
    # DJANGO_ALLOWED_HOSTS are new in v3 — v1/v2 deployments won't have them.
    local required=(
        DOMAIN
        SHARED_SECRET
        DJANGO_SECRET_KEY
        DJANGO_ALLOWED_HOSTS
        DATABASE_NAME
        DATABASE_USER
        DATABASE_PASS
    )

    local missing=()
    for v in "${required[@]}"; do
        # Match `VAR=<non-whitespace>...` (skip blank or whitespace-only values)
        if ! grep -qE "^${v}=[^[:space:]].*$" .env; then
            missing+=("$v")
        fi
    done

    if [ ${#missing[@]} -gt 0 ]; then
        echo "✗ Missing or empty in .env:" >&2
        for v in "${missing[@]}"; do
            echo "    - $v" >&2
        done
        echo >&2
        echo "These variables are required for the v3 stack to start after the migration." >&2
        echo "DJANGO_SECRET_KEY and DJANGO_ALLOWED_HOSTS are new in v3 — v1/v2 .env files" >&2
        echo "do not include them. See README → 'Migrating from Postgres 9.6' for the full list." >&2
        echo >&2
        echo "Tip: generate a Django secret key with:" >&2
        echo "    docker run --rm python:3.11-slim python -c \\" >&2
        echo "      \"import secrets; print(secrets.token_urlsafe(50))\"" >&2
        exit 1
    fi
}

# ── main ────────────────────────────────────────────────────────────────────

echo "=== PyDDNS Postgres 9.6 -> 15 migration ==="
echo
echo "This will:"
echo "  1. Verify your .env has the variables PyDDNS v3 needs to boot"
echo "  2. Rename data/dbdata -> data/dbdata-old (preserves your 9.6 cluster)"
echo "  3. Start postgres 9.6 on data/dbdata-old and postgres 15 on a fresh data/dbdata"
echo "  4. pg_dump from 9.6 and psql restore into 15"
echo "  5. Stop all migration services on success"
echo
echo "Your application stack (python, nginx) is NOT started during migration."
echo

if [ ! -d data/dbdata ] && [ ! -d data/dbdata-old ]; then
    echo "Error: neither data/dbdata nor data/dbdata-old exists. Nothing to migrate."
    exit 1
fi

echo "==> Pre-flight checks..."
preflight
echo "  ✓ .env contains all required variables"
echo

read -r -p "Continue? [y/N] " response
case "$response" in
    [yY]|[yY][eE][sS]) ;;
    *) echo "Aborted."; exit 0 ;;
esac

echo
echo "==> Running migration overlay..."
docker compose \
    -f docker-compose.yml \
    -f docker-compose.migration.yml \
    up \
    --abort-on-container-exit \
    --exit-code-from migrator \
    prep-migration postgres-old postgres migrator

echo
echo "=== Migration finished successfully ==="
echo
echo "Resume normal operation with:"
echo "    docker compose down"
echo "    docker compose up -d"
echo
echo "Once you have verified the application works correctly, you can free disk:"
echo "    rm -rf data/dbdata-old"
