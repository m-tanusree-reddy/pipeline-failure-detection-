"""
Unit tests for the Investigation Tools layer.
Tests ConfigurationInspector, GitHistory, WorkflowHistory, PyPI, and ToolRunner.
"""
import unittest
from unittest.mock import patch, MagicMock
import os
import sys
import tempfile

# Ensure backend/ is in the path when run from project root
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from backend.tools.configuration_inspector import ConfigurationInspector
from backend.tools.git_history import GitHistory
from backend.tools.workflow_history import WorkflowHistory
from backend.tools.pypi_tool import PyPI
from backend.tools.tool_runner import ToolRunner
from backend.models.planner_models import PlannerOutput, InvestigationStep



# ---------------------------------------------------------------------------
# Shared test context
# ---------------------------------------------------------------------------
FLASK_CONTEXT = {
    "category": "ImportError",
    "severity": "High",
    "error_type": "ModuleNotFoundError",
    "file": "backend/auth.py",
    "line": 42,
    "error_message": "No module named 'flask_sqlalchemy'",
}


# ---------------------------------------------------------------------------
# ConfigurationInspector Tests
# ---------------------------------------------------------------------------
class TestConfigurationInspector(unittest.TestCase):

    def setUp(self):
        # Create a temporary directory as a fake repo root
        self.tmp = tempfile.mkdtemp()

    def test_package_found_in_requirements(self):
        """Should report package IS in requirements.txt."""
        req = os.path.join(self.tmp, "requirements.txt")
        with open(req, "w") as f:
            f.write("flask-sqlalchemy==3.0.5\nrequests==2.31\n")

        tool = ConfigurationInspector(repo_root=self.tmp)
        result = tool.run(FLASK_CONTEXT)

        self.assertEqual(result["tool"], "ConfigurationInspector")
        self.assertEqual(result["status"], "success")
        self.assertTrue(any("IS declared" in e for e in result["evidence"]))

    def test_package_missing_from_all_files(self):
        """Should report package NOT found in any manifest."""
        req = os.path.join(self.tmp, "requirements.txt")
        with open(req, "w") as f:
            f.write("requests==2.31\nflask==3.0\n")

        tool = ConfigurationInspector(repo_root=self.tmp)
        result = tool.run(FLASK_CONTEXT)

        self.assertEqual(result["status"], "success")
        self.assertTrue(any("missing from ALL" in e for e in result["evidence"]))

    def test_no_manifest_files(self):
        """Should still return success with 'NOT found' messages when no files exist."""
        tool = ConfigurationInspector(repo_root=self.tmp)
        result = tool.run(FLASK_CONTEXT)
        self.assertIn(result["status"], ("success", "not_found"))

    def test_unparseable_error_message(self):
        """Should return not_found when no package name can be extracted."""
        tool = ConfigurationInspector(repo_root=self.tmp)
        result = tool.run({"error_message": "Something went wrong", "error_type": ""})
        self.assertEqual(result["status"], "not_found")


# ---------------------------------------------------------------------------
# GitHistory Tests
# ---------------------------------------------------------------------------
class TestGitHistory(unittest.TestCase):

    @patch("backend.tools.git_history.subprocess.run")
    def test_commits_found(self, mock_run):
        """Should parse and return commit info from git log output."""
        mock_run.return_value = MagicMock(
            stdout="abc12345|||Alice|||2024-01-10|||Remove flask-sqlalchemy from deps\n"
                   "def67890|||Bob|||2024-01-09|||Update requirements.txt\n",
            returncode=0,
        )
        tool = GitHistory()
        result = tool.run(FLASK_CONTEXT)

        self.assertEqual(result["tool"], "GitHistory")
        self.assertEqual(result["status"], "success")
        self.assertTrue(any("abc12345" in e for e in result["evidence"]))

    @patch("backend.tools.git_history.subprocess.run")
    def test_no_commits(self, mock_run):
        """Should return not_found when git log is empty."""
        mock_run.return_value = MagicMock(stdout="", returncode=0)
        tool = GitHistory()
        result = tool.run(FLASK_CONTEXT)
        self.assertEqual(result["status"], "not_found")

    @patch("backend.tools.git_history.subprocess.run", side_effect=FileNotFoundError("git not found"))
    def test_git_not_available(self, mock_run):
        """Should return not_found gracefully when git is unavailable."""
        tool = GitHistory()
        result = tool.run(FLASK_CONTEXT)
        self.assertEqual(result["status"], "not_found")


# ---------------------------------------------------------------------------
# WorkflowHistory Tests
# ---------------------------------------------------------------------------
class TestWorkflowHistory(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.workflows_dir = os.path.join(self.tmp, ".github", "workflows")
        os.makedirs(self.workflows_dir, exist_ok=True)

    def test_workflow_with_install_step(self):
        """Should detect pip install lines in workflow YAML."""
        yaml_path = os.path.join(self.workflows_dir, "ci.yml")
        with open(yaml_path, "w") as f:
            f.write("steps:\n  - run: pip install -r requirements.txt\n")
        tool = WorkflowHistory(repo_root=self.tmp)
        result = tool.run(FLASK_CONTEXT)

        self.assertEqual(result["tool"], "WorkflowHistory")
        self.assertTrue(any("pip install" in e for e in result["evidence"]))

    def test_no_workflow_files(self):
        """Should report missing workflows gracefully."""
        tool = WorkflowHistory(repo_root=self.tmp)
        result = tool.run(FLASK_CONTEXT)
        self.assertIn(result["status"], ("success", "not_found"))


# ---------------------------------------------------------------------------
# PyPI Tests
# ---------------------------------------------------------------------------
class TestPyPI(unittest.TestCase):

    @patch("backend.tools.pypi_tool.urllib.request.urlopen")
    def test_package_found(self, mock_urlopen):
        """Should return package info when PyPI responds 200."""
        mock_resp = MagicMock()
        mock_resp.read.return_value = b'{"info": {"name": "flask-sqlalchemy", "version": "3.0.5", "summary": "Adds SQLAlchemy support to Flask.", "home_page": "https://github.com/pallets-eco/flask-sqlalchemy"}}'
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_resp

        tool = PyPI()
        result = tool.run(FLASK_CONTEXT)

        self.assertEqual(result["tool"], "PyPI")
        self.assertEqual(result["status"], "success")
        self.assertTrue(any("3.0.5" in e for e in result["evidence"]))

    @patch("backend.tools.pypi_tool.urllib.request.urlopen", side_effect=Exception("Network error"))
    def test_network_error(self, _):
        """Should return not_found gracefully on network error."""
        tool = PyPI()
        result = tool.run(FLASK_CONTEXT)
        self.assertIn(result["status"], ("not_found",))


# ---------------------------------------------------------------------------
# ToolRunner Tests
# ---------------------------------------------------------------------------
class TestToolRunner(unittest.TestCase):

    def _make_plan(self, tools):
        return PlannerOutput(
            summary="Test plan",
            investigation_plan=[
                InvestigationStep(tool=t, priority=i + 1, reason="test")
                for i, t in enumerate(tools)
            ],
            confidence=0.9,
        )

    def test_runs_tools_in_priority_order(self):
        """Results should be ordered by tool priority."""
        plan = self._make_plan(["PyPI", "ConfigurationInspector"])

        with patch("backend.tools.pypi_tool.PyPI.run", return_value={"tool": "PyPI", "status": "success", "evidence": [], "raw": None}), \
             patch("backend.tools.configuration_inspector.ConfigurationInspector.run", return_value={"tool": "ConfigurationInspector", "status": "success", "evidence": [], "raw": None}):

            runner = ToolRunner()
            results = runner.run(plan, FLASK_CONTEXT)

        tool_names = [r["tool"] for r in results]
        # ConfigurationInspector has priority 2, PyPI has priority 1
        self.assertEqual(tool_names[0], "PyPI")
        self.assertEqual(tool_names[1], "ConfigurationInspector")

    def test_unknown_tool_returns_stub(self):
        """Unknown tools should return a not_implemented stub without crashing."""
        plan = self._make_plan(["StackOverflow"])  # registered but no implementation
        runner = ToolRunner()
        results = runner.run(plan, FLASK_CONTEXT)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["status"], "not_implemented")

    def test_tool_exception_is_caught(self):
        """A tool that raises an exception should not crash the runner."""
        plan = self._make_plan(["GitHistory"])
        with patch("backend.tools.git_history.GitHistory.run", side_effect=RuntimeError("crash")):
            runner = ToolRunner()
            results = runner.run(plan, FLASK_CONTEXT)
        self.assertEqual(results[0]["status"], "error")


if __name__ == "__main__":
    unittest.main()
