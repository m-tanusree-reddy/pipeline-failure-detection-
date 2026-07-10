"""
Base interface for all Investigation Tools.

Every tool receives an input dict and returns a structured Evidence dict.
The ToolRunner calls tools based on the PlannerOutput.
"""
from abc import ABC, abstractmethod
from typing import Dict, Any


class BaseTool(ABC):
    """Abstract base class that all investigation tools must implement."""

    name: str = ""  # Must be overridden — matches PlannerOutput tool names

    @abstractmethod
    def run(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute the investigation and return structured evidence.

        Args:
            context: Dict containing error details from the classifier output.
                     Keys: error_message, file, line, category, error_type, etc.

        Returns:
            Dict with:
              - tool       (str)  : name of this tool
              - status     (str)  : "success" | "partial" | "not_found" | "error"
              - evidence   (list) : list of finding strings
              - raw        (Any)  : optional raw data for downstream use
        """
        ...

    def _base_result(self, status: str, evidence: list, raw: Any = None) -> Dict[str, Any]:
        return {
            "tool": self.name,
            "status": status,
            "evidence": evidence,
            "raw": raw,
        }
