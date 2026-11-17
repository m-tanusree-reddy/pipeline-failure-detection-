import re
import os
import requests
from typing import Optional, Tuple, Dict, Any
from backend.config import GITHUB_TOKEN, GITHUB_API_URL, TIMEOUT

class GitHubServiceError(Exception):
    def __init__(self, message: str, status_code: int = 400):
        super().__init__(message)
        self.status_code = status_code

def parse_repo_url(url: str) -> Tuple[str, str]:
    """
    Parses a GitHub repository URL or slug into (owner, repo).
    Supports:
      - https://github.com/owner/repo
      - https://github.com/owner/repo.git
      - http://github.com/owner/repo
      - git@github.com:owner/repo.git
      - owner/repo
    """
    clean_url = url.strip()
    if clean_url.endswith(".git"):
        clean_url = clean_url[:-4]
    
    # Check for git@github.com:owner/repo
    ssh_match = re.match(r"^git@github\.com:([\w\-\.]+)/([\w\-\.]+)$", clean_url)
    if ssh_match:
        return ssh_match.group(1), ssh_match.group(2)

    # Check for https://github.com/owner/repo
    http_match = re.match(r"^https?://github\.com/([\w\-\.]+)/([\w\-\.]+)$", clean_url)
    if http_match:
        return http_match.group(1), http_match.group(2)

    # Check for owner/repo
    slug_match = re.match(r"^([\w\-\.]+)/([\w\-\.]+)$", clean_url)
    if slug_match:
        return slug_match.group(1), slug_match.group(2)

    raise GitHubServiceError(f"Invalid GitHub repository URL or slug: '{url}'. Expected format: https://github.com/owner/repo or owner/repo")

class GitHubService:
    def __init__(self, default_token: Optional[str] = None):
        self.default_token = default_token or GITHUB_TOKEN
        self.api_url = GITHUB_API_URL.rstrip("/")

    def _get_headers(self, token: Optional[str] = None) -> Dict[str, str]:
        auth_token = token or self.default_token
        headers = {
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "CI-Debug-Agent-2.0"
        }
        if auth_token and not auth_token.startswith("ghp_xxx") and auth_token != "YOUR_GITHUB_TOKEN":
            headers["Authorization"] = f"Bearer {auth_token}"
        return headers

    def get_authenticated_user(self, token: Optional[str] = None) -> Dict[str, Any]:
        """
        Retrieves the authenticated user's profile from GitHub.
        """
        url = f"{self.api_url}/user"
        headers = self._get_headers(token)
        if "Authorization" not in headers:
            # If no token provided, return a mock/default user profile
            return {
                "id": "anonymous_dev",
                "login": "dev_user",
                "email": "dev@example.com",
                "avatar_url": "https://github.githubassets.com/images/modules/logos_page/GitHub-Mark.png"
            }
        
        response = requests.get(url, headers=headers, timeout=TIMEOUT)
        if response.status_code == 401:
            raise GitHubServiceError("Invalid or expired GitHub token.", status_code=401)
        response.raise_for_status()
        return response.json()

    def get_repository(self, owner: str, repo: str, token: Optional[str] = None) -> Dict[str, Any]:
        """
        Fetches repository details and verifies access permissions.
        """
        url = f"{self.api_url}/repos/{owner}/{repo}"
        headers = self._get_headers(token)
        response = requests.get(url, headers=headers, timeout=TIMEOUT)
        
        if response.status_code == 404:
            raise GitHubServiceError(
                f"Repository '{owner}/{repo}' not found or access denied. If private, please provide an authorized GitHub token.",
                status_code=404
            )
        elif response.status_code == 401:
            raise GitHubServiceError("Unauthorized GitHub API request. Check token validity.", status_code=401)
        
        response.raise_for_status()
        return response.json()

    def determine_user_permission(self, owner: str, repo: str, username: str, token: Optional[str] = None, repo_data: Optional[Dict[str, Any]] = None) -> str:
        """
        Determines the user's permission level for a given repository:
        Returns: 'admin', 'maintain', 'write', 'read', or 'none'.
        """
        headers = self._get_headers(token)
        
        # 1. Check collaborator permission API if authorized
        if "Authorization" in headers:
            perm_url = f"{self.api_url}/repos/{owner}/{repo}/collaborators/{username}/permission"
            try:
                res = requests.get(perm_url, headers=headers, timeout=TIMEOUT)
                if res.status_code == 200:
                    data = res.json()
                    permission = data.get("permission", "read").lower()
                    if permission in ["admin", "maintain", "write", "read"]:
                        return permission
            except Exception:
                pass

        # 2. Check embedded repo permissions if available
        if not repo_data:
            try:
                repo_data = self.get_repository(owner, repo, token)
            except Exception:
                repo_data = {}

        perms = repo_data.get("permissions", {})
        if perms.get("admin"):
            return "admin"
        if perms.get("maintain"):
            return "maintain"
        if perms.get("push"):
            return "write"
        if perms.get("pull"):
            return "read"

        # If repo is public and accessible, default to read
        if not repo_data.get("private", True):
            return "read"

        return "none"

    def download_run_logs(self, owner: str, repo: str, run_id: int, save_path: str, token: Optional[str] = None) -> bool:
        """
        Downloads workflow run logs zip file from GitHub Actions.
        """
        url = f"{self.api_url}/repos/{owner}/{repo}/actions/runs/{run_id}/logs"
        headers = self._get_headers(token)
        response = requests.get(url, headers=headers, stream=True, timeout=TIMEOUT)
        
        if response.status_code == 404:
            raise GitHubServiceError(f"Workflow logs for run {run_id} have expired or are unavailable.", status_code=404)
        elif response.status_code == 403:
            raise GitHubServiceError("Permission denied when downloading workflow logs. Token lacks actions:read.", status_code=403)
        
        response.raise_for_status()
        os.makedirs(os.path.dirname(save_path), exist_ok=True)
        with open(save_path, "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
        return True

    def register_repo_webhook(self, owner: str, repo: str, webhook_url: str, secret: str, token: str) -> Dict[str, Any]:
        """
        Creates a webhook on the target GitHub repository for workflow_run events.
        """
        url = f"{self.api_url}/repos/{owner}/{repo}/hooks"
        headers = self._get_headers(token)
        payload = {
            "name": "web",
            "active": True,
            "events": ["workflow_run", "ping"],
            "config": {
                "url": webhook_url,
                "content_type": "json",
                "secret": secret,
                "insecure_ssl": "0"
            }
        }
        res = requests.post(url, json=payload, headers=headers, timeout=TIMEOUT)
        if res.status_code == 422:
            # Hook might already exist
            return {"status": "exists", "message": "Webhook already registered or duplicate."}
        res.raise_for_status()
        return res.json()

