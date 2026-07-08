# CI-Debug-Agent

An autonomous CI/CD pipeline failure investigation agent. It detects failed GitHub Actions workflows, extracts and cleans the logs, classifies errors using AI, plans an investigation, gathers evidence using multiple search tools, validates evidence using a critic agent, and generates structured root-cause reports.

## Final Architecture (MVP)

```
                  User
                    │
                    ▼
          Upload GitHub Actions Log
                    │
                    ▼
        Log Parsing & Cleaning
                    │
                    ▼
          Error Classification
                    │
                    ▼
        Investigation Planner
                    │
      ┌─────────────┼─────────────┐
      ▼             ▼             ▼
 Git History     StackOverflow   GitHub Issues
   Search            Search          Search
      │             │              │
      └─────────────┼──────────────┘
                    ▼
          Evidence Collection
                    │
                    ▼
              Critic Agent
                    │
                    ▼
          Root Cause Report
```

## Features and Roadmap

- **Phase 1-3: Fundamentals & Parsing**: GitHub Actions API integration, noise-reduction log parsing (extracting the core error trace from raw console logs).
- **Phase 4-5: Routing & Intent**: AI-driven classification (Dependency, Test Failure, Configuration, etc.) and Planner dispatching.
- **Phase 6-8: Tooling & Evidence**: Modular investigation tools (Git history diffs, StackOverflow search, GitHub Issues search) and Critic-based validation.
- **Phase 9-11: Orchestration**: LangGraph state management flow and feedback loop.
- **Phase 12-14: Interface & Polish**: React-based dashboard for interactive investigation reports, documentation, and final end-to-end verification.

## Folder Structure

```
CI-Debug-Agent/
├── backend/
│   ├── app.py
│   ├── github_api.py
│   ├── log_parser.py
│   ├── classifier.py
│   ├── planner.py
│   ├── investigator.py
│   ├── critic.py
│   ├── report.py
│   └── tools/
│       ├── git_tool.py
│       ├── issues_tool.py
│       └── stackoverflow_tool.py
├── frontend/
├── docs/
├── tests/
├── requirements.txt
└── README.md
```

## Installation & Setup

1. **Backend**:
   ```bash
   python -m venv venv
   # On Windows:
   venv\Scripts\activate
   # On macOS/Linux:
   source venv/bin/activate

   pip install -r requirements.txt
   ```

2. **Frontend**:
   ```bash
   cd frontend
   npm install
   npm run dev
   ```
