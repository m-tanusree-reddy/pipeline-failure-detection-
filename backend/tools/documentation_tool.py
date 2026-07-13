import logging
import requests
from typing import Any, Dict
from backend.tools.base_tool import BaseTool

logger = logging.getLogger(__name__)

class DocumentationTool(BaseTool):
    """
    Tool to find or verify documentation links for specific packages or frameworks.
    Handles network failures gracefully.
    """
    
    def run(self, context: Dict[str, Any]) -> Dict[str, Any]:
        topic = context.get("topic", "")
        if not topic:
            logger.warning("DocumentationTool: No topic provided in context.")
            return {"error": "No topic provided"}
            
        logger.info(f"DocumentationTool running for topic: {topic}")
        
        # Since we don't have a direct search API for general docs, we'll try PyPI first
        # to see if it's a python package with a docs URL, otherwise return a constructed search link.
        # This is a basic implementation of a documentation lookup tool.
        try:
            url = f"https://pypi.org/pypi/{topic}/json"
            response = requests.get(url, timeout=5)
            
            docs_url = None
            if response.status_code == 200:
                info = response.json().get("info", {})
                project_urls = info.get("project_urls", {})
                if project_urls:
                    docs_url = project_urls.get("Documentation") or project_urls.get("Homepage")
            
            if not docs_url:
                # Fallback generic documentation search link
                docs_url = f"https://devdocs.io/#q={topic}"
                
            return {
                "topic": topic,
                "documentation_url": docs_url,
                "source": "PyPI" if response.status_code == 200 else "Constructed"
            }
            
        except requests.RequestException as e:
            logger.error(f"DocumentationTool: Network error occurred: {e}")
            return {
                "error": f"Network error occurred while fetching documentation links: {str(e)}",
                "topic": topic
            }
