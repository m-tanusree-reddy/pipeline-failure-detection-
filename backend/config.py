import os

# GitHub API Configuration
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "")
GITHUB_REPOSITORY = os.getenv("GITHUB_REPOSITORY", "")  # e.g., "owner/repo"

# Application Settings
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOGS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs")

# Ensure logs directory exists
os.makedirs(LOGS_DIR, exist_ok=True)
