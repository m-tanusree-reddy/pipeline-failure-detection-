import requests
from bs4 import BeautifulSoup
import json

# Test GitHub Docs Search API
try:
    res = requests.get("https://docs.github.com/api/search/v1?query=workflow", headers={'Accept': 'application/json'}, timeout=5)
    print("GH Docs API:", res.status_code)
    if res.status_code == 200:
        print(list(res.json().keys()))
except Exception as e:
    print("GH Docs error:", e)

# Test PyPI JSON API
try:
    res = requests.get("https://pypi.org/pypi/requests/json", timeout=5)
    print("PyPI API:", res.status_code)
except Exception as e:
    print("PyPI error:", e)

# Test Python docs direct fetch
try:
    res = requests.get("https://docs.python.org/3/library/json.html", timeout=5)
    print("Python Docs:", res.status_code)
except Exception as e:
    print("Python Docs error:", e)
