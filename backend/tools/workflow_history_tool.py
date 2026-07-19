import logging
from typing import Any, Dict
from backend.tools.base_tool import BaseTool

logger = logging.getLogger(__name__)

class WorkflowHistoryTool(BaseTool):
    """
    Tool to fetch the latest workflow executions and failure history.
    """
    
    def run(self, context: Dict[str, Any]) -> Dict[str, Any]:
        workflow_id = context.get("workflow_id", "default-workflow")
        logger.info(f"WorkflowHistoryTool running for workflow: {workflow_id}")
        
        # Simulating workflow history data.
        return {
            "workflow_id": workflow_id,
            "recent_executions": [
                {
                    "run_id": "123456",
                    "status": "failed",
                    "conclusion": "failure",
                    "created_at": "2023-10-16T10:00:00Z"
                },
                {
                    "run_id": "123455",
                    "status": "completed",
                    "conclusion": "success",
                    "created_at": "2023-10-15T10:00:00Z"
                },
                {
                    "run_id": "123454",
                    "status": "completed",
                    "conclusion": "success",
                    "created_at": "2023-10-14T10:00:00Z"
                }
            ],
            "failure_rate": "33%"
        }
