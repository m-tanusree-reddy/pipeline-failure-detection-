"""
PyPI Tool

Queries the PyPI JSON API to verify whether a package exists, fetch
its latest version, and check if the package name is correct (handles
common underscore/hyphen typos).
"""
import logging
import re
import urllib.request
import urllib.error
import json
from typing import Dict, Any, List

from backend.tools.base_tool import BaseTool


logger = logging.getLogger(__name__)

PYPI_API_BASE = "https://pypi.org/pypi/{package}/json"


class PyPI(BaseTool):
    """
    Validates a missing package against the PyPI registry.
    Checks existence, retrieves latest version, and surfaces
    common name variants (e.g. flask_sqlalchemy vs flask-sqlalchemy).
    """

    name = "PyPI"

    def run(self, context: Dict[str, Any]) -> Dict[str, Any]:
        error_message: str = context.get("error_message", "")
        error_type: str = context.get("error_type", "")

        package_name = self._extract_package_name(error_message, error_type)
        if not package_name:
            return self._base_result(
                "not_found",
                ["Could not extract a package name from the error message."],
            )

        evidence: List[str] = []

        # Try canonical name and hyphenated variant
        variants = list(dict.fromkeys([
            package_name,
            package_name.replace("_", "-"),
            package_name.replace("-", "_"),
        ]))

        found_package = None
        for variant in variants:
            info = self._fetch_pypi(variant)
            if info:
                found_package = info
                evidence.append(
                    f"✓ Package '{variant}' exists on PyPI."
                )
                evidence.append(
                    f"  Latest version : {info.get('version', 'unknown')}"
                )
                evidence.append(
                    f"  Summary        : {info.get('summary', 'N/A')[:100]}"
                )
                evidence.append(
                    f"  PyPI URL       : https://pypi.org/project/{variant}/"
                )
                if variant != package_name:
                    evidence.append(
                        f"  ⚠ Note: The correct PyPI name is '{variant}', "
                        f"not '{package_name}'. Check your dependency file for typos."
                    )
                break

        if not found_package:
            evidence.append(
                f"✗ Package '{package_name}' was NOT found on PyPI."
            )
            evidence.append(
                "  This may indicate a typo in the import statement or "
                "that the package is internal/private."
            )
            return self._base_result("not_found", evidence)

        return self._base_result(
            "success", evidence, raw=found_package
        )

    def _fetch_pypi(self, package: str) -> Dict | None:
        """Fetches package metadata from the PyPI JSON API."""
        url = PYPI_API_BASE.format(package=package)
        try:
            req = urllib.request.Request(
                url,
                headers={"User-Agent": "pipeline-debug-agent/1.0"},
            )
            with urllib.request.urlopen(req, timeout=8) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                info = data.get("info", {})
                return {
                    "name": info.get("name"),
                    "version": info.get("version"),
                    "summary": info.get("summary"),
                    "home_page": info.get("home_page"),
                }
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return None  # Package does not exist
            logger.warning(f"PyPI HTTP error for '{package}': {e}")
            return None
        except Exception as e:
            logger.warning(f"PyPI lookup failed for '{package}': {e}")
            return None

    @staticmethod
    def _extract_package_name(error_message: str, error_type: str) -> str:
        """Extract the missing package name from common error messages."""
        patterns = [
            r"No module named ['\"]([^'\"]+)['\"]",
            r"cannot import name .+ from ['\"]([^'\"]+)['\"]",
            r"ModuleNotFoundError: No module named ['\"]([^'\"]+)['\"]",
        ]
        for pat in patterns:
            match = re.search(pat, error_message, re.IGNORECASE)
            if match:
                return match.group(1).split(".")[0]
        return ""
