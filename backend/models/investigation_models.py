from pydantic import BaseModel, Field
from typing import List, Optional, Any, Dict

class InvestigationTask(BaseModel):
    tool: str = Field(..., description="The name of the tool to execute")
    priority: int = Field(..., description="Priority of the task (lower is higher priority)")
    reason: str = Field(..., description="Reason for executing this tool")
    parameters: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Parameters to pass to the tool")

class PlannerOutput(BaseModel):
    summary: str = Field(..., description="Summary of the investigation plan")
    confidence: float = Field(..., description="Confidence score of the plan")
    investigation_plan: List[InvestigationTask] = Field(..., description="Ordered list of tools to execute")

class Evidence(BaseModel):
    tool: str = Field(..., description="Name of the tool that generated this evidence")
    result: Dict[str, Any] = Field(..., description="The structured result or output from the tool")
    success: bool = Field(True, description="Whether the tool execution was successful")
    error: Optional[str] = Field(None, description="Error message if the tool failed")

class EvidenceBundle(BaseModel):
    evidence_list: List[Evidence] = Field(default_factory=list, description="Collection of evidence gathered from tools")

class InvestigatorOutput(BaseModel):
    summary: str = Field(..., description="Summary of the evidence gathering process")
    evidence_bundle: EvidenceBundle = Field(..., description="The collected evidence")
