import logging
from typing import Dict, Any
from models.planner_models import PlannerOutput, InvestigationStep
from services.llm_service import LLMService

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
