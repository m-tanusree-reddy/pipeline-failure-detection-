from backend.agents.planner import PlannerAgent


classification = {
    "category": "ImportError",
    "severity": "High",
    "error_type": "ModuleNotFoundError",
    "file": "backend/auth.py",
    "line": 42,
    "error_message": "No module named flask_sqlalchemy"
}

planner = PlannerAgent()

plan = planner.generate_plan(classification)

print(plan)