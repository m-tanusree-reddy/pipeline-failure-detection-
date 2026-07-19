import requests
import os

urls = {
    "dashboard_upload.html": "https://contribution.usercontent.google.com/download?c=CgthaWRhX2NvZGVmeBJ7Eh1hcHBfY29tcGFuaW9uX2dlbmVyYXRlZF9maWxlcxpaCiVodG1sX2IyNzY2YTVkMTJlODRmZGZiZDg1OWFjNzI2M2MxNDM4EgsSBxCAwfOToAgYAZIBIwoKcHJvamVjdF9pZBIVQhMzODA3MzI3NTM1ODQ3NTU4MjIx&filename=&opi=89354086",
    "landing_page.html": "https://contribution.usercontent.google.com/download?c=CgthaWRhX2NvZGVmeBJ7Eh1hcHBfY29tcGFuaW9uX2dlbmVyYXRlZF9maWxlcxpaCiVodG1sXzY2Mjc2MTUyYjI4MTQwNThhNTVjN2QxZTRmMTIzYjBhEgsSBxCAwfOToAgYAZIBIwoKcHJvamVjdF9pZBIVQhMzODA3MzI3NTM1ODQ3NTU4MjIx&filename=&opi=89354086",
    "architecture.html": "https://contribution.usercontent.google.com/download?c=CgthaWRhX2NvZGVmeBJ7Eh1hcHBfY29tcGFuaW9uX2dlbmVyYXRlZF9maWxlcxpaCiVodG1sXzI3NTU4YmQyMjRjNjQ3YWQ5YzhmZTlkMDFkOTUwNzk4EgsSBxCAwfOToAgYAZIBIwoKcHJvamVjdF9pZBIVQhMzODA3MzI3NTM1ODQ3NTU4MjIx&filename=&opi=89354086",
    "dashboard_results.html": "https://contribution.usercontent.google.com/download?c=CgthaWRhX2NvZGVmeBJ7Eh1hcHBfY29tcGFuaW9uX2dlbmVyYXRlZF9maWxlcxpaCiVodG1sX2FhNjJmMTg1M2NkNTQzZWNiMGFkZjMzZGFlMTk5MzhmEgsSBxCAwfOToAgYAZIBIwoKcHJvamVjdF9pZBIVQhMzODA3MzI3NTM1ODQ3NTU4MjIx&filename=&opi=89354086"
}

os.makedirs("scratch", exist_ok=True)

for name, url in urls.items():
    print(f"Downloading {name}...")
    try:
        r = requests.get(url, timeout=10)
        r.raise_for_status()
        with open(os.path.join("scratch", name), "w", encoding="utf-8") as f:
            f.write(r.text)
        print(f"Saved {name}")
    except Exception as e:
        print(f"Failed to download {name}: {e}")
