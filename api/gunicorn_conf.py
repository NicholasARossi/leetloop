"""Gunicorn configuration for Cloud Run deployment."""

import multiprocessing
import os

# Server socket
bind = f"0.0.0.0:{os.environ.get('PORT', '8080')}"

# Worker processes
# Cloud Run handles scaling, so we use fewer workers per instance
workers = int(os.environ.get("GUNICORN_WORKERS", min(multiprocessing.cpu_count() * 2 + 1, 4)))
worker_class = "uvicorn.workers.UvicornWorker"

# Timeout
timeout = 300  # 5 minutes for long-running AI requests
graceful_timeout = 30
keepalive = 5

# Logging
accesslog = "-"
errorlog = "-"
loglevel = os.environ.get("LOG_LEVEL", "info")

# Process naming
proc_name = "leetloop-api"

# Security
limit_request_line = 4094
limit_request_fields = 100
limit_request_field_size = 8190
