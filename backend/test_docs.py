import requests

# Test GitHub Docs Search API
try:
    print("Testing GH Actions Docs API...")
    url = "https://docs.github.com/api/search/v1"
    res = requests.get(url, params={"query": "setup-python"}, headers={"Accept": "application/json"})
    print("GH Docs API Status:", res.status_code)
    if res.status_code == 200:
        data = res.json()
        hits = data.get("hits", [])
        if hits:
            print("Top hit URL:", hits[0].get("url"))
    else:
        print("GH Docs API Response:", res.text)
except Exception as e:
    print("GH Docs error:", e)

# Test Python Docs heuristic
print("\nTesting Python Docs heuristic...")
keywords = ["asyncio", "json", "modulenotfounderror", "list"]
for kw in keywords:
    url = f"https://docs.python.org/3/library/{kw}.html"
    res = requests.get(url)
    print(f"URL: {url} -> Status: {res.status_code}")
    if res.status_code == 404:
        url_ref = f"https://docs.python.org/3/reference/{kw}.html"
        res_ref = requests.get(url_ref)
        print(f"URL: {url_ref} -> Status: {res_ref.status_code}")
