# CI-Debug-Agent: Working Log

## Day 1 Setup & Initialization

### 1. Workspace Configuration & Ignore Rules
- Configured `.gitignore` at the root to properly ignore Python virtual environments (`venv/`, `__pycache__/`), Node modules (`node_modules/`), IDE settings (`.vscode/`, `.idea/`), and system files.

### 2. Dependency Setup
- Created `requirements.txt` containing the `requests` library.
- Initialized Python virtual environment (`python -m venv venv`).
- Installed `requests` dependency using `venv\Scripts\pip install -r requirements.txt`.

### 3. Documentation
- Created a comprehensive `README.md` detailing the multi-phase roadmap, architecture diagram, project structure, and local run instructions.

### 4. Git Initialization & Remote Sync
- Initialized local Git repository using `git init`.
- Configured local Git user name to `M Tanusree Reddy` and email to `m.tanusreereddy@gmail.com`.
- Staged and committed initial project structure: `.gitignore`, `requirements.txt`, `README.md`, and `working.md`.
- Renamed the default branch to `main`.
- Added remote origin `https://github.com/m-tanusree-reddy/pipeline-failure-detection-.git`.
- Pulled remote changes with `git pull origin main --rebase` to merge the remote `LICENSE` file cleanly.
- Pushed local commits to the remote `main` branch successfully.

### 5. React Frontend Scaffold
- Initialized Vite React application inside the `frontend` folder with the `react-ts` template.
- Installed frontend node dependencies using `npm install`.

### 6. Verification
- Verified Python environment successfully imports `requests`.
- Verified Vite React application compiles and builds successfully via `npm run build` without any errors.
- Staged all frontend files, committed, and pushed to the remote `main` branch successfully.

## Pre-Day 2 Architecture Improvements
- Created and checked out a new feature branch `feature/day-2-github-api` to keep `main` clean.
- Reorganized the `backend/` directory into a modular structure:
  - `agents/`: AI reasoning and planning logic.
  - `services/`: External integrations (GitHub API, parser, etc.).
  - `tools/`: Individual search and history tools.
  - `models/`: Data models.
  - `utils/`: Common helper functions.
  - `logs/`: Directory for saving downloaded logs.
- Created `backend/config.py` to manage environment configurations.
- Created `backend/app.py` as the application entry point and successfully verified it runs.
- Committed the restructured folder layout to the `feature/day-2-github-api` branch and pushed to the remote.


## Day 2 Ingestion Layer Integration

### 1. Dependency Integration
- Installed `python-dotenv` and `pydantic`.
- Generated an updated, UTF-8 encoded `requirements.txt` containing all current dependency specifications.

### 2. Environment Configuration
- Created `backend/.env` containing a placeholder `GITHUB_TOKEN`.
- Updated `backend/config.py` using `load_dotenv` to expose variables (`GITHUB_TOKEN`, `GITHUB_API_URL`, `TIMEOUT`) to other modules.

### 3. Pydantic Models for Response Verification
- Created `backend/models/github.py` with `WorkflowRun` and `WorkflowRunsResponse` Pydantic models.

### 4. GitHub API Ingestion Client
- Implemented `GitHubAPI` client in `backend/services/github_api.py` with a persistent `requests.Session`.
- Structured `list_runs` to support filtering by status, allowing `latest_failed_run` to specifically fetch the latest failed workflow run from the API directly.
- Implemented streaming log download saving run logs to `backend/logs/run_<run_id>.zip`.
- Added authentication validation checking for placeholder tokens, falling back to unauthenticated requests to allow public repository listing without immediately needing credentials.

### 5. Orchestration & Integration Test
- Updated `backend/app.py` to orchestrate workflow run querying and failed logs download for `microsoft/vscode`.
- Handled potential API-level log download restriction (403 Forbidden when unauthenticated) gracefully by pointing the user to configure `.env`.

## Day 3 Log Parsing & Error Classification

### 1. Core Log Parser Implementation
- Checked out a new feature branch: `feature/log-parser`.
- Created `backend/log_parser.py` to handle raw GitHub Actions logs.
- Implemented standard log operations: reading UTF-8 files, stripping ANSI escape codes, and removing basic noisy lines (timestamps, blank lines).

### 2. Overcoming Early Parsing Weaknesses (Errors & Iterations)
- **Error:** When tested against a real `django_failure` GitHub Action log, the initial parser threw `UnknownError` because it only searched for explicitly printed Python exceptions (`ModuleNotFoundError`, `SyntaxError`). It completely missed workflow-level failures like `Process completed with exit code 1`.
- **Error:** The user accidentally provided a directory path when prompted, prompting an `IsADirectoryError` check which was handled gracefully.
- **Improvement:** Refactored the `remove_noise` logic to aggressively strip environment variables, runner versions, OS details, PR checklists, and Git checkout metadata, while introducing an `is_critical_line()` check to *guarantee* lines containing `##[error]`, `FAILED`, and `Traceback` were never dropped.
- **Improvement:** Reduced the `error_context` extraction window from a hardcoded 30 lines to dynamically parsing up to 5 lines backwards and 25 lines forwards, stopping perfectly at empty boundaries to isolate the failure.

### 3. Priority-Based Error Detection System
- Fully rewrote the `detect_error_type` function into a priority-based classifier.
- Created `ERROR_PATTERNS`, a rigorously ordered list of precompiled regexes that ranks errors (e.g., matching a `SyntaxError` before it falls back to a generic `TestFailure` or `WorkflowExecutionError`).
- Implemented a `classification_confidence` score (0 to 100) based on whether the match was an exact regex capture group or a generic keyword heuristic.
- Upgraded `extract_error_message()` to concatenate multiple consecutive log failures into a single clean sentence.

### 4. Unit Testing the Parser
- Created `backend/tests/test_log_parser.py` using Python's `unittest` framework.
- Mocked 7 diverse real-world logs (Module Not Found, Syntax Error, Assertion Failure, PR Quality Check Failure, Action Workflow Crash, Dependency npm 404, and Unknown crashes).
- All 7 tests passed successfully (`python -m unittest backend.tests.test_log_parser`).

### 5. Error Classification Module
- Implemented `backend/classifier.py` strictly using the Python standard library.
- Mapped granular `error_types` parsed by `log_parser.py` into broad categories (e.g., standardizing `ModuleNotFoundError` to `ImportError`).
- Added rule-based severity calculation (`Critical`, `High`, `Medium`, `Low`) based on the category (e.g., `MemoryError` = `Critical`).
- Added rule-based `recommend_tools()` to point developers towards investigation paths (`StackOverflow`, `Git History`, `NPM Registry`, `PyPI`).
- Wrote a standalone test block under `if __name__ == "__main__":` which verified the output dictionary payload successfully maps severities and tools.

### 6. Source Control Checkpoint
- Committed the massive `log_parser.py` refactor, test suite, and `classifier.py`.
- Pushed branch `feature/log-parser` to origin successfully.

### Current Project State
The Ingestion, Parsing, Classification, and now the **Planning** layers are fully implemented. The system can retrieve log files, parse them to pinpoint exceptions, classify their severity/category, and use an LLM-powered planning agent to output a clean, validated investigation strategy for debug tooling execution.

## Day 4 AI Planner Agent Implementation

### 1. Dependency Integration
- Installed Google Gemini API SDK `google-genai` inside our virtual environment.
- Updated `requirements.txt` with all package references properly encoded in UTF-8.

### 2. Configuration Setup
- Added `GEMINI_API_KEY` and `GEMINI_MODEL` (defaulting to `gemini-2.5-flash`) configuration values to `backend/config.py`.

### 3. Pydantic Models for Structured Output
- Created `backend/models/planner_models.py` defining Pydantic schemas for LLM validation:
  - `InvestigationStep`: containing `tool` (restricted to supported tools via `Literal`), `priority` (integer), and `reason` (string).
  - `PlannerOutput`: containing `summary` (string), `investigation_plan` (list of `InvestigationStep`), and `confidence` (float).

### 4. Reusable LLM Service
- Created `backend/services/llm_service.py` exposing `LLMService`.
- Configured client connection using `google.genai.Client`.
- Implemented structured output validation using `GenerateContentConfig(response_schema=response_model)` to guarantee response compliance and handle API timeouts/retries gracefully.

### 5. AI Planner Agent
- Implemented `PlannerAgent` inside `backend/agents/planner.py` accepting the `LLMService` via dependency injection.
- Added strict system prompt formatting to prevent code-fix hallucinations.
- Added robust error handling, returning a safe default plan (`GitHistory`, `DocumentationSearch`, `StackOverflow`) when the API is inaccessible or fails.

- Created `backend/tests/test_planner.py` to assert correct structured response processing and fallback execution under API error states using unittest mocks.
- Run the full test suite verifying that all 9 tests (7 parser tests + 2 planner tests) pass cleanly.

### 7. Environment Diagnosis & Fix (ImportError Resolution)
- **Root Cause**: The project's virtual environment (`venv`) was not activated in the terminal, so `python -m unittest discover backend/tests` was using the global system Python interpreter, which was missing `google-genai` and `python-dotenv`.
- **Fix**: Installed `google-genai` and `python-dotenv` into the global Python environment so that both the activated venv and the global interpreter can run the test suite without activation.
- **Verified**: `python -c "from google import genai; print('Import successful')"` returns success.
- **All 9 tests pass** using `python -m unittest discover backend/tests` without requiring venv activation.

### 8. Real Gemini API Verification
- Added `GEMINI_API_KEY` to `backend/.env`.
- Created `backend/test_real_gemini.py` to run the `PlannerAgent` against the real Gemini API.
- Discovered that `gemini-2.5-flash` is deprecated for new users and `gemini-2.0-flash` had quota exhaustion on the free tier.
- Updated default model in `backend/config.py` from `gemini-2.5-flash` → `gemini-flash-latest`, which has valid quota.
- **Successful Real API Output** for a `ModuleNotFoundError: No module named flask_sqlalchemy` classification:
  ```
  Summary:
  A ModuleNotFoundError occurred because 'flask_sqlalchemy' is missing in the execution
  environment. The investigation plan focuses on verifying dependency configurations,
  checking recent git changes to dependency files, and inspecting the CI workflow setup.

  Confidence: 0.95

  Investigation Plan:
    1. ConfigurationInspector (Priority: 1) - Inspect requirements.txt/pyproject.toml and CI configs.
    2. GitHistory (Priority: 2) - Check if flask-sqlalchemy was recently removed from dependencies.
    3. WorkflowHistory (Priority: 3) - Determine if this failure started after a workflow change.
    4. PyPI (Priority: 4) - Verify the package name and versioning on PyPI.
  ```

### 9. LLM Service Resilience — Model Fallback Chain
- **Problem**: `gemini-flash-latest` and `gemini-3.1-flash-lite` return `503 UNAVAILABLE` under high demand when using structured JSON output (`response_schema`), even though plain text requests succeed.
- **Root Cause**: Structured output (JSON schema enforcement) routes to a higher-load endpoint on Gemini's free tier.
- **Fix**: Rewrote `backend/services/llm_service.py` to:
  - Define a `MODEL_FALLBACK_CHAIN` list: `gemini-3.1-flash-lite` → `gemini-flash-latest` → `gemini-3-flash-preview`.
  - On `503 UNAVAILABLE`: retry once with 5s backoff, then **skip to the next model** automatically.
  - On `429 RESOURCE_EXHAUSTED`: skip that model immediately (no retry).
  - On any other error (4xx, parse): propagate immediately.
- **Result**: Planner Agent successfully fell back from `gemini-flash-latest` (503) → `gemini-3-flash-preview` and returned a real structured plan:
  ```
  Summary: The application is failing due to a missing 'flask_sqlalchemy' dependency
  in the runtime environment. Investigation will focus on verifying dependency
  definitions and recent changes to the environment configuration.

  Confidence: 0.95

  Investigation Plan:
    1. ConfigurationInspector (Priority: 1) - Verify flask-sqlalchemy in requirements.txt/pyproject.toml.
    2. WorkflowHistory (Priority: 2) - Check recent CI logs for failed/skipped install steps.
    3. GitHistory (Priority: 3) - Find commits that modified dependency files or build config.
    4. PyPI (Priority: 4) - Confirm correct package name and version compatibility.
  ```
- All 9 unit tests still pass after the refactor.

### 10. Investigation Tools Layer
Built the full `backend/tools/` package with 4 tools and an orchestrator:

| File | Class | Purpose |
|------|-------|---------|
| `base_tool.py` | `BaseTool` | Abstract interface all tools implement (`run(context) → evidence dict`) |
| `configuration_inspector.py` | `ConfigurationInspector` | Scans requirements.txt, pyproject.toml, etc. to check if failing package is declared |
| `git_history.py` | `GitHistory` | Runs `git log` on watched paths (requirements, Dockerfile, workflows) to surface relevant commits |
| `workflow_history.py` | `WorkflowHistory` | Reads local CI logs for error matches; scans .github/workflows YAML for install steps |
| `pypi_tool.py` | `PyPI` | Queries PyPI JSON API to verify package existence, version, and detect underscore/hyphen typos |
| `tool_runner.py` | `ToolRunner` | Reads PlannerOutput, sorts tools by priority, executes each, collects evidence |
| `__init__.py` | — | Package exports for clean imports |

- Added `backend/tests/test_tools.py` with **14 new tests** (all 23 total pass cleanly, zero ResourceWarnings).
- Created `backend/test_e2e_pipeline.py` end-to-end integration script wiring Planner → ToolRunner → Evidence.

### 11. LLM Service — Dynamic Model Discovery (Major Refactor)
- **Problem**: Hardcoded model names in fallback chain broke silently when models were deprecated, quota-exhausted, or unavailable.
- **Solution**: Rewrote `backend/services/llm_service.py` with:
  - `_discover_models()` calls `client.models.list()` at startup to auto-detect all compatible text-generation Gemini models.
  - Filters out non-text models (embedding, imagen, veo, tts, audio, live, robotics, etc.).
  - Ranks discovered models Flash-first, then Pro — fully automatic, no hardcoded names.
  - Smart error handling per model:
    - `503 UNAVAILABLE` → retry up to 2× with 5s→10s backoff, then skip to next model.
    - `429 RESOURCE_EXHAUSTED` → skip immediately.
    - `400/401/403/404` → skip immediately (fatal, no retry).
    - Other → skip immediately.
  - Full emoji logging showing selected model, overload, quota, and success at each step.
- **Verified live**: Automatically traversed `gemini-flash-latest` (503) → `gemini-2.5-flash` (404 skip) → `gemini-2.0-flash` variants (429 skip) → working model → **confidence 0.95 output**.
- All 23 unit tests pass. `test_planner_live.py` works without any manual `.env` changes.

## Day 7 Backend Web Server & Premium React Frontend Integration

### 1. FastAPI Web Server (`backend/server.py`)
- Implemented a backend web server hosting endpoints for:
  - `GET /api/logs`: Returns a list of sample and uploaded log files.
  - `POST /api/upload`: Handles multipart log file uploads.
  - `POST /api/analyze`: Spawns a background thread running `PipelineOrchestrator.run(log_path)` and registers a custom logging handler.
  - `GET /api/runs/{run_id}`: Allows the React client to poll run status, step durations, real-time logging, and the final generated report.
  - `POST /api/fix`: Simulates executing automated fixes.

### 2. Frontend React Integration (`frontend/`)
- Configured Vite proxy in [vite.config.ts](file:///e:/Pipeline%20failure%20detection/frontend/vite.config.ts) to route `/api` to the backend.
- Overwrote [App.tsx](file:///e:/Pipeline%20failure%20detection/frontend/src/App.tsx) and [index.css](file:///e:/Pipeline%20failure%20detection/frontend/src/index.css) to build a premium dark-themed single-page application mapping Stitch design tokens (nocturnal blues, primary accent blues, rounded shape corners, glassmorphism, and Material Icons).
- Implemented the 4 visual sections:
  1. **Home:** Interactive pipeline flow and engineering pillars.
  2. **Dashboard:** Predefined/uploaded log selection, vertical execution stepper, and real-time terminal logger.
  3. **Analysis:** Root cause details, circular confidence meter, evidence documents, and Critic Agent audits.
  4. **Architecture:** SVG trace node canvas, latency metrics, and GPU compute stats.

### 3. Debugging & Error Fixes
- **FastAPI Startup Failure (Form Data Processing):**
  - *Error:* The server crashed on startup with `RuntimeError: Form data requires "python-multipart" to be installed.` due to handling UploadFile parameters.
  - *Fix:* Installed `python-multipart` dependency inside the Python virtual environment.
- **Empty Query Retrieval Crash (`backend/pipeline.py`):**
  - *Error:* When parsing logs with empty error messages (e.g., quality check failures), the retriever threw `ValueError: The search query cannot be empty.` during vector database search in Step 3.
  - *Fix:* Implemented fallback query logic in `pipeline.py` that defaults to using `error_type` and `file_name` when the error message is blank, ensuring the pipeline completes successfully.
- **Python Module Resolution:**
  - *Error:* Running tests directly threw `ModuleNotFoundError: No module named 'backend'`.
  - *Fix:* Explicitly set `PYTHONPATH="."` in PowerShell command line environment variables during execution.

### 4. Verification & Validation
- Verified log parser tests and investigator tests run and pass with `OK`.
- Verified React client compiles and bundles successfully with `npm run build` in **2.24s**.
- Both servers are running and fully operational locally.
