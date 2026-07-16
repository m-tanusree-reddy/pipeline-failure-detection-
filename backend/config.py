from dotenv import load_dotenv
import os

# Load environment variables from .env relative to this file
dotenv_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
load_dotenv(dotenv_path)

# GitHub API Configuration
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "")
GITHUB_API_URL = os.getenv("GITHUB_API_URL", "https://api.github.com")
TIMEOUT = int(os.getenv("TIMEOUT", "30"))

# Application Settings
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOGS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs")

# Ensure logs directory exists
os.makedirs(LOGS_DIR, exist_ok=True)

# Gemini API Configuration
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.1-flash-lite")
