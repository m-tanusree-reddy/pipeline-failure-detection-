import unittest
from unittest.mock import MagicMock
from backend.agents.investigator import InvestigatorAgent
from backend.models.investigation_models import PlannerOutput, InvestigationTask
from backend.tools.base_tool import BaseTool

class TestInvestigatorAgent(unittest.TestCase):

    def test_investigator_agent_success(self):
        # Arrange
        mock_git_tool = MagicMock(spec=BaseTool)
        mock_git_tool.run.return_value = {"commit": "12345"}
        
        mock_pypi_tool = MagicMock(spec=BaseTool)
        mock_pypi_tool.run.return_value = {"package": "requests", "version": "2.31.0"}
        
        tools = {
            "GitHistory": mock_git_tool,
            "PyPI": mock_pypi_tool
        }
        
        agent = InvestigatorAgent(tools=tools)
        
        plan = PlannerOutput(
            summary="Test Plan",
            confidence=0.9,
            investigation_plan=[
                InvestigationTask(tool="GitHistory", priority=1, reason="Check recent changes", parameters={"file": "test.py"}),
                InvestigationTask(tool="PyPI", priority=2, reason="Check package version", parameters={"package": "requests"})
            ]
        )
        
        # Act
        output = agent.process_plan(plan)
        
        # Assert
        self.assertEqual(len(output.evidence_bundle.evidence_list), 2)
        self.assertEqual(output.evidence_bundle.evidence_list[0].tool, "GitHistory")
        self.assertTrue(output.evidence_bundle.evidence_list[0].success)
        self.assertEqual(output.evidence_bundle.evidence_list[0].result, {"commit": "12345"})
        
        self.assertEqual(output.evidence_bundle.evidence_list[1].tool, "PyPI")
        self.assertTrue(output.evidence_bundle.evidence_list[1].success)
        self.assertEqual(output.evidence_bundle.evidence_list[1].result, {"package": "requests", "version": "2.31.0"})
        
        mock_git_tool.run.assert_called_once_with({"file": "test.py"})
        mock_pypi_tool.run.assert_called_once_with({"package": "requests"})


    def test_investigator_agent_tool_exception(self):
        # Arrange
        mock_failing_tool = MagicMock(spec=BaseTool)
        mock_failing_tool.run.side_effect = Exception("Network timeout")
        
        mock_success_tool = MagicMock(spec=BaseTool)
        mock_success_tool.run.return_value = {"status": "ok"}
        
        tools = {
            "FailingTool": mock_failing_tool,
            "SuccessTool": mock_success_tool
        }
        
        agent = InvestigatorAgent(tools=tools)
        
        plan = PlannerOutput(
            summary="Test Plan with Failure",
            confidence=0.9,
            investigation_plan=[
                InvestigationTask(tool="FailingTool", priority=1, reason="This will fail"),
                InvestigationTask(tool="SuccessTool", priority=2, reason="This will succeed")
            ]
        )
        
        # Act
        output = agent.process_plan(plan)
        
        # Assert
        self.assertEqual(len(output.evidence_bundle.evidence_list), 2)
        
        failed_evidence = output.evidence_bundle.evidence_list[0]
        self.assertEqual(failed_evidence.tool, "FailingTool")
        self.assertFalse(failed_evidence.success)
        self.assertEqual(failed_evidence.error, "Network timeout")
        
        success_evidence = output.evidence_bundle.evidence_list[1]
        self.assertEqual(success_evidence.tool, "SuccessTool")
        self.assertTrue(success_evidence.success)
        
        mock_failing_tool.run.assert_called_once()
        mock_success_tool.run.assert_called_once()


    def test_investigator_agent_missing_tool(self):
        # Arrange
        mock_existing_tool = MagicMock(spec=BaseTool)
        mock_existing_tool.run.return_value = {"ok": True}
        
        tools = {
            "ExistingTool": mock_existing_tool
        }
        
        agent = InvestigatorAgent(tools=tools)
        
        plan = PlannerOutput(
            summary="Test Plan with Missing Tool",
            confidence=0.9,
            investigation_plan=[
                InvestigationTask(tool="MissingTool", priority=1, reason="Tool not injected"),
                InvestigationTask(tool="ExistingTool", priority=2, reason="Tool injected")
            ]
        )
        
        # Act
        output = agent.process_plan(plan)
        
        # Assert
        self.assertEqual(len(output.evidence_bundle.evidence_list), 2)
        
        missing_evidence = output.evidence_bundle.evidence_list[0]
        self.assertEqual(missing_evidence.tool, "MissingTool")
        self.assertFalse(missing_evidence.success)
        self.assertIn("not found", missing_evidence.error)
        
        success_evidence = output.evidence_bundle.evidence_list[1]
        self.assertTrue(success_evidence.success)

if __name__ == "__main__":
    unittest.main()
