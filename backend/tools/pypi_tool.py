import logging
import requests
from typing import Any, Dict
from backend.tools.base_tool import BaseTool

logger = logging.getLogger(__name__)

class PyPITool(BaseTool):
    """
    Tool to fetch package metadata from the PyPI API.
    Handles network failures gracefully.
    """
    
    def run(self, context: Dict[str, Any]) -> Dict[str, Any]:
        package_name = context.get("package", "")
        if not package_name:
            logger.warning("PyPITool: No package name provided in context.")
            return {"error": "No package name provided"}
            
        logger.info(f"PyPITool running for package: {package_name}")
        url = f"https://pypi.org/pypi/{package_name}/json"
        
        try:
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                data = response.json()
                info = data.get("info", {})
                return {
                    "package": package_name,
                    "version": info.get("version"),
                    "summary": info.get("summary"),
                    "requires_python": info.get("requires_python"),
                    "home_page": info.get("home_page"),
                    "project_urls": info.get("project_urls", {})
                }
            elif response.status_code == 404:
                return {"error": f"Package '{package_name}' not found on PyPI", "status_code": 404}
            else:
                return {"error": f"Failed to fetch PyPI data. Status code: {response.status_code}", "status_code": response.status_code}
                
        except requests.RequestException as e:
            logger.error(f"PyPITool: Network error occurred: {e}")
            return {
                "error": f"Network error occurred while fetching from PyPI: {str(e)}",
                "package": package_name
            }
