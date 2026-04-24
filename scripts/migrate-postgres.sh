#!/bin/bash
# One-shot Postgres 9.6 -> 15 migration for PyDDNS.
#
# Brings up postgres-old (9.6) and postgres (15) side by side, runs
# pg_dump from the former and psql restore into the latter, then exits.
# Safe to re-run: prep-migration is idempotent and pg_dump uses --clean.

set -euo pipefail
cd "$(dirname "$0")/.."

echo "=== PyDDNS Postgres 9.6 -> 15 migration ==="
echo
echo "This will:"
echo "  1. Rename data/dbdata -> data/dbdata-old (preserves your 9.6 cluster)"
echo "  2. Start postgres 9.6 on data/dbdata-old and postgres 15 on a fresh data/dbdata"
echo "  3. pg_dump from 9.6 and psql restore into 15"
echo "  4. Stop all migration services on success"
echo
echo "Your application stack (python, nginx) is NOT started during migration."
echo

if [ ! -d data/dbdata ] && [ ! -d data/dbdata-old ]; then
    echo "Error: neither data/dbdata nor data/dbdata-old exists. Nothing to migrate."
    exit 1
fi

read -r -p "Continue? [y/N] " response
case "$response" in
    [yY]|[yY][eE][sS]) ;;
    *) echo "Aborted."; exit 0 ;;
esac

echo
echo "==> Running migration profile..."
COMPOSE_PROFILES=migration docker compose up \
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
