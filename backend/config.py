# pyrefly: ignore [missing-import]
from dotenv import load_dotenv
import os

# Load environment variables: check project root first, then backend/.env
root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
root_env = os.path.join(root_dir, ".env")
if os.path.exists(root_env):
    load_dotenv(root_env)

dotenv_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
if os.path.exists(dotenv_path):
    load_dotenv(dotenv_path)

# GitHub API & OAuth Configuration
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "")
GITHUB_API_URL = os.getenv("GITHUB_API_URL", "https://api.github.com")
GITHUB_CLIENT_ID = os.getenv("GITHUB_CLIENT_ID", "")
GITHUB_CLIENT_SECRET = os.getenv("GITHUB_CLIENT_SECRET", "")
GITHUB_OAUTH_REDIRECT_URI = os.getenv("GITHUB_OAUTH_REDIRECT_URI", "")
TIMEOUT = int(os.getenv("TIMEOUT", "30"))

# Gemini API Configuration
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-flash-latest")

# Application Settings
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOGS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs")

# Ensure logs directory exists
os.makedirs(LOGS_DIR, exist_ok=True)

# Gemini API Configuration
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.1-flash-lite")

# Allowed CORS Origins (comma separated list, defaults to ["*"])
ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "*").split(",")

