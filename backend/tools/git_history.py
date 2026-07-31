"""
GitHistory Tool

Runs `git log` to find recent commits that touched dependency-related
files (requirements.txt, pyproject.toml, Dockerfiles, workflow files).
Returns the commit hashes, authors, dates, and messages of the most
relevant recent changes.
"""
import subprocess
import logging
import os
from typing import Dict, Any, List

from backend.tools.base_tool import BaseTool


logger = logging.getLogger(__name__)

# Files whose git history is most relevant for dependency failures
WATCHED_PATHS = [
    "requirements.txt",
    "requirements-dev.txt",
    "pyproject.toml",
    "setup.cfg",
    "setup.py",
    "Pipfile",
    "Dockerfile",
    ".github/workflows/",
]


class GitHistory(BaseTool):
    """
    Queries git log to surface recent commits relevant to dependency
    or environment configuration changes.
    """

    name = "GitHistory"

    def __init__(self, repo_root: str = None, max_commits: int = 10):
        self.repo_root = repo_root or os.path.abspath(
            os.path.join(os.path.dirname(__file__), "..", "..")
        )
        self.max_commits = max_commits

    def run(self, context: Dict[str, Any]) -> Dict[str, Any]:
        evidence: List[str] = []
        all_commits: List[Dict] = []

        for path in WATCHED_PATHS:
            commits = self._git_log(path)
            if commits:
                all_commits.extend(commits)
                evidence.append(
                    f"Recent commits touching '{path}':"
                )
                for c in commits[:3]:  # Top 3 per file
                    evidence.append(
                        f"  • {c['hash']} [{c['date']}] {c['author']}: {c['message']}"
                    )

        if not all_commits:
            return self._base_result(
                "not_found",
                ["No recent git commits found touching dependency or workflow files."],
            )

        return self._base_result(
            "success",
            evidence,
            raw=all_commits[: self.max_commits],
        )

    def _git_log(self, path: str) -> List[Dict]:
        """Runs git log for a given file/directory path and parses output."""
        try:
            result = subprocess.run(
                [
                    "git", "log",
                    f"--max-count={self.max_commits}",
                    "--pretty=format:%H|||%an|||%ad|||%s",
                    "--date=short",
                    "--",
                    path,
                ],
                cwd=self.repo_root,
                capture_output=True,
                text=True,
                timeout=10,
            )
            commits = []
            for line in result.stdout.strip().splitlines():
                if "|||" in line:
                    parts = line.split("|||", 3)
                    if len(parts) == 4:
                        commits.append({
                            "hash": parts[0][:8],
                            "author": parts[1],
                            "date": parts[2],
                            "message": parts[3],
                        })
            return commits
        except Exception as e:
            logger.warning(f"git log failed for path '{path}': {e}")
            return []
