import sys
from backend.retrieval.collector import retrieve_python_docs, retrieve_github_actions_docs

def check_doc(name, docs):
    if not docs:
        print(f"{name}: Failed (No docs returned)")
        return
    doc = docs[0]
    print(f"{name}: Success -> Title: {doc.title} | URL: {doc.url}")
    print(f"Content preview: {doc.content[:100]}...\n")

check_doc('retrieve_python_docs("asyncio", 1)', retrieve_python_docs("asyncio", 1))
check_doc('retrieve_python_docs("json", 1)', retrieve_python_docs("json", 1))
check_doc('retrieve_github_actions_docs("setup-python", 1)', retrieve_github_actions_docs("setup-python", 1))
check_doc('retrieve_github_actions_docs("actions/cache", 1)', retrieve_github_actions_docs("actions/cache", 1))
