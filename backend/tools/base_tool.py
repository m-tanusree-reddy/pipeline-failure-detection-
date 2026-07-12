from abc import ABC, abstractmethod
from typing import Any, Dict

class BaseTool(ABC):
    """
    Abstract base class for all investigation tools.
    """
    
    @abstractmethod
    def run(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute the tool with the given context/parameters.
        
        Args:
            context (Dict[str, Any]): The input parameters for the tool.
            
        Returns:
            Dict[str, Any]: A dictionary containing the tool's structured output.
        """
        pass
