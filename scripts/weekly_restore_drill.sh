#!/usr/bin/env bash
set -euo pipefail

BACKUP_DIR="${BACKUP_DIR:-/opt/db-backups}"
PG_CONTAINER="${PG_CONTAINER:-budget-postgres}"
PG_USER="${PG_USER:-budget}"
RESTORE_DB="${RESTORE_DB:-budget_restore_drill}"

LATEST_BACKUP="$(ls -1t "$BACKUP_DIR"/*.sql 2>/dev/null | head -n1 || true)"
if [ -z "$LATEST_BACKUP" ]; then
  echo "[DEPLOY] No SQL backups found in $BACKUP_DIR"
  exit 1
fi

echo "[DEPLOY] Weekly restore drill using: $LATEST_BACKUP"

docker exec "$PG_CONTAINER" psql -U "$PG_USER" -c "DROP DATABASE IF EXISTS $RESTORE_DB;" >/dev/null

docker exec "$PG_CONTAINER" psql -U "$PG_USER" -c "CREATE DATABASE $RESTORE_DB;" >/dev/null

docker exec -i "$PG_CONTAINER" psql -U "$PG_USER" -d "$RESTORE_DB" < "$LATEST_BACKUP" >/dev/null

TABLE_COUNT="$(docker exec "$PG_CONTAINER" psql -U "$PG_USER" -d "$RESTORE_DB" -tAc "SELECT count(*) FROM information_schema.tables WHERE table_schema='public';")"

if [ "${TABLE_COUNT:-0}" -lt 1 ]; then
  echo "[DEPLOY] Restore drill failed: restored DB has no public tables"
  exit 1
fi

echo "[SUCCESS] Restore drill passed. Restored table count: $TABLE_COUNT"

docker exec "$PG_CONTAINER" psql -U "$PG_USER" -c "DROP DATABASE IF EXISTS $RESTORE_DB;" >/dev/null
