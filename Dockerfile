# syntax=docker/dockerfile:1
# =============================================================================
# TEAKWONDO — Production Multi-Stage Dockerfile (Django 5.2 LTS + Gunicorn)
# =============================================================================
FROM python:3.12-slim-bookworm AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libjpeg62-turbo-dev \
    zlib1g-dev \
    libwebp-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /build
COPY requirements.txt .
RUN python -m venv /opt/venv \
    && /opt/venv/bin/pip install --upgrade pip wheel \
    && /opt/venv/bin/pip install -r requirements.txt


FROM python:3.12-slim-bookworm AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:$PATH" \
    DJANGO_SETTINGS_MODULE="config.settings.production" \
    APP_HOME="/app"

# Install runtime shared libraries, gettext (msgfmt), sqlite3 CLI, and curl for healthchecks
RUN apt-get update && apt-get install -y --no-install-recommends \
    gettext \
    sqlite3 \
    libjpeg62-turbo \
    zlib1g \
    libwebp7 \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd --system --gid 1001 teakwondo \
    && useradd --system --uid 1001 --gid teakwondo --home-dir /app --shell /usr/sbin/nologin teakwondo

WORKDIR /app
COPY --from=builder /opt/venv /opt/venv
COPY --chown=teakwondo:teakwondo . /app

RUN mkdir -p /app/data /app/staticfiles /app/media /app/private_media /app/logs /app/backups \
    && chmod +x /app/deploy/entrypoint.sh /app/deploy/backup_cron.sh \
    && chmod 750 /app/private_media /app/data /app/backups \
    && python manage.py compile_translations \
    && DJANGO_SETTINGS_MODULE=config.settings.development \
       DJANGO_SECRET_KEY="build-time-collectstatic-placeholder-key" \
       python manage.py collectstatic --noinput --clear \
    && chown -R teakwondo:teakwondo /app

USER teakwondo

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD curl --fail --silent http://127.0.0.1:8000/healthz/ || exit 1

ENTRYPOINT ["/app/deploy/entrypoint.sh"]
CMD ["gunicorn", "config.wsgi:application", "--config", "/app/deploy/gunicorn.conf.py"]
