import sys
import os

# Ensure backend directory is in path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from config import GEMINI_API_KEY
from agents.planner import PlannerAgent

def main():
    print("Testing Planner Agent against real Gemini API...")
    print(f"Loaded GEMINI_API_KEY from config: {'Yes (Length=' + str(len(GEMINI_API_KEY)) + ')' if GEMINI_API_KEY else 'No'}")
    
    if not GEMINI_API_KEY:
        print("Error: GEMINI_API_KEY is not set in backend/.env or environment variables.")
        sys.exit(1)
        
    classification = {
        "category": "ImportError",
        "severity": "High",
        "error_type": "ModuleNotFoundError",
        "file": "backend/auth.py",
        "line": 42,
        "error_message": "No module named flask_sqlalchemy"
    }
    
    planner = PlannerAgent()
    try:
        plan = planner.generate_plan(classification)
        print("\n" + "=" * 40)
        print("REAL GEMINI PLANNER OUTPUT")
        print("=" * 40)
        print(f"Summary:\n{plan.summary}\n")
        print(f"Confidence: {plan.confidence}")
        print("\nInvestigation Plan:")
        for idx, step in enumerate(plan.investigation_plan, 1):
            print(f"  {idx}. Tool: {step.tool} (Priority: {step.priority})")
            print(f"     Reason: {step.reason}")
    except Exception as e:
        print(f"Real Gemini test failed: {e}")

if __name__ == "__main__":
    main()
