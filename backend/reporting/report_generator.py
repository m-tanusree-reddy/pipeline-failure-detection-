"""
Report Generator module for automated CI/CD pipeline failure investigation.
Generates structured text and JSON reports combining Analysis and Critic results.
"""

import logging
import os
import re
import json
import sys
from typing import List
from pydantic import BaseModel, Field

# Add project root to sys.path at startup to enable consistent imports
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if project_root not in sys.path:
    sys.path.append(project_root)

# Import Pydantic models for validation
from backend.services.llm_service import AnalysisResult
from backend.agents.critic import CriticResult
from backend.retrieval.retriever import RetrievedDocument

logger = logging.getLogger(__name__)


class PipelineFailureReport(BaseModel):
    """
    Pydantic model representing the final consolidated report.
    Matches standard fields and supports JSON serialization.
    """
    pipeline_error: str = Field(..., description="The original pipeline error message.")
    failure_type: str = Field(..., description="Classified type of failure (e.g. ImportError).")
    root_cause: str = Field(..., description="Determined root cause of the failure.")
    explanation: str = Field(..., description="Detailed explanation of the root cause.")
    evidence: List[str] = Field(..., description="List of evidence files or document titles.")
    suggested_fixes: List[str] = Field(..., description="List of actionable suggested fixes.")
    original_confidence: int = Field(..., description="Original confidence score from the LLM (0-100).")
    final_confidence: int = Field(..., description="Adjusted confidence score after Critic evaluation (0-100).")
    critic_status: str = Field(..., description="Critic review status (Approved / Rejected / Requires Review).")
    critic_comments: str = Field(..., description="Critique remarks or gaps identified.")

    def to_json(self) -> str:
        """
        Serializes the report to a formatted JSON string.

        Returns:
            JSON string representation of the report.
        """
        return self.model_dump_json(indent=2)

    def to_text(self) -> str:
        """
        Generates a clean structured text report.

        Returns:
            Formatted text report matching the specified design.
        """
        fixes_str = "\n".join([f"• {fix}" for fix in self.suggested_fixes]) if self.suggested_fixes else "• No fixes suggested."
        evidence_str = "\n".join([f"{i} {item}" for i, item in enumerate(self.evidence, 1)]) if self.evidence else "No evidence available."

        lines = [
            "==================================",
            "CI Pipeline Failure Report",
            "==================================",
            "Failure Type",
            self.failure_type,
            "----------------------------------",
            "Root Cause",
            self.root_cause,
            "----------------------------------",
            "Explanation",
            self.explanation,
            "----------------------------------",
            "Evidence",
            evidence_str,
            "----------------------------------",
            "Suggested Fixes",
            fixes_str,
            "----------------------------------",
            "Confidence",
            f"{self.final_confidence}%",
            "----------------------------------",
            "Critic Status",
            self.critic_status,
            "----------------------------------",
            "=================================="
        ]
        return "\n\n".join(lines)


class ReportGenerator:
    """
    Generator responsible for creating consolidated failure reports.
    """

    @staticmethod
    def _classify_failure_type(pipeline_error: str) -> str:
        """
        Parses the pipeline error to extract a specific exception or error type.

        Args:
            pipeline_error: The raw pipeline error string.

        Returns:
            A string representing the failure class.
        """
        # Clean lines
        lines = [line.strip() for line in pipeline_error.split("\n") if line.strip()]
        
        # Heuristic 1: Scan python traceback format from the bottom
        for line in reversed(lines):
            # Check for pattern like "ModuleNotFoundError: No module named..." or "ValueError: ..."
            match = re.match(r"^([a-zA-Z_][a-zA-Z0-9_]*Error)\b", line)
            if match:
                return match.group(1)

        # Heuristic 2: Search for standard error class names anywhere in the text
        known_errors = [
            "ImportError", "ModuleNotFoundError", "SyntaxError", "TypeError", 
            "ValueError", "AssertionError", "FileNotFoundError", "KeyError", 
            "IndexError", "ConnectionError", "TimeoutError", "NameError", 
            "AttributeError", "PermissionError", "OSError"
        ]
        for line in lines:
            for err in known_errors:
                if err in line:
                    return err

        # Heuristic 3: Check for typical bash command failure signatures
        if "command not found" in pipeline_error.lower():
            return "CommandNotFoundError"
        if "exit status" in pipeline_error.lower() or "exit code" in pipeline_error.lower():
            return "ProcessExitError"

        return "PipelineExecutionError"

    def generate_report(
        self,
        pipeline_error: str,
        analysis: AnalysisResult,
        critic: CriticResult,
        retrieved_documents: List[RetrievedDocument]
    ) -> PipelineFailureReport:
        """
        Consolidates raw inputs into a clean PipelineFailureReport.

        Args:
            pipeline_error: Original failure log trace.
            analysis: Result from the LLMService.
            critic: Validation output from the CriticAgent.
            retrieved_documents: Documents returned by retrieval layer.

        Returns:
            A populated PipelineFailureReport object.
        """
        # Determine status
        if critic.approved:
            status = "Approved"
        else:
            status = "Rejected" if "REJECTED" in critic.critic_comments else "Requires Review"

        # Calculate final adjusted confidence bound within 0-100
        final_confidence = max(0, min(100, analysis.confidence + critic.confidence_adjustment))

        # Format evidence list: prefer document title, fallback to source/chunk name
        evidence_list = []
        for doc in retrieved_documents:
            if hasattr(doc, 'chunk'):
                title = doc.chunk.title.strip()
                source = doc.chunk.source.strip()
                if title and source:
                    evidence_list.append(f"{title} (Source: {source})")
                elif title:
                    evidence_list.append(title)
                else:
                    evidence_list.append(source)
            else:
                evidence_list.append("Unknown Evidence")

        # Fallback if no evidence list was constructed
        if not evidence_list:
            evidence_list = ["No retrieved evidence files matches."]

        # Classify error class
        failure_type = self._classify_failure_type(pipeline_error)

        return PipelineFailureReport(
            pipeline_error=pipeline_error,
            failure_type=failure_type,
            root_cause=analysis.root_cause,
            explanation=analysis.explanation,
            evidence=evidence_list,
            suggested_fixes=analysis.suggested_fixes,
            original_confidence=analysis.confidence,
            final_confidence=final_confidence,
            critic_status=status,
            critic_comments=critic.critic_comments
        )


if __name__ == "__main__":
    # Test suite printing a sample report
    from backend.retrieval.chunker import Chunk

    print("\n--- Running ReportGenerator Test & Print Sample ---")

    # Mocks
    mock_error = (
        "Traceback (most recent call last):\n"
        "  File \"app.py\", line 12, in <module>\n"
        "    import requests\n"
        "ImportError: No module named requests"
    )

    mock_analysis = AnalysisResult(
        root_cause="requests package missing from requirements.txt",
        confidence=95,
        explanation="The log parser reports an ImportError during app.py execution. The dependency config list requirements.txt is missing 'requests'.",
        suggested_fixes=[
            "pip install requests",
            "Update requirements.txt"
        ],
        supporting_documents=[1, 2]
    )

    mock_critic = CriticResult(
        approved=True,
        confidence_adjustment=-1,
        critic_comments="Confidence adjusted down slightly (100% is statistically overconfident). | Evidence keyword alignment verified (common terms: ['requests', 'requirements.txt']).",
        missing_evidence=[]
    )

    mock_chunk_1 = Chunk(
        chunk_id="chunk-1",
        document_id="doc-1",
        source="requirements.txt",
        title="Requirements File",
        content="numpy==1.25.0",
        url="http://github.com/repo/requirements.txt",
        metadata={},
        chunk_index=1,
        total_chunks=1
    )
    doc_1 = RetrievedDocument(chunk=mock_chunk_1, score=0.1, rank=1)

    mock_chunk_2 = Chunk(
        chunk_id="chunk-2",
        document_id="doc-2",
        source="app.py",
        title="Main Module",
        content="import requests",
        url="http://github.com/repo/app.py",
        metadata={},
        chunk_index=1,
        total_chunks=1
    )
    doc_2 = RetrievedDocument(chunk=mock_chunk_2, score=0.2, rank=2)

    generator = ReportGenerator()
    report = generator.generate_report(
        pipeline_error=mock_error,
        analysis=mock_analysis,
        critic=mock_critic,
        retrieved_documents=[doc_1, doc_2]
    )

    print("\n[Generated Text Report]")
    print(report.to_text())

    print("\n[Generated JSON Report]")
    print(report.to_json())

    print("\n[OK] Report Generator test run completed.")
