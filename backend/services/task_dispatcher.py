import os
import logging
from typing import Optional, Dict, Any
from fastapi import BackgroundTasks

from backend.celery_app import celery_app, is_redis_available

logger = logging.getLogger("backend.dispatcher")

# Queue mode configuration: "auto" (default), "celery", or "direct"
TASK_QUEUE_MODE = os.getenv("TASK_QUEUE_MODE", "auto").lower()

def dispatch_analysis(
    run_id: str,
    log_path: str,
    db_run_id: Optional[str] = None,
    background_tasks: Optional[BackgroundTasks] = None,
    sync_fallback_func = None
) -> Dict[str, Any]:
    """
    Intelligently routes task execution:
    - If Celery/Redis is available and configured -> queues via Celery Worker.
    - If Celery/Redis is unavailable or in local mode -> falls back to FastAPI BackgroundTasks.
    """
    use_celery = False

    if TASK_QUEUE_MODE == "celery":
        use_celery = True
    elif TASK_QUEUE_MODE == "direct":
        use_celery = False
    elif TASK_QUEUE_MODE == "auto":
        use_celery = is_redis_available()

    if use_celery:
        try:
            from backend.tasks.analysis_tasks import analyze_failure_task
            async_result = analyze_failure_task.apply_async(
                args=[run_id, log_path, db_run_id]
            )
            logger.info(f"[Task Dispatcher] Dispatched task to Celery worker (Task ID: {async_result.id})")
            return {
                "mode": "celery",
                "task_id": async_result.id,
                "status": "queued",
                "message": "Task queued in Redis for Celery background worker."
            }
        except Exception as e:
            logger.warning(f"[Task Dispatcher] Failed to queue via Celery ({e}). Falling back to local background execution.")

    # Fallback to local background execution
    if background_tasks and sync_fallback_func:
        background_tasks.add_task(sync_fallback_func, run_id, log_path, db_run_id=db_run_id)
        logger.info("[Task Dispatcher] Dispatched task via local asynchronous background runner.")
        return {
            "mode": "local_async",
            "run_id": run_id,
            "status": "queued",
            "message": "Task queued in local asynchronous worker thread."
        }

    return {
        "mode": "unknown",
        "status": "unsupported",
        "message": "Neither Celery nor local background worker could be scheduled."
    }

def get_queue_telemetry() -> Dict[str, Any]:
    """Returns real-time queue health and connectivity metrics."""
    redis_ok = is_redis_available()
    active_mode = "celery" if (redis_ok and TASK_QUEUE_MODE != "direct") else "local_fallback"
    return {
        "configured_mode": TASK_QUEUE_MODE,
        "active_mode": active_mode,
        "redis_connected": redis_ok,
        "broker_url": celery_app.conf.broker_url if redis_ok else "unreachable",
        "task_acks_late": celery_app.conf.task_acks_late,
        "prefetch_multiplier": celery_app.conf.worker_prefetch_multiplier
    }
