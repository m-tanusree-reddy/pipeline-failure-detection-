import requests

try:
    url = "https://docs.github.com/api/search/v1"
    res = requests.get(url, params={"query": "setup-python", "client_name": "pipeline-failure-detector"}, headers={"Accept": "application/json"})
    print("GH Docs API Status:", res.status_code)
    if res.status_code == 200:
        data = res.json()
        hits = data.get("hits", [])
        if hits:
            print("Top hit URL:", hits[0].get("url"))
            print("Title:", hits[0].get("title"))
    else:
        print("Response:", res.text)
except Exception as e:
    print("Error:", e)
