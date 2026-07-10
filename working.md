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
The **Ingestion Layer** (GitHub API logs) and the **Parsing/Classification Layer** (Log Parser + Rule-Based Classifier) are now fully implemented and functioning. The system can successfully download a raw `.txt` workflow log, heavily filter out the OS/Git noise, pinpoint the exact traceback, assign a standardized category/severity, and format a clean JSON payload that is primed for the next AI agent reasoning step.
