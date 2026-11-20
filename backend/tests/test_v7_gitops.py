"""
Test Suite for Milestone 7: Autonomous GitOps & GitHub PR Remediation Engine
"""

import os
import unittest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool
from sqlalchemy.orm import sessionmaker

from backend.db.models import Base, User, Repository, RepositoryMember, WorkflowRun, FailureAnalysis, CodeRemediation
from backend.services.gitops_service import GitOpsService, GitOpsServiceError
from backend.services.rbac_service import Role
from backend.server import app, get_db

# Shared in-memory SQLite with StaticPool for thread-safe test isolation
TEST_DB_URL = "sqlite:///:memory:"
engine = create_engine(
    TEST_DB_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()

client = TestClient(app)

class TestMilestone7GitOps(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        Base.metadata.create_all(bind=engine)
        app.dependency_overrides[get_db] = override_get_db

    @classmethod
    def tearDownClass(cls):
        app.dependency_overrides.pop(get_db, None)
        Base.metadata.drop_all(bind=engine)

    def setUp(self):
        self.db = TestingSessionLocal()
        # Clean existing test data
        self.db.query(CodeRemediation).delete()
        self.db.query(FailureAnalysis).delete()
        self.db.query(WorkflowRun).delete()
        self.db.query(RepositoryMember).delete()
        self.db.query(Repository).delete()
        self.db.query(User).delete()
        self.db.commit()

        # Seed standard repository and workflow run
        self.user = User(
            id="usr_gitops_1",
            github_id="gh_12345",
            username="tanusree_dev",
            email="tanu@example.com"
        )
        self.repo = Repository(
            id="repo_gitops_1",
            owner="m-tanusree-reddy",
            name="pipeline-failure-detection-",
            full_name="m-tanusree-reddy/pipeline-failure-detection-",
            default_branch="main"
        )
        self.run = WorkflowRun(
            id="run_gitops_test_100",
            repo_id=self.repo.id,
            run_number=42,
            head_branch="feature/payment-gateways",
            head_sha="e7a89b1c2d3e4f5a6b7c8d9e0f1a2b3c4d5e6f7a",
            status="completed",
            conclusion="failure"
        )
        self.analysis = FailureAnalysis(
            id="fa_gitops_test_100",
            run_id=self.run.id,
            failure_category="DEPENDENCY_INCOMPATIBILITY",
            severity_score=0.85,
            root_cause="ModuleNotFoundError: No module named 'requests'",
            is_recurring=True,
            recurrence_count=3
        )
        self.remediation = CodeRemediation(
            id="rem_gitops_test_100",
            run_id=self.run.id,
            title="Add missing 'requests' runtime dependency to requirements.txt",
            target_file="requirements.txt",
            diff_content="diff --git a/requirements.txt b/requirements.txt\n--- a/requirements.txt\n+++ b/requirements.txt\n@@ -10,3 +10,4 @@\n+requests>=2.31.0\n",
            rationale="ModuleNotFoundError: No module named 'requests' encountered during build.",
            risk_level="LOW",
            validation_command="pip install -r requirements.txt && pytest",
            status="approved"
        )

        self.db.add_all([self.user, self.repo, self.run, self.analysis, self.remediation])
        self.db.commit()

    def tearDown(self):
        self.db.close()

    def test_generate_pr_title(self):
        service = GitOpsService()
        title1 = service.generate_pr_title("Add missing 'requests' dependency")
        self.assertEqual(title1, "fix(ci): Add missing 'requests' dependency")

        title2 = service.generate_pr_title("fix: adjust checkout timeout assertion")
        self.assertEqual(title2, "fix: adjust checkout timeout assertion")

    def test_generate_pr_body_markdown(self):
        service = GitOpsService()
        run_info = {
            "id": "run_12345678",
            "run_number": 42,
            "head_branch": "main",
            "head_sha": "abc1234567890",
            "category": "DEPENDENCY_INCOMPATIBILITY",
            "severity": 0.85
        }
        remediation_dict = {
            "title": "Add missing requests dependency",
            "target_file": "requirements.txt",
            "rationale": "Missing package caused import error",
            "risk_level": "LOW",
            "validation_command": "pytest backend/tests",
            "diff_content": "+requests>=2.31.0"
        }
        body = service.generate_pr_body(remediation_dict, run_info, "tanusree_dev", "Developer")
        self.assertIn("Pipeline Failure Detection: Automated Remediation", body)
        self.assertIn("Run #42", body)
        self.assertIn("DEPENDENCY_INCOMPATIBILITY", body)
        self.assertIn("requirements.txt", body)
        self.assertIn("pytest backend/tests", body)
        self.assertIn("@tanusree_dev", body)

    def test_generate_diagnostic_comment(self):
        service = GitOpsService()
        run_info = {
            "id": "run_123",
            "run_number": 10,
            "head_branch": "main"
        }
        analysis_dict = {
            "root_cause": "SyntaxError in server.py line 40",
            "failure_category": "BUILD_SYNTAX_ERROR",
            "severity_score": 0.90,
            "is_recurring": True,
            "recurrence_count": 2
        }
        remediation_dict = {
            "title": "Fix syntax error",
            "target_file": "server.py",
            "diff_content": "+def valid():",
            "risk_level": "LOW"
        }
        comment = service.generate_diagnostic_comment(analysis_dict, run_info, remediation_dict)
        self.assertIn("Pipeline Failure Detected (Run #10)", comment)
        self.assertIn("BUILD_SYNTAX_ERROR", comment)
        self.assertIn("RECURRENT FAILURE (2x detected)", comment)
        self.assertIn("server.py", comment)

    def test_create_remediation_pull_request_simulation_mode(self):
        service = GitOpsService(token=None)
        result = service.create_remediation_pull_request(
            db_session=self.db,
            remediation_id=self.remediation.id,
            reviewer_username="tanusree_dev",
            reviewer_role="Developer"
        )
        self.assertTrue(result["success"])
        self.assertEqual(result["status"], "pr_created")
        self.assertIn("https://github.com/m-tanusree-reddy/pipeline-failure-detection-/pull/", result["pr_url"])
        self.assertTrue(result["pr_number"] > 0)
        self.assertTrue(result["branch_name"].startswith("fix/ci-run_gito"))

        # Check DB was updated
        updated_rem = self.db.query(CodeRemediation).filter_by(id=self.remediation.id).first()
        self.assertEqual(updated_rem.status, "pr_created")
        self.assertEqual(updated_rem.pr_url, result["pr_url"])
        self.assertEqual(updated_rem.pr_number, result["pr_number"])

    @patch("requests.post")
    @patch("requests.get")
    def test_create_remediation_pull_request_live_api_mock(self, mock_get, mock_post):
        # Mock GET base branch ref
        mock_get_ref = MagicMock()
        mock_get_ref.status_code = 200
        mock_get_ref.json.return_value = {"object": {"sha": "base_sha_12345"}}

        # Mock GET file sha
        mock_get_file = MagicMock()
        mock_get_file.status_code = 200
        mock_get_file.json.return_value = {"sha": "file_sha_67890"}

        mock_get.side_effect = [mock_get_ref, mock_get_file]

        # Mock POST create branch ref and POST create PR
        mock_post_branch = MagicMock()
        mock_post_branch.status_code = 201
        mock_post_branch.json.return_value = {"ref": "refs/heads/fix/ci-test"}

        mock_post_pr = MagicMock()
        mock_post_pr.status_code = 201
        mock_post_pr.json.return_value = {
            "number": 77,
            "html_url": "https://github.com/m-tanusree-reddy/pipeline-failure-detection-/pull/77"
        }

        mock_post.side_effect = [mock_post_branch, mock_post_pr]

        service = GitOpsService(token="ghp_real_authorized_token_for_test")
        result = service.create_remediation_pull_request(
            db_session=self.db,
            remediation_id=self.remediation.id,
            reviewer_username="lead_architect",
            reviewer_role="Admin",
            token="ghp_real_authorized_token_for_test"
        )

        self.assertTrue(result["success"])
        self.assertEqual(result["pr_number"], 77)
        self.assertEqual(result["pr_url"], "https://github.com/m-tanusree-reddy/pipeline-failure-detection-/pull/77")

    def test_create_pr_endpoint_rbac_forbidden_for_viewer(self):
        # Viewer role should be denied 403
        response = client.post(
            f"/api/remediations/{self.remediation.id}/create-pr",
            json={"reviewer_role": "Viewer", "reviewer_username": "guest"}
        )
        self.assertEqual(response.status_code, 403)
        self.assertIn("does not have permission to create Pull Requests", response.json()["detail"])

    def test_create_pr_endpoint_success_for_developer(self):
        # Developer role should be accepted
        response = client.post(
            f"/api/remediations/{self.remediation.id}/create-pr",
            json={"reviewer_role": "Developer", "reviewer_username": "tanusree_dev"}
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["success"])
        self.assertEqual(data["status"], "pr_created")
        self.assertIn("pull", data["pr_url"])

    def test_post_github_diagnostic_comment_endpoint(self):
        response = client.post(
            f"/api/runs/{self.run.id}/post-github-comment",
            json={"target": "commit"}
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["success"])
        self.assertIn("commit", data["comment_url"])

if __name__ == "__main__":
    unittest.main()
