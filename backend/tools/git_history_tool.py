import logging
from typing import Any, Dict
from backend.tools.base_tool import BaseTool

logger = logging.getLogger(__name__)

class GitHistoryTool(BaseTool):
    """
    Tool to fetch git commit history for a specific file or repository path.
    """
    
    def run(self, context: Dict[str, Any]) -> Dict[str, Any]:
        file_path = context.get("file", "unknown")
        logger.info(f"GitHistoryTool running for file: {file_path}")
        
        # Simulating returning recent commits.
        # In a real scenario, this might use GitPython or call the GitHub API.
        return {
            "recent_commits": [
                {
                    "sha": "a1b2c3d4",
                    "author": "Alice Developer",
                    "date": "2023-10-15T14:30:00Z",
                    "message": f"Update {file_path} for performance improvements"
                },
                {
                    "sha": "e5f6g7h8",
                    "author": "Bob Engineer",
                    "date": "2023-10-10T09:15:00Z",
                    "message": f"Initial commit for {file_path}"
                }
            ],
            "file_analyzed": file_path
        }
