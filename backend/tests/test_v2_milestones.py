import os
import sys
import json
import pytest
from starlette.testclient import TestClient

# Add project root to sys.path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if project_root not in sys.path:
    sys.path.append(project_root)

from backend.server import app
from backend.services.github_service import parse_repo_url, GitHubServiceError
from backend.services.rbac_service import (
    map_github_to_app_role, Role, Action, has_permission, enforce_permission, RBACException
)
from backend.services.webhook_service import verify_github_signature, generate_signature

client = TestClient(app)

def test_parse_repo_url():
    # HTTPS standard
    owner, repo = parse_repo_url("https://github.com/facebook/react")
    assert owner == "facebook"
    assert repo == "react"

    # HTTPS with .git
    owner, repo = parse_repo_url("https://github.com/django/django.git")
    assert owner == "django"
    assert repo == "django"

    # Slug format
    owner, repo = parse_repo_url("microsoft/vscode")
    assert owner == "microsoft"
    assert repo == "vscode"

    # Invalid URL
    with pytest.raises(GitHubServiceError):
        parse_repo_url("https://notgithub.com/something")

def test_rbac_mapping():
    assert map_github_to_app_role("admin", is_creator=True) == Role.OWNER
    assert map_github_to_app_role("admin", is_creator=False) == Role.ADMIN
    assert map_github_to_app_role("maintain") == Role.ADMIN
    assert map_github_to_app_role("write") == Role.DEVELOPER
    assert map_github_to_app_role("push") == Role.DEVELOPER
    assert map_github_to_app_role("read") == Role.VIEWER
    assert map_github_to_app_role("pull") == Role.VIEWER

    with pytest.raises(RBACException):
        map_github_to_app_role("none")

def test_rbac_permissions():
    # Owner permissions
    assert has_permission(Role.OWNER, Action.MANAGE_REPOSITORY)
    assert has_permission(Role.OWNER, Action.TRIGGER_ANALYSIS)

    # Admin permissions
    assert not has_permission(Role.ADMIN, Action.MANAGE_REPOSITORY)
    assert has_permission(Role.ADMIN, Action.MANAGE_SETTINGS)

    # Developer permissions
    assert not has_permission(Role.DEVELOPER, Action.MANAGE_SETTINGS)
    assert has_permission(Role.DEVELOPER, Action.TRIGGER_ANALYSIS)
    assert has_permission(Role.DEVELOPER, Action.VIEW_REPORTS)

    # Viewer permissions
    assert not has_permission(Role.VIEWER, Action.TRIGGER_ANALYSIS)
    assert has_permission(Role.VIEWER, Action.VIEW_REPORTS)

    # Enforcement test
    enforce_permission(Role.DEVELOPER, Action.VIEW_REPORTS)
    with pytest.raises(RBACException):
        enforce_permission(Role.VIEWER, Action.TRIGGER_ANALYSIS)

def test_hmac_signature_verification():
    secret = "super_secure_webhook_key_987"
    payload = json.dumps({"action": "completed", "event": "workflow_run"}).encode("utf-8")
    valid_sig = generate_signature(payload, secret)

    # Valid signature
    assert verify_github_signature(payload, secret, valid_sig) is True

    # Tampered signature
    assert verify_github_signature(payload, secret, "sha256=invalidhex123") is False

    # Tampered payload
    tampered_payload = json.dumps({"action": "tampered"}).encode("utf-8")
    assert verify_github_signature(tampered_payload, secret, valid_sig) is False

def test_api_health():
    res = client.get("/health")
    assert res.status_code == 200
    assert res.json()["status"] == "healthy"
    assert res.json()["version"] in ["2.0.0", "3.0.0"]

def test_api_connect_repository():
    # Connect a valid public repository
    res = client.post("/api/repos/connect", json={
        "url": "https://github.com/django/django",
        "webhook_secret": "django_secret_key"
    })
    assert res.status_code == 200
    data = res.json()
    assert data["repository"]["full_name"].lower() == "django/django"
    assert "permissions" in data
    assert data["permissions"]["app_role"] in [Role.OWNER, Role.ADMIN, Role.DEVELOPER, Role.VIEWER]

def test_api_list_repositories():
    res = client.get("/api/repos")
    assert res.status_code == 200
    repos = res.json()
    assert isinstance(repos, list)
    assert len(repos) >= 1

def test_api_webhook_ping():
    res = client.post(
        "/api/webhooks/github",
        json={"zen": "Non-blocking is better than blocking."},
        headers={"X-GitHub-Event": "ping"}
    )
    assert res.status_code == 200
    assert "Pong" in res.json()["message"]

def test_api_webhook_simulate():
    res = client.post("/api/webhooks/github/simulate", json={
        "repo_full_name": "django/django",
        "workflow_name": "CI Tests",
        "branch": "main",
        "commit_sha": "f12c890",
        "commit_message": "test: regression in payment serializer",
        "error_type": "AssertionError: Expected 200, got 500"
    })
    assert res.status_code == 200
    data = res.json()
    assert data["status"] in ["simulated", "duplicate"]
    if data["status"] == "simulated":
        assert "run_id" in data
        assert "db_run_id" in data

def test_api_list_events():
    res = client.get("/api/events")
    assert res.status_code == 200
    events = res.json()
    assert isinstance(events, list)
    assert len(events) >= 1

def test_api_backward_compatibility_logs():
    res = client.get("/api/logs")
    assert res.status_code == 200
    logs = res.json()
    assert isinstance(logs, list)

if __name__ == "__main__":
    pytest.main(["-v", __file__])

