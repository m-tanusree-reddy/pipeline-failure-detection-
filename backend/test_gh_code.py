import os
import requests
from dotenv import load_dotenv
load_dotenv()

token = os.getenv("GITHUB_TOKEN")
headers = {"Accept": "application/vnd.github.v3+json"}
if token:
    headers["Authorization"] = f"Bearer {token}"

url = "https://api.github.com/search/code"
# Search in github/docs repository, specifically in the content/actions directory
params = {"q": "setup-python repo:github/docs path:content/actions"}

res = requests.get(url, headers=headers, params=params)
print("Status:", res.status_code)
if res.status_code == 200:
    data = res.json()
    items = data.get("items", [])
    if items:
        for item in items[:2]:
            print("Found path:", item["path"])
            # Example path: content/actions/automating-builds-and-tests/building-and-testing-python.md
            # URL would be: https://docs.github.com/en/actions/automating-builds-and-tests/building-and-testing-python
            doc_url = "https://docs.github.com/en/" + item["path"].replace("content/", "").replace(".md", "")
            print("Doc URL:", doc_url)
            
            # Fetch raw content
            raw_url = f"https://raw.githubusercontent.com/github/docs/main/{item['path']}"
            raw_res = requests.get(raw_url)
            print("Raw status:", raw_res.status_code)
            if raw_res.status_code == 200:
                print("Raw content snippet:", raw_res.text[:100].replace('\n', ' '))
    else:
        print("No items found.")
else:
    print("Error:", res.text)
