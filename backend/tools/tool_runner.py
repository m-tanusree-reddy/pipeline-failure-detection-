"""
ToolRunner — Investigation Orchestrator

Receives a PlannerOutput and a classification context, then executes
each recommended tool in priority order, collecting structured evidence.
"""
import logging
from typing import Dict, Any, List

from models.planner_models import PlannerOutput
from tools.base_tool import BaseTool
from tools.configuration_inspector import ConfigurationInspector
from tools.git_history import GitHistory
from tools.workflow_history import WorkflowHistory
from tools.pypi_tool import PyPI

logger = logging.getLogger(__name__)

# Registry: maps PlannerOutput tool names → tool class instances
TOOL_REGISTRY: Dict[str, BaseTool] = {
    "ConfigurationInspector": ConfigurationInspector(),
    "GitHistory": GitHistory(),
    "WorkflowHistory": WorkflowHistory(),
    "PyPI": PyPI(),
    # Fallback tools (planner may select these; return graceful stubs)
    "StackOverflow": None,
    "DocumentationSearch": None,
    "GitHubIssues": None,
}


class ToolRunner:
    """
    Executes investigation tools based on the PlannerAgent's output.

    Steps:
      1. Sort the planner's investigation_plan by priority (ascending).
      2. Look up each tool in the TOOL_REGISTRY.
      3. Run each tool with the shared classification context.
      4. Collect and return all evidence results.
    """

    def run(
        self,
        plan: PlannerOutput,
        context: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        """
        Execute tools from the plan and return a list of evidence dicts.

        Args:
            plan    : PlannerOutput from the PlannerAgent.
            context : Classification result dict (error details).

        Returns:
            List of evidence dicts, one per executed tool.
        """
        results: List[Dict[str, Any]] = []

        # Sort tools by priority (1 = highest)
        sorted_steps = sorted(plan.investigation_plan, key=lambda s: s.priority)

        logger.info(
            f"ToolRunner executing {len(sorted_steps)} tool(s): "
            + ", ".join(s.tool for s in sorted_steps)
        )

        for step in sorted_steps:
            tool_name = step.tool
            tool = TOOL_REGISTRY.get(tool_name)

            if tool is None:
                # Tool not yet implemented — return a graceful stub
                logger.warning(
                    f"Tool '{tool_name}' is registered but not yet implemented."
                )
                results.append({
                    "tool": tool_name,
                    "status": "not_implemented",
                    "evidence": [
                        f"Tool '{tool_name}' is planned but not yet implemented."
                    ],
                    "raw": None,
                })
                continue

            if tool_name not in TOOL_REGISTRY:
                logger.warning(f"Unknown tool requested by planner: '{tool_name}'")
                results.append({
                    "tool": tool_name,
                    "status": "unknown_tool",
                    "evidence": [f"Tool '{tool_name}' is not in the tool registry."],
                    "raw": None,
                })
                continue

            try:
                logger.info(f"Running tool: {tool_name} (priority={step.priority})")
                result = tool.run(context)
                results.append(result)
                logger.info(
                    f"Tool '{tool_name}' completed with status: {result.get('status')}"
                )
            except Exception as e:
                logger.error(f"Tool '{tool_name}' raised an exception: {e}", exc_info=True)
                results.append({
                    "tool": tool_name,
                    "status": "error",
                    "evidence": [f"Tool '{tool_name}' failed with error: {str(e)}"],
                    "raw": None,
                })

        return results
