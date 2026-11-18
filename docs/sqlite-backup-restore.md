# SQLite Backup, Integrity Verification & Restore Guide

TECHWANDO runs SQLite in **WAL (Write-Ahead Logging)** mode with `PRAGMA foreign_keys = ON`, `synchronous = NORMAL`, and `busy_timeout = 20000` (20 s), avoiding raw `cp` file copies while the database is live.

---

## 1. Creating a Consistent Online Backup

Use the built-in `backup_sqlite` management command, which leverages Python's `sqlite3.Connection.backup()` API in read-only URI mode, verifies the resulting snapshot with `PRAGMA integrity_check`, enforces `0600` file permissions, writes a `.sha256` checksum, and rotates older snapshots:

```bash
.venv/bin/python manage.py backup_sqlite --output-dir ./backups --keep 30
```

Artifacts created:
- `backups/techwando_YYYYMMDDTHHMMSSZ.sqlite3` (mode `0600`)
- `backups/techwando_YYYYMMDDTHHMMSSZ.sqlite3.sha256` (mode `0600`)

---

## 2. Backing Up Uploaded Media Alongside SQLite

Run `deploy/backup_cron.sh` to snapshot SQLite **plus** both `media/` (public uploads) and `private_media/` (protected athlete certificates & medal evidence):

```bash
APP_DIR=/srv/techwando BACKUP_DIR=/srv/techwando/backups ./deploy/backup_cron.sh
```

Copy encrypted backups off-host daily (e.g., `rclone`, `restic`, or `borgbackup` to object storage). Never commit `db.sqlite3` or backup archives to Git or place them inside `static/` or `media/`.

---

## 3. Verifying a Backup Before Restore

```bash
cd /srv/techwando/backups
sha256sum --check techwando_20261117T023000Z.sqlite3.sha256
sqlite3 techwando_20261117T023000Z.sqlite3 "PRAGMA integrity_check; PRAGMA foreign_key_check;"
```

Both checks must return `ok` (and zero rows for `foreign_key_check`).

---

## 4. Restoring From a Backup

```bash
# 1. Stop application writers cleanly
sudo systemctl stop techwando        # or: docker compose stop web backup

# 2. Verify snapshot checksum & integrity
sha256sum --check /srv/techwando/backups/techwando_20261117T023000Z.sqlite3.sha256
sqlite3 /srv/techwando/backups/techwando_20261117T023000Z.sqlite3 "PRAGMA integrity_check;"

# 3. Preserve pre-restore database files (including -wal and -shm!)
STAMP=$(date -u +%Y%m%dT%H%M%SZ)
sudo mv /srv/techwando/data/db.sqlite3 "/srv/techwando/backups/pre_restore_${STAMP}.sqlite3"
sudo rm -f /srv/techwando/data/db.sqlite3-wal /srv/techwando/data/db.sqlite3-shm

# 4. Install verified snapshot with strict ownership & permissions
sudo cp /srv/techwando/backups/techwando_20261117T023000Z.sqlite3 /srv/techwando/data/db.sqlite3
sudo chown techwando:www-data /srv/techwando/data/db.sqlite3
sudo chmod 600 /srv/techwando/data/db.sqlite3

# 5. Restore media archive if required
sudo tar -xzf /srv/techwando/backups/techwando_media_20261117T023000Z.tar.gz -C /srv/techwando
sudo chown -R techwando:www-data /srv/techwando/media /srv/techwando/private_media
sudo chmod 750 /srv/techwando/private_media

# 6. Run any pending migrations, restart application & check health
sudo -u techwando DJANGO_SETTINGS_MODULE=config.settings.production /srv/techwando/.venv/bin/python /srv/techwando/manage.py migrate --noinput
sudo systemctl start techwando       # or: docker compose up -d web backup
curl -fsS https://techwando.example.com/healthz/
```
