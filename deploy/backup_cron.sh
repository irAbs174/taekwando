#!/usr/bin/env bash
# =============================================================================
# TEAKWONDO — Automated SQLite + Media Backup Script (for cron / systemd timer)
# Example crontab (runs daily at 02:30 UTC):
#   30 2 * * * /srv/teakwondo/deploy/backup_cron.sh >> /srv/teakwondo/logs/backup.log 2>&1
# =============================================================================
set -euo pipefail

APP_DIR="${APP_DIR:-/srv/teakwondo}"
PYTHON_BIN="${PYTHON_BIN:-${APP_DIR}/.venv/bin/python}"
BACKUP_DIR="${BACKUP_DIR:-${APP_DIR}/backups}"
KEEP_COUNT="${BACKUP_RETENTION_COUNT:-30}"
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"

mkdir -p "${BACKUP_DIR}"
chmod 700 "${BACKUP_DIR}"

cd "${APP_DIR}"

echo "[${STAMP}] Starting verified online SQLite backup..."
"${PYTHON_BIN}" manage.py backup_sqlite --output-dir "${BACKUP_DIR}" --keep "${KEEP_COUNT}"

# Archive public and private uploads with restrictive permissions
MEDIA_ARCHIVE="${BACKUP_DIR}/teakwondo_media_${STAMP}.tar.gz"
tar -czf "${MEDIA_ARCHIVE}" \
    --ignore-failed-read \
    -C "${APP_DIR}" media private_media
chmod 600 "${MEDIA_ARCHIVE}"
sha256sum "${MEDIA_ARCHIVE}" > "${MEDIA_ARCHIVE}.sha256"
chmod 600 "${MEDIA_ARCHIVE}.sha256"

# Prune old media archives beyond KEEP_COUNT
ls -1t "${BACKUP_DIR}"/teakwondo_media_*.tar.gz 2>/dev/null | tail -n +$((KEEP_COUNT + 1)) | while read -r old; do
    rm -f "${old}" "${old}.sha256"
done

echo "[${STAMP}] Backup completed successfully."
