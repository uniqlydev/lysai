#!/usr/bin/env bash
set -euo pipefail

echo "==> [pagila] starting idempotent init..."

# 1) Create DB if not exists
if ! psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -tAc "SELECT 1 FROM pg_database WHERE datname='pagila'" | grep -q 1; then
  echo "==> [pagila] creating database 'pagila'..."
  createdb -U "$POSTGRES_USER" -O "$POSTGRES_USER" pagila
else
  echo "==> [pagila] database 'pagila' already exists (ok)"
fi

# 2) Load schema if a sentinel table (actor) is missing
if ! psql -U "$POSTGRES_USER" -d pagila -tAc "SELECT 1 FROM information_schema.tables WHERE table_schema='public' AND table_name='actor'" | grep -q 1; then
  echo "==> [pagila] loading schema..."
  psql -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d pagila -f /opt/pagila/pagila-schema.sql
else
  echo "==> [pagila] schema already present (ok)"
fi

# 3) Load data if film table is empty or absent
if ! psql -U "$POSTGRES_USER" -d pagila -tAc "SELECT 1 FROM information_schema.tables WHERE table_name='film'" | grep -q 1; then
  echo "==> [pagila] loading data (no film table)..."
  psql -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d pagila -f /opt/pagila/pagila-data.sql
else
  FILM_COUNT=$(psql -U "$POSTGRES_USER" -d pagila -tAc "SELECT COUNT(*) FROM film" || echo 0)
  if [ "${FILM_COUNT:-0}" -eq 0 ]; then
    echo "==> [pagila] loading data (film table empty)..."
    psql -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d pagila -f /opt/pagila/pagila-data.sql
  else
    echo "==> [pagila] data already present (film count: $FILM_COUNT)"
  fi
fi

echo "==> [pagila] init complete."