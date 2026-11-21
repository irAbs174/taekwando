# SQLite Backup, Integrity Verification & Restore Guide

TEAKWONDO runs SQLite in **WAL (Write-Ahead Logging)** mode with `PRAGMA foreign_keys = ON`, `synchronous = NORMAL`, and `busy_timeout = 20000` (20 s), avoiding raw `cp` file copies while the database is live.

---

## 1. Creating a Consistent Online Backup

Use the built-in `backup_sqlite` management command, which leverages Python's `sqlite3.Connection.backup()` API in read-only URI mode, verifies the resulting snapshot with `PRAGMA integrity_check`, enforces `0600` file permissions, writes a `.sha256` checksum, and rotates older snapshots:

```bash
.venv/bin/python manage.py backup_sqlite --output-dir ./backups --keep 30
```

Artifacts created:
- `backups/teakwondo_YYYYMMDDTHHMMSSZ.sqlite3` (mode `0600`)
- `backups/teakwondo_YYYYMMDDTHHMMSSZ.sqlite3.sha256` (mode `0600`)

---

## 2. Backing Up Uploaded Media Alongside SQLite

Run `deploy/backup_cron.sh` to snapshot SQLite **plus** both `media/` (public uploads) and `private_media/` (protected athlete certificates & medal evidence):

```bash
APP_DIR=/srv/teakwondo BACKUP_DIR=/srv/teakwondo/backups ./deploy/backup_cron.sh
```

Copy encrypted backups off-host daily (e.g., `rclone`, `restic`, or `borgbackup` to object storage). Never commit `db.sqlite3` or backup archives to Git or place them inside `static/` or `media/`.

---

## 3. Verifying a Backup Before Restore

```bash
cd /srv/teakwondo/backups
sha256sum --check teakwondo_20261117T023000Z.sqlite3.sha256
sqlite3 teakwondo_20261117T023000Z.sqlite3 "PRAGMA integrity_check; PRAGMA foreign_key_check;"
```

Both checks must return `ok` (and zero rows for `foreign_key_check`).

---

## 4. Restoring From a Backup

```bash
# 1. Stop application writers cleanly
sudo systemctl stop teakwondo        # or: docker compose stop web backup

# 2. Verify snapshot checksum & integrity
sha256sum --check /srv/teakwondo/backups/teakwondo_20261117T023000Z.sqlite3.sha256
sqlite3 /srv/teakwondo/backups/teakwondo_20261117T023000Z.sqlite3 "PRAGMA integrity_check;"

# 3. Preserve pre-restore database files (including -wal and -shm!)
STAMP=$(date -u +%Y%m%dT%H%M%SZ)
sudo mv /srv/teakwondo/data/db.sqlite3 "/srv/teakwondo/backups/pre_restore_${STAMP}.sqlite3"
sudo rm -f /srv/teakwondo/data/db.sqlite3-wal /srv/teakwondo/data/db.sqlite3-shm

# 4. Install verified snapshot with strict ownership & permissions
sudo cp /srv/teakwondo/backups/teakwondo_20261117T023000Z.sqlite3 /srv/teakwondo/data/db.sqlite3
sudo chown teakwondo:www-data /srv/teakwondo/data/db.sqlite3
sudo chmod 600 /srv/teakwondo/data/db.sqlite3

# 5. Restore media archive if required
sudo tar -xzf /srv/teakwondo/backups/teakwondo_media_20261117T023000Z.tar.gz -C /srv/teakwondo
sudo chown -R teakwondo:www-data /srv/teakwondo/media /srv/teakwondo/private_media
sudo chmod 750 /srv/teakwondo/private_media

# 6. Run any pending migrations, restart application & check health
sudo -u teakwondo DJANGO_SETTINGS_MODULE=config.settings.production /srv/teakwondo/.venv/bin/python /srv/teakwondo/manage.py migrate --noinput
sudo systemctl start teakwondo       # or: docker compose up -d web backup
curl -fsS https://teakwondo.example.com/healthz/
```
