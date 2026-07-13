import json
from typing import List, Dict, Any
from pydantic import BaseModel, Field

class RetrievalPlan(BaseModel):
    """
    Represents a structured plan for retrieving knowledge context.
    """
    queries: List[str] = Field(description="List of search queries generated based on the error.")
    sources: List[str] = Field(description="Preferred knowledge sources to search.")
    top_k: int = Field(default=5, description="Number of top results to retrieve.")
    reason: str = Field(description="Explanation of why these queries and sources were chosen.")
    status: str = Field(default="planned", description="Status of the retrieval plan.")

def generate_retrieval_plan(classification_result: Dict[str, Any]) -> RetrievalPlan:
    """
    Generates a deterministic retrieval plan based on the classification result.
    
    Args:
        classification_result (Dict[str, Any]): The structured output from the classifier.
            Must contain at least a 'category' key.
            
    Returns:
        RetrievalPlan: The retrieval strategy containing queries, sources, and top_k.
    """
    category = classification_result.get("category", "UnknownError")
    
    # Define mapping from error category to retrieval strategy parameters
    strategy_map = {
        "ImportError": {
            "queries": [
                "ModuleNotFoundError GitHub Actions",
                "No module named requests",
                "Python ImportError requests"
            ],
            "sources": ["github_issues", "stackoverflow", "python_docs", "historical_logs"],
            "reason": "ImportError usually requires searching GitHub Issues, StackOverflow, official Python documentation and previous pipeline failures."
        },
        "DependencyError": {
            "queries": [
                "pip install failed",
                "package not found",
                "dependency resolution GitHub Actions"
            ],
            "sources": ["github_issues", "stackoverflow", "pypi_docs", "historical_logs"],
            "reason": "Dependency errors usually stem from package resolution or missing PyPI distributions."
        },
        "SyntaxError": {
            "queries": [
                "SyntaxError invalid syntax",
                "Python syntax error GitHub Actions",
                "IndentationError expected an indented block"
            ],
            "sources": ["python_docs", "stackoverflow", "historical_logs"],
            "reason": "Syntax errors are fundamental code issues usually addressed via documentation or StackOverflow."
        },
        "AssertionFailure": {
            "queries": [
                "pytest assertion failed",
                "unittest assert failed",
                "test failure GitHub Actions"
            ],
            "sources": ["github_issues", "historical_logs"],
            "reason": "Assertion failures are specific to the test suite and code logic, requiring project historical context."
        },
        "ConfigurationError": {
            "queries": [
                "GitHub Actions yaml invalid",
                "Invalid workflow configuration",
                "workflow syntax error"
            ],
            "sources": ["github_actions_docs", "github_issues", "stackoverflow"],
            "reason": "Configuration errors are typically resolved by checking official GitHub Actions documentation."
        },
        "QualityCheckFailure": {
            "queries": [
                "GitHub Actions quality check failed",
                "PR failed required checks",
                "workflow quality gate"
            ],
            "sources": ["github_issues", "github_actions_docs", "historical_logs"],
            "reason": "Quality check failures relate to linters and project policies, needing historical context and workflow docs."
        },
        "WorkflowExecutionError": {
            "queries": [
                "Process completed with exit code 1",
                "GitHub Actions exit code",
                "workflow failed"
            ],
            "sources": ["github_actions_docs", "github_issues", "stackoverflow", "historical_logs"],
            "reason": "General execution errors require broad searching across actions docs and community issues."
        },
        "PermissionError": {
            "queries": [
                "GitHub Actions Permission denied",
                "403 Forbidden GitHub API",
                "GITHUB_TOKEN permissions"
            ],
            "sources": ["github_actions_docs", "github_issues", "stackoverflow"],
            "reason": "Permission errors are mostly related to GITHUB_TOKEN scopes and require official docs."
        },
        "TimeoutError": {
            "queries": [
                "GitHub Actions job timeout",
                "workflow execution taking too long",
                "timeout exceeded"
            ],
            "sources": ["github_actions_docs", "github_issues", "historical_logs"],
            "reason": "Timeouts relate to runner limits and performance issues, checked against historical trends."
        },
        "MemoryError": {
            "queries": [
                "GitHub Actions out of memory",
                "OOM killed workflow",
                "runner memory limit exceeded"
            ],
            "sources": ["github_actions_docs", "github_issues", "stackoverflow"],
            "reason": "Memory errors require checking GitHub runner specifications and community workarounds."
        },
        "UnknownError": {
            "queries": [
                "GitHub Actions unknown failure",
                "pipeline failed unexpectedly",
                "workflow error"
            ],
            "sources": ["github_issues", "stackoverflow", "github_actions_docs", "historical_logs"],
            "reason": "Unknown errors require a broad search strategy across all available knowledge bases."
        }
    }
    
    # Fetch the strategy for the category, defaulting to UnknownError if not matched
    strategy = strategy_map.get(category, strategy_map["UnknownError"])
    
    return RetrievalPlan(
        queries=strategy["queries"],
        sources=strategy["sources"],
        top_k=5,
        reason=strategy["reason"],
        status="planned"
    )

if __name__ == "__main__":
    # Test all supported categories
    categories = [
        "ImportError",
        "DependencyError",
        "SyntaxError",
        "AssertionFailure",
        "ConfigurationError",
        "QualityCheckFailure",
        "WorkflowExecutionError",
        "PermissionError",
        "TimeoutError",
        "MemoryError",
        "UnknownError",
        "SomeRandomErrorNotSupported" # Should fallback to UnknownError
    ]
    
    for cat in categories:
        print(f"--- Generating Plan for: {cat} ---")
        mock_classification = {
            "category": cat,
            "severity": "High",
            "confidence": 95,
            "reason": "Sample mock reason for testing",
            "status": "classified"
        }
        
        plan = generate_retrieval_plan(mock_classification)
        # Print the Pydantic model as formatted JSON
        print(json.dumps(plan.model_dump(), indent=4))
        print("\n")
