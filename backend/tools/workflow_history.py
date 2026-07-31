"""
WorkflowHistory Tool

Reads local CI workflow log files from backend/logs/ to find recent
pipeline run records that indicate failure patterns. Also scans the
.github/workflows/ YAML files to surface install/setup steps that
may be misconfigured.
"""
import os
import re
import logging
from typing import Dict, Any, List

from backend.tools.base_tool import BaseTool


logger = logging.getLogger(__name__)


class WorkflowHistory(BaseTool):
    """
    Analyses local CI log files and GitHub Actions workflow YAML files
    to find environment setup steps and recent failure patterns.
    """

    name = "WorkflowHistory"

    def __init__(self, repo_root: str = None):
        self.repo_root = repo_root or os.path.abspath(
            os.path.join(os.path.dirname(__file__), "..", "..")
        )
        self.logs_dir = os.path.join(self.repo_root, "backend", "logs")
        self.workflows_dir = os.path.join(self.repo_root, ".github", "workflows")

    def run(self, context: Dict[str, Any]) -> Dict[str, Any]:
        evidence: List[str] = []
        error_message: str = context.get("error_message", "")

        # 1. Scan local log files for relevant error lines
        log_evidence = self._scan_local_logs(error_message)
        evidence.extend(log_evidence)

        # 2. Scan workflow YAML for install/setup steps
        workflow_evidence = self._scan_workflow_files()
        evidence.extend(workflow_evidence)

        if not evidence:
            return self._base_result(
                "not_found",
                ["No workflow history or log files found to analyse."],
            )

        return self._base_result("success", evidence)

    def _scan_local_logs(self, error_message: str) -> List[str]:
        """Scan backend/logs/*.log for lines matching the current error."""
        results: List[str] = []

        if not os.path.isdir(self.logs_dir):
            results.append(f"No local logs directory found at: {self.logs_dir}")
            return results

        log_files = [
            f for f in os.listdir(self.logs_dir) if f.endswith(".log")
        ]

        if not log_files:
            results.append("No .log files found in backend/logs/.")
            return results

        # Extract a short keyword from the error to search for
        keyword = self._extract_keyword(error_message)
        results.append(f"Scanning {len(log_files)} log file(s) for '{keyword}'...")

        for log_file in sorted(log_files)[-5:]:  # Last 5 log files
            full_path = os.path.join(self.logs_dir, log_file)
            try:
                with open(full_path, encoding="utf-8", errors="ignore") as fh:
                    lines = fh.readlines()
                matches = [
                    l.strip() for l in lines
                    if keyword.lower() in l.lower()
                ]
                if matches:
                    results.append(f"  {log_file}: {len(matches)} matching line(s):")
                    for m in matches[:3]:
                        results.append(f"    → {m[:120]}")
                else:
                    results.append(f"  {log_file}: no matches for '{keyword}'")
            except Exception as e:
                logger.warning(f"Could not read log {log_file}: {e}")

        return results

    def _scan_workflow_files(self) -> List[str]:
        """Scan .github/workflows/*.yml for pip install and setup steps."""
        results: List[str] = []

        if not os.path.isdir(self.workflows_dir):
            results.append(
                "No .github/workflows/ directory found. "
                "CI install steps cannot be verified."
            )
            return results

        yaml_files = [
            f for f in os.listdir(self.workflows_dir)
            if f.endswith((".yml", ".yaml"))
        ]

        if not yaml_files:
            results.append("No workflow YAML files found in .github/workflows/.")
            return results

        install_pattern = re.compile(
            r"(pip install|pip3 install|poetry install|pipenv install"
            r"|npm install|yarn install|conda install)",
            re.IGNORECASE,
        )

        for yaml_file in yaml_files:
            full_path = os.path.join(self.workflows_dir, yaml_file)
            try:
                with open(full_path, encoding="utf-8", errors="ignore") as fh:
                    lines = fh.readlines()
                install_steps = [
                    (i + 1, l.strip())
                    for i, l in enumerate(lines)
                    if install_pattern.search(l)
                ]
                if install_steps:
                    results.append(f"Workflow '{yaml_file}' install steps:")
                    for lineno, step in install_steps[:5]:
                        results.append(f"  Line {lineno}: {step}")
                else:
                    results.append(
                        f"Workflow '{yaml_file}': no install steps detected."
                    )
            except Exception as e:
                logger.warning(f"Could not read workflow {yaml_file}: {e}")

        return results

    @staticmethod
    def _extract_keyword(error_message: str) -> str:
        """Extract the most searchable keyword from the error message."""
        # Try to get the module/package name
        match = re.search(
            r"No module named ['\"]?([a-zA-Z0-9_\-]+)", error_message
        )
        if match:
            return match.group(1)
        # Fallback: first word of the error
        words = error_message.split()
        return words[0] if words else "error"
