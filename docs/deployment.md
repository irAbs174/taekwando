# TEAKWONDO Production Deployment Guide

This guide covers deploying **TEAKWONDO** (Django 5.2 LTS) to production using either **Docker Compose** (recommended) or a hardened **Ubuntu/Debian Linux VPS** (`systemd` + `Gunicorn` + `Nginx` + Let's Encrypt HTTPS).

---

## 1. Environment Configuration (`.env`)

Never run production with `DJANGO_DEBUG=True` or default secrets. Copy `.env.example` to `.env`, set permissions to `0600`, and generate a fresh cryptographic secret key:

```bash
cp .env.example .env
chmod 600 .env
python3 -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

Required production environment variables:

```ini
DJANGO_SETTINGS_MODULE=config.settings.production
DJANGO_DEBUG=False
DJANGO_SECRET_KEY=<generated-64-char-random-secret>
DJANGO_ALLOWED_HOSTS=teakwondo.example.com,www.teakwondo.example.com
DJANGO_CSRF_TRUSTED_ORIGINS=https://teakwondo.example.com,https://www.teakwondo.example.com
SITE_BASE_URL=https://teakwondo.example.com

# Obscured Django Admin URL (always keep trailing slash)
DJANGO_ADMIN_URL=club-control-9f3a2c/

# SQLite storage path (placed on persistent volume with mode 0600)
DB_ENGINE=django.db.backends.sqlite3
SQLITE_DB_PATH=/app/data/db.sqlite3

# Private certificate & evidence acceleration via Nginx internal location
USE_X_ACCEL_REDIRECT=True
X_ACCEL_REDIRECT_PREFIX=/_private_media

# Production SMTP for password reset & operational alerts
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.example.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=noreply@teakwondo.example.com
EMAIL_HOST_PASSWORD=<smtp-secret>
DEFAULT_FROM_EMAIL=TEAKWONDO <noreply@teakwondo.example.com>

# Optional Sentry Error & Performance Monitoring
SENTRY_DSN=
SENTRY_ENVIRONMENT=production
SENTRY_TRACES_SAMPLE_RATE=0.1
```

---

## 2. Option A — Docker Compose Deployment (Recommended)

1. Provision TLS certificates with Certbot into `./deploy/certs` and update `server_name` and certificate paths in `deploy/nginx.conf`.
2. Build and launch the stack:

```bash
docker compose build --pull
docker compose up -d
```

3. Verify security configuration and service health:

```bash
docker compose exec web python manage.py check --deploy
curl -fsS https://teakwondo.example.com/healthz/
```

4. Create your initial `SUPER_ADMIN` account and optional starter data:

```bash
docker compose exec web python manage.py createsuperuser
docker compose exec web python manage.py seed_teakwondo
```

5. Trigger an immediate verified SQLite backup:

```bash
docker compose exec web python manage.py backup_sqlite --output-dir /app/backups --keep 30
```

---

## 3. Option B — Ubuntu/Debian VPS (`systemd` + `Gunicorn` + `Nginx`)

```bash
# 1. System packages & unprivileged user
sudo apt-get update && sudo apt-get install -y python3.12 python3.12-venv nginx certbot python3-certbot-nginx gettext sqlite3
sudo useradd --system --home /srv/teakwondo --shell /usr/sbin/nologin teakwondo

# 2. Application checkout & virtual environment
sudo mkdir -p /srv/teakwondo/{data,media,private_media,staticfiles,logs,backups}
sudo chown -R teakwondo:www-data /srv/teakwondo
sudo chmod 750 /srv/teakwondo/{data,private_media,backups}

cd /srv/teakwondo
sudo -u teakwondo python3.12 -m venv .venv
sudo -u teakwondo .venv/bin/pip install --upgrade pip -r requirements.txt

# 3. Database migration, RBAC setup, translations, static files & deploy audit
sudo -u teakwondo DJANGO_SETTINGS_MODULE=config.settings.production .venv/bin/python manage.py check --deploy
sudo -u teakwondo DJANGO_SETTINGS_MODULE=config.settings.production .venv/bin/python manage.py migrate --noinput
sudo chmod 600 /srv/teakwondo/data/db.sqlite3
sudo -u teakwondo DJANGO_SETTINGS_MODULE=config.settings.production .venv/bin/python manage.py setup_roles
sudo -u teakwondo DJANGO_SETTINGS_MODULE=config.settings.production .venv/bin/python manage.py compile_translations
sudo -u teakwondo DJANGO_SETTINGS_MODULE=config.settings.production .venv/bin/python manage.py collectstatic --noinput
sudo -u teakwondo DJANGO_SETTINGS_MODULE=config.settings.production .venv/bin/python manage.py createsuperuser

# 4. Enable Gunicorn systemd service, Nginx reverse proxy, Let's Encrypt, logrotate & backup cron
sudo cp deploy/teakwondo.service /etc/systemd/system/teakwondo.service
sudo systemctl daemon-reload && sudo systemctl enable --now teakwondo

sudo cp deploy/nginx.conf /etc/nginx/sites-available/teakwondo
sudo ln -sf /etc/nginx/sites-available/teakwondo /etc/nginx/sites-enabled/teakwondo
sudo nginx -t && sudo systemctl reload nginx
sudo certbot --nginx -d teakwondo.example.com -d www.teakwondo.example.com

sudo cp deploy/logrotate-teakwondo.conf /etc/logrotate.d/teakwondo
sudo chmod +x /srv/teakwondo/deploy/backup_cron.sh
echo "30 2 * * * teakwondo /srv/teakwondo/deploy/backup_cron.sh >> /srv/teakwondo/logs/backup.log 2>&1" | sudo tee /etc/cron.d/teakwondo-backup
```

---

## 4. Private Media Protection Verification

After deploying, verify that athlete certificates and medal evidence can never be accessed directly:

```bash
# Must return 403 or 404
curl -I https://teakwondo.example.com/_private_media/medals/2026/11/test.pdf
curl -I https://teakwondo.example.com/media/certificates/2026/11/test.pdf

# Must redirect (302) anonymous users to login
curl -I https://teakwondo.example.com/protected-media/medal/1/
```

---

## 5. Logging, Monitoring & Health Checks

- **Liveness / Database Readiness**: `GET /healthz/` executes `SELECT 1` and returns `{"status": "ok", "database": "ok"}` (HTTP `200`) or HTTP `503` on failure.
- **Application & Security Logs**: Written to `logs/teakwondo.log` and `logs/security.log` (failed logins, rate-limit lockouts, permission denials), rotated via `deploy/logrotate-teakwondo.conf`.
- **Audit & Review Trail**: Immutable database records in `audit_logs.AuditLog` and `core.ReviewLog`, inspectable by `CLUB_MANAGER` and `SUPER_ADMIN`.
- **Error Tracking**: Set `SENTRY_DSN` in `.env` to activate automatic `sentry-sdk` Django integration (with `send_default_pii=False`).

---

## 6. Future Migration from SQLite to PostgreSQL (Zero Code Redesign)

All models, constraints, indexes, and queries use pure database-agnostic Django ORM primitives. To migrate to PostgreSQL when concurrent write traffic grows:

1. Take a verified backup (`python manage.py backup_sqlite`) and put the site in brief maintenance mode.
2. Export logical data:
   ```bash
   python manage.py dumpdata --natural-foreign --natural-primary \
     --exclude contenttypes --exclude auth.permission --indent 2 > teakwondo_export.json
   ```
3. Install `psycopg[binary]` and update `.env`:
   ```ini
   DB_ENGINE=django.db.backends.postgresql
   DB_NAME=teakwondo
   DB_USER=teakwondo_app
   DB_PASSWORD=<strong-password>
   DB_HOST=127.0.0.1
   DB_PORT=5432
   DB_CONN_MAX_AGE=60
   ```
4. Apply migrations, load data, and re-sync RBAC groups:
   ```bash
   python manage.py migrate --noinput
   python manage.py loaddata teakwondo_export.json
   python manage.py setup_roles
   ```
