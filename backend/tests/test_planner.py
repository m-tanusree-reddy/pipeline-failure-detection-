import sys
import os
import unittest
from unittest.mock import MagicMock

# Ensure backend directory is in path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.models.planner_models import PlannerOutput, InvestigationStep
from backend.agents.planner import PlannerAgent


class TestPlannerAgent(unittest.TestCase):
    def test_generate_plan_success(self):
        # Create a mock LLMService
        mock_llm_service = MagicMock()
        
        # Expected mock output
        expected_output = PlannerOutput(
            summary="This appears to be an import-related dependency issue.",
            investigation_plan=[
                InvestigationStep(
                    tool="GitHistory",
                    priority=1,
                    reason="Recent commits may have introduced incorrect imports."
                ),
                InvestigationStep(
                    tool="StackOverflow",
                    priority=2,
                    reason="Search for known Flask SQLAlchemy import issues."
                ),
                InvestigationStep(
                    tool="PyPI",
                    priority=3,
                    reason="Verify package installation and version compatibility."
                )
            ],
            confidence=0.95
        )
        
        # Set the mock method to return our expected output
        mock_llm_service.get_structured_completion.return_value = expected_output
        
        # Initialize PlannerAgent with the mock service
        planner = PlannerAgent(llm_service=mock_llm_service)
        
        # Test input
        classification_result = {
            "category": "ImportError",
            "severity": "High",
            "error_type": "ModuleNotFoundError",
            "file": "backend/auth.py",
            "line": 42,
            "error_message": "No module named flask_sqlalchemy"
        }
        
        # Generate plan
        plan = planner.generate_plan(classification_result)
        
        # Assertions
        self.assertEqual(plan.summary, "This appears to be an import-related dependency issue.")
        self.assertEqual(len(plan.investigation_plan), 3)
        self.assertEqual(plan.investigation_plan[0].tool, "GitHistory")
        self.assertEqual(plan.investigation_plan[1].tool, "StackOverflow")
        self.assertEqual(plan.investigation_plan[2].tool, "PyPI")
        self.assertEqual(plan.confidence, 0.95)
        
        # Verify that get_structured_completion was called with correct arguments
        mock_llm_service.get_structured_completion.assert_called_once()
        args, kwargs = mock_llm_service.get_structured_completion.call_args
        self.assertIn("system", kwargs["messages"][0]["role"].lower())
        self.assertIn("devops engineer", kwargs["messages"][0]["content"].lower())
        self.assertEqual(kwargs["response_model"], PlannerOutput)

    def test_generate_plan_fallback(self):
        # Create a mock LLMService that raises an Exception
        mock_llm_service = MagicMock()
        mock_llm_service.get_structured_completion.side_effect = Exception("Gemini API connection error")
        
        # Initialize PlannerAgent with the mock service
        planner = PlannerAgent(llm_service=mock_llm_service)
        
        # Test input
        classification_result = {
            "category": "ImportError",
            "severity": "High",
            "error_type": "ModuleNotFoundError",
            "file": "backend/auth.py",
            "line": 42,
            "error_message": "No module named flask_sqlalchemy"
        }
        
        # Generate plan (should not raise an exception, should return fallback plan)
        plan = planner.generate_plan(classification_result)
        
        # Assertions for fallback
        self.assertIn("Fallback plan generated", plan.summary)
        self.assertEqual(len(plan.investigation_plan), 3)
        self.assertEqual(plan.investigation_plan[0].tool, "GitHistory")
        self.assertEqual(plan.investigation_plan[1].tool, "DocumentationSearch")
        self.assertEqual(plan.investigation_plan[2].tool, "StackOverflow")
        self.assertEqual(plan.confidence, 0.5)

if __name__ == '__main__':
    unittest.main()
