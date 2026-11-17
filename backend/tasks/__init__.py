"""Asynchronous task processing package for Celery."""
from backend.tasks.analysis_tasks import analyze_failure_task

__all__ = ["analyze_failure_task"]
