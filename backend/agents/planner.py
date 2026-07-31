import logging
from typing import Dict, Any, List
from pydantic import BaseModel, Field
from backend.models.planner_models import PlannerOutput, InvestigationStep
from backend.services.llm_service import LLMService




logger = logging.getLogger(__name__)

class PlannerAgent:
    """
    PlannerAgent is an LLM-powered planning agent that determines 
    investigation steps for CI pipeline failures without suggesting fixes.
    """
    def __init__(self, llm_service: LLMService = None):
        self.llm_service = llm_service or LLMService()

    def generate_plan(self, classification_result: Dict[str, Any]) -> PlannerOutput:
        """
        Generates a structured investigation plan based on error classification.
        
        Args:
            classification_result (Dict[str, Any]): Dictionary containing error details.
            
        Returns:
            PlannerOutput: Structured Pydantic model with tools and summary.
        """
        system_prompt = (
            "You are a senior DevOps engineer specializing in CI/CD failures.\n"
            "Your responsibility is NOT to solve the issue.\n"
            "Your responsibility is ONLY to determine the best investigation strategy.\n"
            "Select the investigation tools that should be executed.\n"
            "Explain briefly why each tool is useful.\n"
            "Prioritize the tools from highest to lowest importance.\n"
            "Never hallucinate fixes.\n"
            "Never recommend tools unrelated to the detected error.\n"
            "Return JSON only."
        )
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Classification Result:\n{classification_result}"}
        ]
        
        try:
            plan = self.llm_service.get_structured_completion(
                messages=messages,
                response_model=PlannerOutput
            )
            return plan
        except Exception as e:
            logger.error(f"Failed to generate plan via LLMService: {e}", exc_info=True)
            
            # Safe fallback investigation plan
            return PlannerOutput(
                summary="Fallback plan generated due to LLM failure or missing API key.",
                investigation_plan=[
                    InvestigationStep(
                        tool="GitHistory",
                        priority=1,
                        reason="Check git history to find the recent commit that introduced the change/error."
                    ),
                    InvestigationStep(
                        tool="DocumentationSearch",
                        priority=2,
                        reason="Search official repository or external API documentation for configuration/module mismatch."
                    ),
                    InvestigationStep(
                        tool="StackOverflow",
                        priority=3,
                        reason="Lookup standard error message online on StackOverflow for common fixes."
                    )
                ],
                confidence=0.5
            )


class RetrievalPlan(BaseModel):
    queries: List[str] = Field(description="List of search queries generated based on the error.")
    sources: List[str] = Field(description="Preferred knowledge sources to search.")
    top_k: int = Field(default=5, description="Number of top results to retrieve.")
    reason: str = Field(description="Explanation of why these queries and sources were chosen.")
    status: str = Field(default="planned", description="Status of the retrieval plan.")


def generate_retrieval_plan(classification_result: Dict[str, Any]) -> RetrievalPlan:
    category = classification_result.get("category", "UnknownError")

    strategy_map = {
        "ImportError": {
            "queries": ["ModuleNotFoundError GitHub Actions", "No module named requests", "Python ImportError requests"],
            "sources": ["github_issues", "stackoverflow", "python_docs", "historical_logs"],
            "reason": "ImportError usually requires searching issues, StackOverflow, docs, and historical failures.",
        },
        "DependencyError": {
            "queries": ["pip install failed", "package not found", "dependency resolution GitHub Actions"],
            "sources": ["github_issues", "stackoverflow", "pypi_docs", "historical_logs"],
            "reason": "Dependency errors usually stem from package resolution or missing distributions.",
        },
        "SyntaxError": {
            "queries": ["SyntaxError invalid syntax", "Python syntax error GitHub Actions", "IndentationError expected an indented block"],
            "sources": ["python_docs", "stackoverflow", "historical_logs"],
            "reason": "Syntax errors are usually addressed via docs or community examples.",
        },
        "AssertionFailure": {
            "queries": ["pytest assertion failed", "unittest assert failed", "test failure GitHub Actions"],
            "sources": ["github_issues", "historical_logs"],
            "reason": "Assertion failures are test-suite specific and need project historical context.",
        },
        "ConfigurationError": {
            "queries": ["GitHub Actions yaml invalid", "Invalid workflow configuration", "workflow syntax error"],
            "sources": ["github_actions_docs", "github_issues", "stackoverflow"],
            "reason": "Configuration errors are typically resolved by checking workflow documentation.",
        },
        "QualityCheckFailure": {
            "queries": ["GitHub Actions quality check failed", "PR failed required checks", "workflow quality gate"],
            "sources": ["github_issues", "github_actions_docs", "historical_logs"],
            "reason": "Quality check failures relate to linters and project policies.",
        },
        "WorkflowExecutionError": {
            "queries": ["Process completed with exit code 1", "GitHub Actions exit code", "workflow failed"],
            "sources": ["github_actions_docs", "github_issues", "stackoverflow", "historical_logs"],
            "reason": "General execution errors require broad searching across docs and issues.",
        },
        "PermissionError": {
            "queries": ["GitHub Actions Permission denied", "403 Forbidden GitHub API", "GITHUB_TOKEN permissions"],
            "sources": ["github_actions_docs", "github_issues", "stackoverflow"],
            "reason": "Permission errors are mostly related to token scopes and permissions.",
        },
        "TimeoutError": {
            "queries": ["GitHub Actions job timeout", "workflow execution taking too long", "timeout exceeded"],
            "sources": ["github_actions_docs", "github_issues", "historical_logs"],
            "reason": "Timeouts relate to runner limits and workload duration.",
        },
        "MemoryError": {
            "queries": ["GitHub Actions out of memory", "OOM killed workflow", "runner memory limit exceeded"],
            "sources": ["github_actions_docs", "github_issues", "stackoverflow"],
            "reason": "Memory errors require checking runner limits and known workarounds.",
        },
        "UnknownError": {
            "queries": ["GitHub Actions unknown failure", "pipeline failed unexpectedly", "workflow error"],
            "sources": ["github_issues", "stackoverflow", "github_actions_docs", "historical_logs"],
            "reason": "Unknown errors require a broad search strategy.",
        },
    }

    strategy = strategy_map.get(category, strategy_map["UnknownError"])
    return RetrievalPlan(
        queries=strategy["queries"],
        sources=strategy["sources"],
        top_k=5,
        reason=strategy["reason"],
        status="planned",
    )
