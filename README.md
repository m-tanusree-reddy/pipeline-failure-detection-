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

## Installation & Local Setup

### 1. Backend Setup
1. Navigate to the project root and create a virtual environment:
   ```bash
   python -m venv venv
   ```
2. Activate the virtual environment:
   * **Windows (PowerShell):** `.\venv\Scripts\Activate.ps1`
   * **macOS/Linux:** `source venv/bin/activate`
3. Install the dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Create a `backend/.env` file from the example:
   ```bash
   cp backend/.env.example backend/.env
   ```
   Add your `GEMINI_API_KEY` and `GITHUB_TOKEN` in the `.env` file.
5. Start the FastAPI server locally:
   ```bash
   python backend/server.py
   ```
   The backend will start at `http://127.0.0.1:8000`.

### 2. Frontend Setup
1. Navigate to the `frontend/` directory:
   ```bash
   cd frontend
   ```
2. Install dependencies:
   ```bash
   npm install
   ```
3. Start the Vite React development server:
   ```bash
   npm run dev
   ```
   The development server will run at `http://localhost:5173`. Any API calls to `/api/*` will automatically be proxied to the backend server.

---

## Production Deployment (Free Tier Setup)

The application is configured to deploy directly to **Render** (for the backend FastAPI service) and **Vercel** (for the React static frontend) for free without using Docker.

### 1. Backend Deployment on Render (FastAPI)
1. Sign up/Log in to [Render](https://render.com/).
2. Click **New +** and select **Blueprint**.
3. Connect your GitHub repository. Render will automatically parse the `render.yaml` configuration in the root directory.
4. During setup, configure the following **Environment Variables** in Render:
   * `GEMINI_API_KEY`: Your Gemini API Key (obtained from Google AI Studio).
   * `GITHUB_TOKEN`: Your GitHub Personal Access Token.
   * `ALLOWED_ORIGINS`: Set this to your deployed Vercel frontend URL (e.g. `https://your-app.vercel.app`) to secure the API.
   * `PYTHONPATH`: `.`
5. Click **Apply**. Render will deploy the backend as a free web service. You will receive a backend URL like `https://ci-debug-agent-backend.onrender.com`.
6. Verify deployment by visiting `https://your-service-name.onrender.com/health` (should return `{"status": "healthy"}`).

### 2. Frontend Deployment on Vercel (Vite + React)
1. Sign up/Log in to [Vercel](https://vercel.com/).
2. Create a **New Project** and connect your GitHub repository.
3. Configure the project:
   * **Root Directory**: `frontend` (Important: must target the `frontend` folder).
   * **Framework Preset**: `Vite`.
   * **Build Command**: `npm run build`.
   * **Output Directory**: `dist`.
4. Add the following **Environment Variable** in Vercel:
   * `VITE_API_URL`: Set this to your deployed Render backend URL (e.g., `https://ci-debug-agent-backend.onrender.com`).
5. Click **Deploy**. Vercel will build and serve your static React application.

---

## Automatic GitHub Deployments
Both Render and Vercel support native, zero-config automatic deployments out of the box when you push to the `main` branch:

* **Render Auto-Deploy**: Enabled by default when connecting your repo. Every push to `main` triggers Render to download your latest code, run `pip install -r requirements.txt`, and restart the FastAPI server.
* **Vercel Auto-Deploy**: Enabled by default. Every push to `main` builds the Vite assets and deploys them to production. Pull requests on other branches automatically build preview deployments.

---

## Environment Variables Reference

| Variable | Scope | Location | Description |
| :--- | :--- | :--- | :--- |
| `GEMINI_API_KEY` | Backend | `.env` / Render Env | Credentials to query the Google Gemini models. |
| `GITHUB_TOKEN` | Backend | `.env` / Render Env | Personal Access Token to download workflow runs and actions logs. |
| `ALLOWED_ORIGINS` | Backend | `.env` / Render Env | Comma-separated list of CORS-approved domains. Set to `*` to allow all. |
| `VITE_API_URL` | Frontend | Vercel Env | The production URL of the Render backend. Defaults to `""` in local development to use Vite's dev proxy. |

