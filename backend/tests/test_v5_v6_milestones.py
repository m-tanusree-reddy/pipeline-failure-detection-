import os
import sys
import uuid
import pytest
from starlette.testclient import TestClient

# Add project root to sys.path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if project_root not in sys.path:
    sys.path.append(project_root)

from backend.server import app
from backend.db.session import SessionLocal
from backend.db.models import Repository, WorkflowRun, FailureAnalysis, CodeRemediation
from backend.services.classification_service import (
    classify_granular_failure, compute_composite_severity, FailureCategory
)
from backend.services.remediation_service import synthesize_code_patch, apply_simulated_patch
from backend.services.metrics_service import (
    record_failure_metric, record_remediation_metric, get_prometheus_metrics
)

client = TestClient(app)

# ==============================================================================
# MILESTONE 5: CLASSIFICATION, SEVERITY & REMEDIATION TESTS
# ==============================================================================

def test_granular_failure_classification():
    """Validates deep taxonomy classification across failure archetypes."""
    # 1. Dependency Incompatibility
    dep_res = classify_granular_failure(
        error_type="ModuleNotFoundError",
        error_message="No module named 'requests'",
        log_snippet="import requests"
    )
    assert dep_res["category"] == FailureCategory.DEPENDENCY_INCOMPATIBILITY.value
    assert dep_res["confidence"] >= 0.85

    # 2. Resource Exhaustion / OOM
    oom_res = classify_granular_failure(
        error_type="FatalError",
        error_message="Process terminated with exit code 137: Out of memory",
        log_snippet="FATAL ERROR: Ineffective mark-compacts near heap limit Allocation failed - JavaScript heap out of memory"
    )
    assert oom_res["category"] == FailureCategory.RESOURCE_EXHAUSTION.value

    # 3. Secrets / Token Expiration
    sec_res = classify_granular_failure(
        error_type="HTTPError",
        error_message="401 Unauthorized: Bad credentials",
        log_snippet="GitHub API responded with 401 Unauthorized"
    )
    assert sec_res["category"] == FailureCategory.SECRETS_CREDENTIALS_EXPIRATION.value

    # 4. Flaky Test
    flaky_res = classify_granular_failure(
        error_type="TestTimeout",
        error_message="Intermittent test timed out after 30000ms (retry 2 of 3)"
    )
    assert flaky_res["category"] == FailureCategory.FLAKY_TEST.value

def test_composite_severity_scoring():
    """Validates composite risk calculation, branch amplification, and recurrence escalation."""
    # Production main branch + recurrent failure -> CRITICAL
    crit_sev = compute_composite_severity(
        category=FailureCategory.RESOURCE_EXHAUSTION.value,
        branch="main",
        is_recurring=True,
        recurrence_count=3
    )
    assert crit_sev["severity_score"] >= 0.85
    assert crit_sev["severity_tier"] == "CRITICAL"
    assert crit_sev["is_production_branch"] is True

    # Feature branch + non-recurring flaky test -> LOW/MEDIUM
    low_sev = compute_composite_severity(
        category=FailureCategory.FLAKY_TEST.value,
        branch="feat/user-avatar",
        is_recurring=False,
        recurrence_count=1
    )
    assert low_sev["severity_score"] <= 0.50
    assert low_sev["severity_tier"] in ("LOW", "MEDIUM")
    assert low_sev["is_production_branch"] is False

def test_code_level_patch_synthesis():
    """Validates unified Git diff patch generation."""
    patch = synthesize_code_patch(
        category=FailureCategory.DEPENDENCY_INCOMPATIBILITY.value,
        root_cause="ModuleNotFoundError: No module named requests",
        explanation="requests is missing from requirements.txt"
    )
    assert patch["target_file"] == "requirements.txt"
    assert "diff --git a/requirements.txt b/requirements.txt" in patch["diff_content"]
    assert "+requests>=" in patch["diff_content"]
    assert patch["risk_level"] == "LOW"
    assert "pip install" in patch["validation_command"]

def test_simulated_patch_application():
    """Tests syntax checking and staging verification of synthesized patches."""
    valid_diff = (
        "diff --git a/requirements.txt b/requirements.txt\n"
        "--- a/requirements.txt\n"
        "+++ b/requirements.txt\n"
        "@@ -1,2 +1,3 @@\n"
        " fastapi\n"
        "+requests\n"
    )
    res = apply_simulated_patch(valid_diff, "requirements.txt", "run_test_123")
    assert res["success"] is True
    assert res["status"] == "applied_to_staging"

    invalid_diff = "random prose without diff headers"
    fail_res = apply_simulated_patch(invalid_diff, "requirements.txt", "run_test_123")
    assert fail_res["success"] is False
    assert fail_res["status"] == "patch_syntax_error"

def test_human_in_the_loop_approval_flow():
    """
    Tests end-to-end human-in-the-loop workflow:
    1. Create remediation proposal in DB
    2. Viewer attempt to approve is forbidden (RBAC)
    3. Developer approves patch
    4. Apply approved patch to staging
    """
    db = SessionLocal()
    try:
        repo = Repository(
            owner="remediation-org",
            name="checkout-service",
            full_name=f"remediation-org/checkout-{uuid.uuid4().hex[:6]}",
            is_private=False
        )
        db.add(repo)
        db.commit()
        db.refresh(repo)

        wf_run = WorkflowRun(
            repo_id=repo.id,
            github_run_id=11223344,
            workflow_name="Checkout CI",
            head_branch="main",
            conclusion="failure"
        )
        db.add(wf_run)
        db.commit()
        db.refresh(wf_run)

        # 1. Propose remediation patch
        remediation = CodeRemediation(
            run_id=wf_run.id,
            title="Add requests to requirements.txt",
            target_file="requirements.txt",
            diff_content=(
                "diff --git a/requirements.txt b/requirements.txt\n"
                "--- a/requirements.txt\n"
                "+++ b/requirements.txt\n"
                "@@ -1,2 +1,3 @@\n"
                " fastapi\n"
                "+requests>=2.31.0\n"
            ),
            rationale="Fixes ModuleNotFoundError",
            risk_level="LOW",
            validation_command="pip install -r requirements.txt",
            status="pending_review"
        )
        db.add(remediation)
        db.commit()
        db.refresh(remediation)

        rem_id = remediation.id

        # 2. Attempt to apply unapproved patch -> HTTP 400
        apply_unapproved = client.post(f"/api/remediations/{rem_id}/apply", json={"action": "apply"})
        assert apply_unapproved.status_code == 400
        assert "must be 'approved'" in apply_unapproved.json()["detail"]

        # 3. Viewer attempt to review -> HTTP 403 Forbidden
        viewer_review = client.post(f"/api/remediations/{rem_id}/review", json={
            "action": "approve",
            "reviewer_role": "Viewer",
            "reviewer_username": "viewer-user"
        })
        assert viewer_review.status_code == 403

        # 4. Developer reviews and approves
        dev_review = client.post(f"/api/remediations/{rem_id}/review", json={
            "action": "approve",
            "reviewer_role": "Developer",
            "reviewer_username": "developer-tanu",
            "comment": "Verified diff against dependency checklist."
        })
        assert dev_review.status_code == 200
        assert dev_review.json()["status"] == "approved"

        # 5. Apply approved patch
        apply_approved = client.post(f"/api/remediations/{rem_id}/apply", json={"action": "apply"})
        assert apply_approved.status_code == 200
        assert apply_approved.json()["status"] == "applied"
        assert "PASSED" in apply_approved.json()["verification"]

        # 6. Verify database updated
        db.refresh(remediation)
        assert remediation.status == "applied"
        assert remediation.applied_at is not None
        assert remediation.reviewed_by == "developer-tanu"
    finally:
        db.close()

# ==============================================================================
# MILESTONE 6: OBSERVABILITY & PROMETHEUS METRICS TESTS
# ==============================================================================

def test_prometheus_metrics_endpoint():
    """Validates GET /api/metrics exposes Prometheus metrics."""
    # Seed metrics
    record_failure_metric("org/repo-test", "AssertionError", "HIGH")
    record_remediation_metric("approved")

    response = client.get("/api/metrics")
    assert response.status_code == 200
    assert "text/plain" in response.headers.get("content-type", "")
    
    body = response.text
    assert "pipeline_failures_total" in body
    assert "pipeline_remediations_total" in body
    assert "pipeline_queue_depth" in body
