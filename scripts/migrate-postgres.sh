#!/bin/bash
# One-shot Postgres 9.6 -> 15 migration for PyDDNS.
#
# Brings up postgres-old (9.6) and postgres (15) side by side, runs
# pg_dump from the former and psql restore into the latter, then exits.
# Safe to re-run: prep-migration is idempotent and pg_dump uses --clean.
#
# Before touching the data, the script validates that .env contains the
# variables required for PyDDNS v2 to start after the migration completes.
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

    # Required for the v2 runtime to start. DJANGO_SECRET_KEY and
    # DJANGO_ALLOWED_HOSTS are new in v2 — v1 deployments won't have them.
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
        echo "These variables are required for the v2 stack to start after the migration." >&2
        echo "DJANGO_SECRET_KEY and DJANGO_ALLOWED_HOSTS are new in v2 — v1 .env files" >&2
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
echo "  1. Verify your .env has the variables PyDDNS v2 needs to boot"
echo "  2. Rename data/dbdata -> data/dbdata-old (preserves your 9.6 cluster)"
echo "  3. Start postgres 9.6 on data/dbdata-old and postgres 15 on a fresh data/dbdata"
echo "  4. pg_dump from 9.6 and psql restore into 15"
echo "  5. Reconcile Django migration history with v2 (move v1 migrations aside,"
echo "     re-mark 0001_initial as applied via --fake-initial)"
echo "  6. Stop all migration services on success"
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
echo "==> Reconciling Django migration history..."
# v1 deployments carried untracked, locally-generated migrations
# (0001_initial.py, possibly 0002+, 0003+...). v2 ships a single
# committed 0001_initial.py per app. The restored database already has
# the live schema, so we:
#   1. Move any *untracked* numbered migrations aside (preserve them).
#   2. Wipe the django_migrations table for our two apps (--fake zero).
#   3. Re-record v2's 0001_initial as applied (--fake-initial).
# Fresh installs (nothing untracked, nothing in django_migrations to clear)
# pass through this block as a no-op.

backup_dir="data/migrations-backup-$(date +%Y%m%d-%H%M%S)"
moved_any=0
for app_dir in appdata/pyddns/common/migrations appdata/pyddns/pyddns/migrations; do
    [ -d "$app_dir" ] || continue
    for f in "$app_dir"/[0-9][0-9][0-9][0-9]_*.py; do
        [ -f "$f" ] || continue
        if ! git ls-files --error-unmatch "$f" >/dev/null 2>&1; then
            mkdir -p "$backup_dir/$app_dir"
            mv "$f" "$backup_dir/$app_dir/$(basename "$f")"
            moved_any=1
            echo "  ↳ moved untracked: $f"
        fi
    done
    rm -rf "$app_dir/__pycache__"
done

if [ "$moved_any" -eq 1 ]; then
    echo "  ↳ backups in: $backup_dir"
fi

echo "  ↳ aligning django_migrations table with v2..."
# Bring postgres-15 back up (it was stopped by --abort-on-container-exit
# above) and run the fake-migrate against it. `docker compose run` will
# start `postgres` automatically because the python service depends on it.
docker compose run --rm python bash -c "
    set -e
    cd /usr/src/app
    python manage.py migrate common zero --fake >/dev/null 2>&1 || true
    python manage.py migrate pyddns zero --fake >/dev/null 2>&1 || true
    python manage.py migrate --fake-initial
" 2>&1 | sed 's/^/    /'

echo "  ✓ migration history reconciled"

# Tidy up — leave nothing running so the user follows up with `up -d`.
docker compose stop postgres >/dev/null 2>&1 || true

echo
echo "=== Migration finished successfully ==="
echo
echo "Resume normal operation with:"
echo "    docker compose down"
echo "    docker compose up -d"
echo
echo "Once you have verified the application works correctly, you can free disk:"
echo "    rm -rf data/dbdata-old"
