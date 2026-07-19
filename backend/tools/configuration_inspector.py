"""
ConfigurationInspector Tool

Scans the repository for dependency manifest files (requirements.txt,
pyproject.toml, setup.cfg, Pipfile, package.json) and checks whether
the failing module/package is listed in them.
"""
import os
import re
import logging
from typing import Dict, Any, List

from tools.base_tool import BaseTool

logger = logging.getLogger(__name__)

# Files to search for dependency declarations
DEPENDENCY_FILES = [
    "requirements.txt",
    "requirements-dev.txt",
    "pyproject.toml",
    "setup.cfg",
    "setup.py",
    "Pipfile",
    "Pipfile.lock",
    "package.json",
]


class ConfigurationInspector(BaseTool):
    """
    Searches dependency manifests to verify if a missing package
    is declared in the project's configuration files.
    """

    name = "ConfigurationInspector"

    def __init__(self, repo_root: str = None):
        # Default to two levels up from this file (project root)
        self.repo_root = repo_root or os.path.abspath(
            os.path.join(os.path.dirname(__file__), "..", "..")
        )

    def run(self, context: Dict[str, Any]) -> Dict[str, Any]:
        error_message: str = context.get("error_message", "")
        error_type: str = context.get("error_type", "")

        # Extract the missing package name from the error message
        package_name = self._extract_package_name(error_message, error_type)
        if not package_name:
            return self._base_result(
                "not_found",
                ["Could not extract a package name from the error message."],
            )

        evidence: List[str] = []
        found_in: List[str] = []

        for dep_file in DEPENDENCY_FILES:
            full_path = os.path.join(self.repo_root, dep_file)
            if not os.path.isfile(full_path):
                continue

            try:
                with open(full_path, encoding="utf-8", errors="ignore") as fh:
                    content = fh.read()
            except Exception as e:
                logger.warning(f"Could not read {dep_file}: {e}")
                continue

            # Normalise: flask_sqlalchemy <-> flask-sqlalchemy
            normalised = package_name.lower().replace("_", "-")
            if normalised in content.lower().replace("_", "-"):
                found_in.append(dep_file)
                evidence.append(
                    f"'{package_name}' IS declared in {dep_file}. "
                    "The package may not be installed in the CI environment."
                )
            else:
                evidence.append(
                    f"'{package_name}' is NOT found in {dep_file}."
                )

        if not found_in:
            evidence.insert(
                0,
                f"FINDING: '{package_name}' is missing from ALL dependency "
                "manifest files. It needs to be added.",
            )
            status = "success"
        else:
            evidence.insert(
                0,
                f"FINDING: '{package_name}' is declared in {found_in} "
                "but may not be installed in the runtime environment.",
            )
            status = "success"

        return self._base_result(status, evidence, raw={"package": package_name, "found_in": found_in})

    @staticmethod
    def _extract_package_name(error_message: str, error_type: str) -> str:
        """Extract the missing package name from common error messages."""
        # ModuleNotFoundError / ImportError patterns
        patterns = [
            r"No module named ['\"]([^'\"]+)['\"]",
            r"cannot import name .+ from ['\"]([^'\"]+)['\"]",
            r"ModuleNotFoundError: No module named ['\"]([^'\"]+)['\"]",
        ]
        for pat in patterns:
            match = re.search(pat, error_message, re.IGNORECASE)
            if match:
                return match.group(1).split(".")[0]  # top-level package only
        return ""
