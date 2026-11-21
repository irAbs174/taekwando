#!/usr/bin/env sh
set -eu

echo "[TEAKWONDO] Applying database migrations..."
python manage.py migrate --noinput

# Restrict SQLite database file permissions when using SQLite
DB_FILE="${SQLITE_DB_PATH:-/app/db.sqlite3}"
if [ -f "$DB_FILE" ]; then
    chmod 600 "$DB_FILE" || true
fi

echo "[TEAKWONDO] Synchronizing RBAC role groups and permissions..."
python manage.py setup_roles

echo "[TEAKWONDO] Compiling localization catalogs (fa & ja)..."
python manage.py compile_translations

echo "[TEAKWONDO] Collecting static assets..."
python manage.py collectstatic --noinput

echo "[TEAKWONDO] Starting application process..."
exec "$@"
