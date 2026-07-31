"""
End-to-End Integration Test: Planner → ToolRunner → Evidence

Runs the full investigation pipeline against a real classification result:
  1. PlannerAgent (Gemini API) → produces PlannerOutput
  2. ToolRunner → executes each recommended tool
  3. Prints collected evidence to console
"""
import sys
import os
import pprint

# Run from project root: python backend/test_e2e_pipeline.py
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

from backend.agents.planner import PlannerAgent
from backend.tools.tool_runner import ToolRunner


# Simulated classification result (as produced by the classifier)
CLASSIFICATION = {
    "category": "ImportError",
    "severity": "High",
    "error_type": "ModuleNotFoundError",
    "file": "backend/auth.py",
    "line": 42,
    "error_message": "No module named 'flask_sqlalchemy'",
}

DIVIDER = "=" * 60


def main():
    print(f"\n{DIVIDER}")
    print("  PIPELINE FAILURE DEBUG AGENT — End-to-End Test")
    print(DIVIDER)
    print(f"\nClassification Input:")
    pprint.pprint(CLASSIFICATION, indent=2)

    # ── Step 1: Planner Agent ────────────────────────────────────
    print(f"\n{DIVIDER}")
    print("  STEP 1: Planner Agent (Gemini API)")
    print(DIVIDER)
    planner = PlannerAgent()
    plan = planner.generate_plan(CLASSIFICATION)

    print(f"\nSummary   : {plan.summary}")
    print(f"Confidence: {plan.confidence}")
    print(f"\nInvestigation Plan ({len(plan.investigation_plan)} tool(s)):")
    for step in sorted(plan.investigation_plan, key=lambda s: s.priority):
        print(f"  {step.priority}. [{step.tool}] — {step.reason}")

    # ── Step 2: Tool Runner ──────────────────────────────────────
    print(f"\n{DIVIDER}")
    print("  STEP 2: Tool Runner — Executing Investigation Tools")
    print(DIVIDER)
    runner = ToolRunner()
    evidence_list = runner.run(plan, CLASSIFICATION)

    # ── Step 3: Evidence Report ──────────────────────────────────
    print(f"\n{DIVIDER}")
    print("  STEP 3: Evidence Collected")
    print(DIVIDER)
    for result in evidence_list:
        tool_name = result["tool"]
        status = result["status"]
        evidence = result["evidence"]
        print(f"\n[{tool_name}] — Status: {status.upper()}")
        for line in evidence:
            print(f"  {line}")

    print(f"\n{DIVIDER}")
    print(f"  Pipeline complete. {len(evidence_list)} tool(s) executed.")
    print(DIVIDER)


if __name__ == "__main__":
    main()
