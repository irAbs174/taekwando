"""Production Gunicorn configuration for TEAKWONDO."""
import multiprocessing
import os

bind = os.environ.get("GUNICORN_BIND", "0.0.0.0:8000")

# Keep worker count conservative for SQLite WAL write serialization (2-4 workers);
# scale higher automatically once migrated to PostgreSQL.
default_workers = min(4, max(2, multiprocessing.cpu_count()))
workers = int(os.environ.get("GUNICORN_WORKERS", default_workers))
threads = int(os.environ.get("GUNICORN_THREADS", 2))
worker_class = "gthread"

timeout = int(os.environ.get("GUNICORN_TIMEOUT", 60))
graceful_timeout = 30
keepalive = 5

# Mitigate memory growth and slow-client/oversized header abuse
max_requests = 1200
max_requests_jitter = 150
limit_request_line = 4094
limit_request_fields = 100
limit_request_field_size = 8190

accesslog = os.environ.get("GUNICORN_ACCESS_LOG", "-")
errorlog = os.environ.get("GUNICORN_ERROR_LOG", "-")
loglevel = os.environ.get("GUNICORN_LOG_LEVEL", "info")
capture_output = True
forwarded_allow_ips = os.environ.get("GUNICORN_FORWARDED_ALLOW_IPS", "127.0.0.1,172.16.0.0/12")
