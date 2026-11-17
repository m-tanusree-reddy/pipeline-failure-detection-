import os
import sys
import pytest
from starlette.testclient import TestClient

# Add project root to sys.path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if project_root not in sys.path:
    sys.path.append(project_root)

from backend.server import app
from backend.db.session import SessionLocal
from backend.db.models import User, Repository, RepositoryMember, WorkflowRun, FailureAnalysis, InAppNotification
from backend.services.rbac_service import Role
from backend.services.historical_failure_service import (
    HistoricalFailureService, generate_error_signature, normalize_error_trace
)
from backend.services.notification_service import (
    NotificationService, get_routing_roles, EventType, Severity, is_alert_throttled, record_alert_dispatched
)

client = TestClient(app)

def test_normalization_and_signature():
    # Test that volatile memory addresses and timestamps are stripped
    trace1 = "Error at 0x7fa92b0 in line 42 at 2026-11-17 08:57:53: AssertionError: Expected 200, got 500"
    trace2 = "Error at 0x81efc34 in line 99 at 2026-11-17 09:12:00: AssertionError: Expected 200, got 500"
    sig1 = generate_error_signature("AssertionError", "Payment validation failed", trace1)
    sig2 = generate_error_signature("AssertionError", "Payment validation failed", trace2)
    assert sig1 == sig2

def test_role_based_routing_matrix():
    # Main branch failure: Owner, Admin, Developer
    main_roles = get_routing_roles(EventType.MAIN_BRANCH_FAILURE)
    assert Role.OWNER in main_roles
    assert Role.ADMIN in main_roles
    assert Role.DEVELOPER in main_roles

    # Repeated failure: Owner and Admin (escalation)
    repeated_roles = get_routing_roles(EventType.REPEATED_FAILURE)
    assert Role.OWNER in repeated_roles
    assert Role.ADMIN in repeated_roles
    assert Role.DEVELOPER not in repeated_roles

    # Feature branch failure: Developer
    branch_roles = get_routing_roles(EventType.BRANCH_FAILURE)
    assert Role.DEVELOPER in branch_roles
    assert Role.OWNER not in branch_roles

def test_alert_throttling_deduplication():
    repo_id = "test_repo_throttle"
    sig = "sig_12345"
    branch = "main"

    # Initially not throttled
    assert is_alert_throttled(repo_id, sig, branch) is False

    # Dispatched
    record_alert_dispatched(repo_id, sig, branch)

    # Immediately afterwards, should be throttled
    assert is_alert_throttled(repo_id, sig, branch) is True

    # Different branch should not be throttled
    assert is_alert_throttled(repo_id, sig, "feature-x") is False

def test_historical_failure_correlation():
    import uuid
    db = SessionLocal()
    try:
        unique_name = f"checkout-service-{uuid.uuid4().hex[:6]}"
        repo = Repository(
            owner="org-test",
            name=unique_name,
            full_name=f"org-test/{unique_name}"
        )
        db.add(repo)
        db.commit()
        db.refresh(repo)

        hist_svc = HistoricalFailureService(db)

        # 1. First failure occurrence
        res1 = hist_svc.check_and_correlate_failure(
            repo_id=repo.id,
            failure_type="DatabaseConnectionError",
            root_cause="PostgreSQL connection pool exhausted"
        )
        assert res1["is_recurring"] is False
        assert res1["recurrence_count"] == 1

        # Simulate storing run 1
        wf1 = WorkflowRun(repo_id=repo.id, head_branch="main", head_sha="abc111", conclusion="failure")
        db.add(wf1)
        db.commit()
        db.refresh(wf1)

        fa1 = FailureAnalysis(
            run_id=wf1.id,
            failure_type="DatabaseConnectionError",
            root_cause="PostgreSQL connection pool exhausted",
            error_signature=res1["error_signature"]
        )
        db.add(fa1)
        db.commit()

        # 2. Second failure occurrence (recurrence!)
        res2 = hist_svc.check_and_correlate_failure(
            repo_id=repo.id,
            failure_type="DatabaseConnectionError",
            root_cause="PostgreSQL connection pool exhausted"
        )
        assert res2["is_recurring"] is True
        assert res2["recurrence_count"] >= 2
        assert "RECURRING FAILURE DETECTED" in res2["intelligence_note"]
        assert len(res2["past_occurrences"]) >= 1
    finally:
        db.close()

def test_in_app_notification_flow():
    # 1. Get initial notifications
    res = client.get("/api/notifications")
    assert res.status_code == 200
    data = res.json()
    assert "unread_count" in data
    assert "notifications" in data

    # 2. Trigger a simulated failure which creates an in-app notification
    sim_res = client.post("/api/webhooks/github/simulate", json={
        "workflow_name": "E2E Order Tests",
        "branch": "main",
        "commit_sha": "d74e891",
        "commit_message": "feat: order processing worker",
        "error_type": "AssertionError: Expected 200, got 500"
    })
    assert sim_res.status_code == 200

    # 3. Check notifications endpoint again
    res2 = client.get("/api/notifications")
    assert res2.status_code == 200
    data2 = res2.json()
    assert len(data2["notifications"]) >= 1

    # 4. Mark notification as read
    first_notif = data2["notifications"][0]
    patch_res = client.patch(f"/api/notifications/{first_notif['id']}/read")
    assert patch_res.status_code == 200

    # 5. Mark all as read
    all_read_res = client.post("/api/notifications/mark-all-read")
    assert all_read_res.status_code == 200

def test_notification_preferences_api():
    # Get preferences
    res = client.get("/api/notifications/preferences")
    assert res.status_code == 200
    pref = res.json()
    assert "in_app_enabled" in pref

    # Update preferences
    update_res = client.put("/api/notifications/preferences", json={
        "in_app_enabled": True,
        "slack_enabled": False,
        "notify_critical_only": True
    })
    assert update_res.status_code == 200
    updated = update_res.json()["preferences"]
    assert updated["slack_enabled"] is False
    assert updated["notify_critical_only"] is True

def test_repo_notification_channels_api():
    # Connect a repo first
    conn_res = client.post("/api/repos/connect", json={
        "url": "https://github.com/fastapi/fastapi"
    })
    repo_id = conn_res.json()["repository"]["id"]

    # Register a Slack webhook channel
    add_channel_res = client.post(f"/api/repos/{repo_id}/notifications", json={
        "channel": "slack",
        "target_url_or_email": "https://hooks.slack.com/services/T00/B00/XXXX"
    })
    assert add_channel_res.status_code == 200
    config_id = add_channel_res.json()["id"]

    # List channels
    list_res = client.get(f"/api/repos/{repo_id}/notifications")
    assert list_res.status_code == 200
    channels = list_res.json()
    assert any(c["id"] == config_id for c in channels)

    # Delete channel
    del_res = client.delete(f"/api/repos/{repo_id}/notifications/{config_id}")
    assert del_res.status_code == 200

if __name__ == "__main__":
    pytest.main(["-v", __file__])
