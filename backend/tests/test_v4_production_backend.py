import os
import sys
import uuid
import pytest
from unittest.mock import MagicMock, patch
from starlette.testclient import TestClient
from fastapi import BackgroundTasks

# Add project root to sys.path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if project_root not in sys.path:
    sys.path.append(project_root)

from backend.server import app
from backend.db.session import SessionLocal, get_db_telemetry
from backend.db.models import Base, Repository, WorkflowRun, FailureAnalysis
from backend.services.task_dispatcher import dispatch_analysis, get_queue_telemetry
import backend.services.task_dispatcher as dispatcher_module
from backend.tasks.analysis_tasks import analyze_failure_task

client = TestClient(app)

def test_api_system_status():
    """Validates the GET /api/system/status telemetry endpoint."""
    response = client.get("/api/system/status")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "online"
    assert data["version"] == "3.0.0"
    
    # Check database telemetry
    db_data = data["database"]
    assert db_data["status"] == "connected"
    assert db_data["dialect"] in ["sqlite", "postgresql"]
    assert "pool_size" in db_data
    
    # Check queue telemetry
    queue_data = data["queue"]
    assert "configured_mode" in queue_data
    assert "active_mode" in queue_data
    assert "redis_connected" in queue_data
    assert queue_data["task_acks_late"] is True
    assert queue_data["prefetch_multiplier"] == 1

def test_task_dispatcher_local_fallback():
    """Tests that task_dispatcher falls back to BackgroundTasks when Celery is direct/unavailable."""
    original_mode = dispatcher_module.TASK_QUEUE_MODE
    try:
        dispatcher_module.TASK_QUEUE_MODE = "direct"
        
        bg_tasks = BackgroundTasks()
        mock_sync_func = MagicMock()
        
        result = dispatch_analysis(
            run_id="test_run_local",
            log_path="dummy/path/log.txt",
            db_run_id="db_run_123",
            background_tasks=bg_tasks,
            sync_fallback_func=mock_sync_func
        )
        
        assert result["mode"] == "local_async"
        assert result["status"] == "queued"
        assert len(bg_tasks.tasks) == 1
    finally:
        dispatcher_module.TASK_QUEUE_MODE = original_mode

def test_task_dispatcher_celery_routing():
    """Tests that task_dispatcher invokes Celery apply_async when mode is celery."""
    original_mode = dispatcher_module.TASK_QUEUE_MODE
    try:
        dispatcher_module.TASK_QUEUE_MODE = "celery"
        
        with patch("backend.tasks.analysis_tasks.analyze_failure_task.apply_async") as mock_apply:
            mock_async_result = MagicMock()
            mock_async_result.id = "celery_task_uuid_999"
            mock_apply.return_value = mock_async_result
            
            result = dispatch_analysis(
                run_id="test_run_celery",
                log_path="dummy/path/log.txt",
                db_run_id="db_run_456"
            )
            
            assert result["mode"] == "celery"
            assert result["status"] == "queued"
            assert result["task_id"] == "celery_task_uuid_999"
            mock_apply.assert_called_once_with(args=["test_run_celery", "dummy/path/log.txt", "db_run_456"])
    finally:
        dispatcher_module.TASK_QUEUE_MODE = original_mode

def test_celery_task_idempotency():
    """
    Validates that analyze_failure_task is idempotent:
    If a WorkflowRun is already completed and has an existing FailureAnalysis,
    it must return 'already_completed' without re-running the diagnostic pipeline.
    """
    db = SessionLocal()
    try:
        # Create test repository
        repo = Repository(
            owner="idempotency-test",
            name="auth-service",
            full_name=f"idempotency-test/auth-{uuid.uuid4().hex[:6]}",
            is_private=False
        )
        db.add(repo)
        db.commit()
        db.refresh(repo)

        # Create already-completed workflow run
        wf_run = WorkflowRun(
            repo_id=repo.id,
            github_run_id=98765432,
            workflow_name="CI Test",
            head_branch="main",
            head_sha="abcdef12",
            status="completed",
            conclusion="failure"
        )
        db.add(wf_run)
        db.commit()
        db.refresh(wf_run)

        # Create existing analysis
        analysis = FailureAnalysis(
            run_id=wf_run.id,
            analysis_run_id="existing_run_123",
            failure_type="DatabaseError",
            root_cause="Connection timeout to Redis",
            explanation="Existing completed diagnosis",
            status="completed"
        )
        db.add(analysis)
        db.commit()

        # Invoke analyze_failure_task directly (as a function)
        task_result = analyze_failure_task(
            run_id="duplicate_celery_trigger",
            log_path="dummy.log",
            db_run_id=wf_run.id
        )

        assert task_result["status"] == "already_completed"
        assert task_result["db_run_id"] == wf_run.id
    finally:
        db.close()

def test_alembic_metadata_tables():
    """Validates that Alembic metadata correctly captures all 7 production tables."""
    table_names = Base.metadata.tables.keys()
    expected_tables = {
        "users",
        "repositories",
        "repository_members",
        "workflow_runs",
        "failure_analyses",
        "notification_configs",
        "in_app_notifications",
        "notification_preferences"
    }
    for table in expected_tables:
        assert table in table_names, f"Expected table {table} not registered in Base.metadata"
