from pydantic import BaseModel, Field
from typing import List, Literal

SupportedTool = Literal[
    "GitHistory",
    "StackOverflow",
    "GitHubIssues",
    "PyPI",
    "NPMRegistry",
    "DependencyChangelog",
    "DocumentationSearch",
    "ConfigurationInspector",
    "TestHistory",
    "WorkflowHistory"
]

class InvestigationStep(BaseModel):
    tool: SupportedTool
    priority: int = Field(..., description="Priority of the tool execution, from 1 (highest) to N (lowest).")
    reason: str = Field(..., description="Brief explanation of why this tool is useful for the detected error.")

class PlannerOutput(BaseModel):
    summary: str = Field(..., description="Summary of the detected error and the investigation strategy.")
    investigation_plan: List[InvestigationStep] = Field(..., description="List of investigation steps prioritized by importance.")
    confidence: float = Field(..., description="Confidence score between 0.0 and 1.0 (or 0 and 100) representing how certain the agent is in this plan.")
