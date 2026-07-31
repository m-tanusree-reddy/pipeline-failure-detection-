import requests
from typing import Optional
from backend.config import GITHUB_TOKEN, GITHUB_API_URL, TIMEOUT
from backend.models.github import WorkflowRun, WorkflowRunsResponse


class GitHubAPI:
    """
    A class to interact with the GitHub REST API for workflow runs and logs.
    """
    def __init__(self, token: str = GITHUB_TOKEN, api_url: str = GITHUB_API_URL):
        self.api_url = api_url.rstrip("/")
        self.session = requests.Session()
        self.session.headers.update({
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        })
        # Only set authorization if token is not empty and not the default placeholder
        if token and not token.startswith("ghp_xxx") and token != "YOUR_GITHUB_TOKEN":
            self.session.headers["Authorization"] = f"Bearer {token}"
            
    def list_runs(self, owner: str, repo: str, status: Optional[str] = None) -> WorkflowRunsResponse:
        """
        List workflow runs for a repository.
        """
        url = f"{self.api_url}/repos/{owner}/{repo}/actions/runs"
        params = {}
        if status:
            params["status"] = status
        response = self.session.get(url, params=params, timeout=TIMEOUT)
        response.raise_for_status()
        
        data = response.json()
        try:
            return WorkflowRunsResponse.model_validate(data)
        except AttributeError:
            return WorkflowRunsResponse.parse_obj(data)

    def latest_failed_run(self, owner: str, repo: str) -> Optional[WorkflowRun]:
        """
        Get the latest failed workflow run.
        """
        response_data = self.list_runs(owner, repo, status="failure")
        
        if not response_data.workflow_runs:
            return None
            
        # Return the first one (which is the latest since API returns them sorted desc)
        return response_data.workflow_runs[0]

    def download_logs(self, owner: str, repo: str, run_id: int, save_path: str) -> bool:
        """
        Download the workflow run logs as a ZIP archive.
        """
        url = f"{self.api_url}/repos/{owner}/{repo}/actions/runs/{run_id}/logs"
        response = self.session.get(url, stream=True, timeout=TIMEOUT)
        response.raise_for_status()
        
        # Write to file in chunks
        with open(save_path, "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
        return True
