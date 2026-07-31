import os
import sys
from backend.config import LOGS_DIR
from backend.services.github_api import GitHubAPI

def main():
    owner = "microsoft"
    repo = "vscode"
    
    print(f"Repository")
    print(f"{owner}/{repo}")
    print("-" * 28)
    
    # Initialize GitHub API service
    api = GitHubAPI()
    
    # 1. Connect and list runs
    try:
        response = api.list_runs(owner, repo)
    except Exception as e:
        print(f"Error connecting or retrieving runs: {e}")
        sys.exit(1)
        
    print(f"Found {response.total_count} workflow runs")
    
    # 2. Get latest failed run
    failed_run = api.latest_failed_run(owner, repo)
    if not failed_run:
        print("No failed workflow runs found.")
        return
        
    print("Latest failed run")
    print(f"ID: {failed_run.id}")
    print(f"Branch: {failed_run.head_branch}")
    print(f"Created:")
    print(failed_run.created_at[:10])
    
    # 3. Download and save logs
    print("Downloading logs...")
    zip_filename = f"run_{failed_run.id}.zip"
    save_path = os.path.join(LOGS_DIR, zip_filename)
    
    try:
        success = api.download_logs(owner, repo, failed_run.id, save_path)
        if success:
            print("Saved to")
            print(f"backend/logs/{zip_filename}")
        else:
            print("Failed to download logs.")
    except Exception as e:
        import requests
        if isinstance(e, requests.exceptions.HTTPError) and e.response is not None and e.response.status_code == 403:
            print("Error downloading logs: 403 Client Error: Forbidden. Please ensure you have set a valid GITHUB_TOKEN in backend/.env.")
        else:
            print(f"Error downloading logs: {e}")

if __name__ == "__main__":
    main()
