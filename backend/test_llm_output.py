"""
Standalone test: verifies the raw Gemini output for root_cause and explanation
to determine if short text is coming from the LLM prompt or the frontend.
"""
import os, sys, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
load_dotenv()

from services.llm_service import LLMService, AnalysisResult

# Simulate a realistic pipeline error and retrieved evidence
FAKE_ERROR = (
    "ERROR: ModuleNotFoundError: No module named 'requests'\n"
    "  at step 'Install Python Dependencies' in GitHub Actions\n"
    "  Workflow: .github/workflows/ci.yml\n"
    "  Runner: ubuntu-latest, Python 3.11\n"
    "  Command: pip install -r requirements.txt\n"
    "  Exit code: 1"
)

FAKE_DOCS = [
    type('Doc', (), {
        'chunk': type('Chunk', (), {
            'source': 'stackoverflow',
            'content': (
                "When you see ModuleNotFoundError: No module named 'requests', it means the 'requests' "
                "package is not installed in the Python environment being used. In GitHub Actions, this typically "
                "happens because the virtual environment is not activated, or the requirements.txt does not include "
                "the package, or pip install was not run before the failing step. Solution: ensure your workflow "
                "includes 'pip install -r requirements.txt' before any step that imports the package."
            )
        })()
    })(),
    type('Doc', (), {
        'chunk': type('Chunk', (), {
            'source': 'github_issues',
            'content': (
                "Issue: Actions workflow fails with ModuleNotFoundError. The problem is that each job in GitHub "
                "Actions starts with a fresh environment. You need to cache your pip dependencies or ensure the "
                "install step runs first. Use actions/setup-python with cache: 'pip' to speed up builds."
            )
        })()
    })(),
]

def main():
    print("=" * 60)
    print("TESTING RAW GEMINI OUTPUT — No frontend involved")
    print("=" * 60)

    svc = LLMService()
    result = svc.analyze_failure(FAKE_ERROR, FAKE_DOCS)

    print(f"\n--- ROOT CAUSE ({len(result.root_cause)} chars) ---")
    print(result.root_cause)

    print(f"\n--- EXPLANATION ({len(result.explanation)} chars) ---")
    print(result.explanation)

    print(f"\n--- SUGGESTED FIXES ({len(result.suggested_fixes)} items) ---")
    for i, fix in enumerate(result.suggested_fixes, 1):
        print(f"  {i}. {fix}")

    print(f"\n--- CONFIDENCE ---")
    print(f"  {result.confidence}%")

    print("\n" + "=" * 60)
    print("VERDICT:")
    if len(result.explanation) < 200:
        print("⚠  EXPLANATION IS SHORT (<200 chars) — This is a PROMPT issue, NOT a frontend issue.")
        print("   The LLM is returning brief responses. The frontend fix will NOT help.")
    else:
        print("✅ EXPLANATION IS FULL — The truncation is likely a FRONTEND CSS issue.")
    print("=" * 60)

if __name__ == "__main__":
    main()
