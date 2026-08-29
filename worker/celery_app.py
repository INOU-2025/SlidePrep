"""Celery application and worker configuration."""

import os
from celery import Celery

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

celery_app = Celery(
    "slideprep_worker",
    broker=REDIS_URL,
    backend=REDIS_URL,
    include=['worker.tasks']
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
)

# api/routes.py resolves AsyncResult(job_id) without an explicit app=,
# relying on Celery's "current app" lookup. That lookup is thread-local by
# default — only the thread that constructed this app sees it as current,
# so any request handled on a different thread (a threaded ASGI server, a
# thread-pool-backed route, or an ASGI test client that runs the app in a
# worker thread) would silently fall back to Celery's unconfigured default
# app, whose result backend is disabled. set_default() registers this app
# as the process-wide default so status lookups resolve consistently
# regardless of which thread actually serves the request.
celery_app.set_default()
