from pydantic import BaseModel
from typing import List, Optional

class WorkflowRun(BaseModel):
    id: int
    status: str
    conclusion: Optional[str] = None
    created_at: str
    head_branch: str

class WorkflowRunsResponse(BaseModel):
    total_count: int
    workflow_runs: List[WorkflowRun]
