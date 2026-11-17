import os
import logging
from celery import Celery

logger = logging.getLogger("backend.celery")

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

# Initialize Celery app
celery_app = Celery(
    "pipeline_failure_agent",
    broker=REDIS_URL,
    backend=REDIS_URL,
    include=["backend.tasks.analysis_tasks"]
)

# Production Celery Configuration
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    # Worker reliability settings
    task_acks_late=True,                 # Acknowledge task only after execution finishes
    task_reject_on_worker_lost=True,     # Requeue task if worker process dies unexpectedly
    worker_prefetch_multiplier=1,        # Prevents worker hoard when tasks are long-running
    task_track_started=True,             # Track when task transitions from PENDING to STARTED
    task_time_limit=900,                 # 15 minutes hard timeout
    task_soft_time_limit=840,            # 14 minutes soft timeout (allows graceful teardown)
)

def is_redis_available() -> bool:
    """Checks if Redis broker is reachable."""
    try:
        import redis
        client = redis.from_url(REDIS_URL, socket_timeout=1.5)
        return client.ping()
    except Exception:
        return False
