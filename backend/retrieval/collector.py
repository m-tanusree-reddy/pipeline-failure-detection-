import os
import re
import logging
import requests
from bs4 import BeautifulSoup
from typing import List, Dict, Any
from pydantic import BaseModel, Field
from dotenv import load_dotenv

load_dotenv()

# We import RetrievalPlan from planner if available, otherwise define a fallback for type hinting.
try:
    from backend.agents.planner import RetrievalPlan
except ImportError:
    class RetrievalPlan(BaseModel):
        queries: List[str]
        sources: List[str]
        top_k: int
        reason: str = ""
        status: str = "planned"

logger = logging.getLogger(__name__)

class Document(BaseModel):
    """
    Represents a raw document retrieved from a knowledge source.
    """
    source: str = Field(description="The source where the document was retrieved from.")
    title: str = Field(description="Title or headline of the document.")
    content: str = Field(description="The raw text content of the document.")
    url: str = Field(description="URL or unique identifier for the document.")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional source-specific metadata.")

def retrieve_github_issues(query: str, top_k: int) -> List[Document]:
    """
    Retrieves relevant GitHub issues matching the query.
    
    Args:
        query (str): The search query.
        top_k (int): Maximum number of documents to retrieve.
        
    Returns:
        List[Document]: List of retrieved documents.
    """
    logger.info(f"Retrieving from GitHub Issues. Query: '{query}', Top K: {top_k}")
    documents = []
    try:
        token = os.getenv("GITHUB_TOKEN")
        headers = {"Accept": "application/vnd.github.v3+json"}
        if token:
            headers["Authorization"] = f"Bearer {token}"
            
        url = "https://api.github.com/search/issues"
        params = {"q": f"{query} type:issue", "per_page": top_k}
        
        response = requests.get(url, headers=headers, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        for item in data.get("items", [])[:top_k]:
            documents.append(
                Document(
                    source="github_issues",
                    title=item.get("title", ""),
                    content=item.get("body") or "",
                    url=item.get("html_url", ""),
                    metadata={
                        "repository": item.get("repository_url", "").split("/")[-1] if item.get("repository_url") else "",
                        "state": item.get("state", ""),
                        "comments": item.get("comments", 0),
                        "labels": [label.get("name") for label in item.get("labels", [])],
                        "author": item.get("user", {}).get("login", "") if item.get("user") else "",
                        "created_at": item.get("created_at", ""),
                        "updated_at": item.get("updated_at", "")
                    }
                )
            )
    except Exception as e:
        logger.error(f"Failed to retrieve GitHub issues: {e}")
    return documents

def retrieve_stackoverflow(query: str, top_k: int) -> List[Document]:
    """
    Retrieves relevant StackOverflow answers matching the query.
    
    Args:
        query (str): The search query.
        top_k (int): Maximum number of documents to retrieve.
        
    Returns:
        List[Document]: List of retrieved documents.
    """
    logger.info(f"Retrieving from StackOverflow. Query: '{query}', Top K: {top_k}")
    documents = []
    try:
        url = "https://api.stackexchange.com/2.3/search/advanced"
        params = {
            "order": "desc",
            "sort": "relevance",
            "q": query,
            "site": "stackoverflow",
            "pagesize": top_k,
            "filter": "withbody"
        }
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        for item in data.get("items", [])[:top_k]:
            documents.append(
                Document(
                    source="stackoverflow",
                    title=item.get("title", ""),
                    content=item.get("body", ""),
                    url=item.get("link", ""),
                    metadata={
                        "score": item.get("score", 0),
                        "tags": item.get("tags", []),
                        "is_answered": item.get("is_answered", False),
                        "accepted_answer_id": item.get("accepted_answer_id")
                    }
                )
            )
    except Exception as e:
        logger.error(f"Failed to retrieve StackOverflow answers: {e}")
    return documents

def extract_python_keywords(query: str) -> list[str]:
    """Helper to extract meaningful Python-related keywords from a query."""
    # Remove punctuation except dots and underscores
    clean_query = re.sub(r'[^a-zA-Z0-9\s_.]', ' ', query)
    words = clean_query.split()
    
    # Common stop words to ignore
    stop_words = {"no", "module", "named", "how", "to", "in", "python", "error", "exception", "the", "a", "an", "is", "for", "with", "and", "or", "not"}
    
    keywords = []
    for w in words:
        w_lower = w.lower()
        if w_lower not in stop_words and len(w_lower) > 1:
            keywords.append(w)
    return keywords

def retrieve_python_docs(query: str, top_k: int) -> List[Document]:
    """
    Retrieves relevant official Python documentation.
    
    Args:
        query (str): The search query.
        top_k (int): Maximum number of documents to retrieve.
        
    Returns:
        List[Document]: List of retrieved documents.
    """
    logger.info(f"Retrieving from Python Docs. Query: '{query}', Top K: {top_k}")
    documents = []
    try:
        # 1. Extract meaningful Python-related keywords from the query
        keywords = extract_python_keywords(query)
        if not keywords:
            logger.warning(f"No meaningful keywords extracted from query: '{query}'")
            return documents
            
        # 2. Build potential documentation URLs based on the keywords
        urls_to_try = []
        for kw in keywords:
            kw_lower = kw.lower()
            if kw_lower.endswith("error") or kw_lower.endswith("exception"):
                urls_to_try.append(("exceptions", "https://docs.python.org/3/library/exceptions.html"))
            elif kw_lower in ["list", "dict", "set", "tuple", "str", "int", "float", "bool"]:
                urls_to_try.append(("stdtypes", "https://docs.python.org/3/library/stdtypes.html"))
            else:
                module = kw_lower.split(".")[0]
                urls_to_try.append((module, f"https://docs.python.org/3/library/{module}.html"))
                
        # Deduplicate URLs while preserving order
        seen = set()
        unique_urls = []
        for u in urls_to_try:
            if u[1] not in seen:
                seen.add(u[1])
                unique_urls.append(u)
                
        # 3. Retrieve the most relevant documentation pages
        for module_name, url in unique_urls:
            if len(documents) >= top_k:
                break
                
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                # 4. Parse the useful documentation text
                soup = BeautifulSoup(response.text, "html.parser")
                body = soup.find("div", class_="body")
                content = body.get_text(separator="\n", strip=True) if body else soup.get_text(separator="\n", strip=True)
                
                # Truncate extremely long pages to avoid blowing up context window
                if len(content) > 10000:
                    content = content[:10000] + "\n...[truncated]"
                    
                title = soup.title.string if soup.title else f"Python {module_name} Docs"
                
                # 5. Return Document
                documents.append(
                    Document(
                        source="python_docs",
                        title=title,
                        content=content,
                        url=url,
                        metadata={"module": module_name}
                    )
                )
            else:
                logger.warning(f"Python docs for '{module_name}' returned status {response.status_code}")
                
    except Exception as e:
        logger.error(f"Failed to retrieve Python docs: {e}")
    return documents

def retrieve_pypi_docs(query: str, top_k: int) -> List[Document]:
    """
    Retrieves package descriptions and documentation from PyPI.
    
    Args:
        query (str): The search query.
        top_k (int): Maximum number of documents to retrieve.
        
    Returns:
        List[Document]: List of retrieved documents.
    """
    logger.info(f"Retrieving from PyPI Docs. Query: '{query}', Top K: {top_k}")
    documents = []
    try:
        package_name = query.split()[0].strip().lower()
        if not package_name:
            return documents
            
        url = f"https://pypi.org/pypi/{package_name}/json"
        response = requests.get(url, timeout=10)
        
        if response.status_code == 404:
            logger.warning(f"PyPI package '{package_name}' not found.")
            return documents
            
        response.raise_for_status()
        data = response.json()
        info = data.get("info", {})
        
        documents.append(
            Document(
                source="pypi_docs",
                title=info.get("name", package_name),
                content=info.get("description") or info.get("summary") or "",
                url=info.get("project_url") or info.get("package_url") or "",
                metadata={
                    "version": info.get("version", ""),
                    "summary": info.get("summary", ""),
                    "author": info.get("author", "")
                }
            )
        )
    except Exception as e:
        logger.error(f"Failed to retrieve PyPI docs: {e}")
    return documents

def retrieve_github_actions_docs(query: str, top_k: int) -> List[Document]:
    """
    Retrieves GitHub Actions official documentation.
    
    Args:
        query (str): The search query.
        top_k (int): Maximum number of documents to retrieve.
        
    Returns:
        List[Document]: List of retrieved documents.
    """
    logger.info(f"Retrieving from GitHub Actions Docs. Query: '{query}', Top K: {top_k}")
    documents = []
    try:
        # We query the official GitHub docs repository using the core GitHub Search API
        token = os.getenv("GITHUB_TOKEN")
        headers = {"Accept": "application/vnd.github.v3+json"}
        if token:
            headers["Authorization"] = f"Bearer {token}"
            
        search_url = "https://api.github.com/search/code"
        # Search the official github/docs repository, scoping specifically to the content/actions folder
        params = {
            "q": f"{query} repo:github/docs path:content/actions",
            "per_page": top_k
        }
        
        response = requests.get(search_url, params=params, headers=headers, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            items = data.get("items", [])
            
            if not items:
                logger.warning(f"No GitHub Actions docs found for query: '{query}'")
                return documents
                
            for item in items[:top_k]:
                repo_path = item.get("path", "")
                if not repo_path:
                    continue
                    
                # Construct the canonical docs.github.com URL from the markdown path
                # e.g., "content/actions/using-workflows/caching.md" -> "https://docs.github.com/en/actions/using-workflows/caching"
                doc_path_clean = repo_path.replace("content/", "").replace(".md", "")
                full_url = f"https://docs.github.com/en/{doc_path_clean}"
                
                # Extract a readable title from the filename
                title = item.get("name", "").replace("-", " ").replace(".md", "").title()
                
                # Fetch the raw markdown content directly from the repository
                raw_url = f"https://raw.githubusercontent.com/github/docs/main/{repo_path}"
                raw_res = requests.get(raw_url, timeout=10)
                
                if raw_res.status_code == 200:
                    content_text = raw_res.text
                    
                    if len(content_text) > 10000:
                        content_text = content_text[:10000] + "\n...[truncated]"
                        
                    documents.append(
                        Document(
                            source="github_actions_docs",
                            title=title,
                            content=content_text,
                            url=full_url,
                            metadata={"repo_path": repo_path}
                        )
                    )
                else:
                    logger.warning(f"Failed to fetch raw markdown for: {repo_path}")
        else:
            logger.warning(f"GitHub Code Search API returned {response.status_code}: {response.text}")
            
    except Exception as e:
        logger.error(f"Failed to retrieve GitHub Actions docs: {e}")
    return documents

def retrieve_historical_logs(query: str, top_k: int) -> List[Document]:
    """
    Retrieves similar past CI/CD failure logs from internal historical data.
    
    Args:
        query (str): The search query.
        top_k (int): Maximum number of documents to retrieve.
        
    Returns:
        List[Document]: List of retrieved documents.
    """
    logger.info(f"Retrieving from Historical Logs. Query: '{query}', Top K: {top_k}")
    # TODO: Implement actual internal log database search (e.g. Elasticsearch or vector DB).
    return [
        Document(
            source="historical_logs",
            title=f"Past Pipeline Failure: {query}",
            content=f"Simulated historical pipeline log showing a similar failure. Resolution was: updating the base image.",
            url="internal://logs/run_87654",
            metadata={"run_id": "87654", "date": "2023-09-12"}
        )
    ]

def collect_documents(plan: RetrievalPlan) -> List[Document]:
    """
    Iterates through the requested sources, executes queries, and merges documents.
    
    Args:
        plan (RetrievalPlan): The plan containing queries, sources, and top_k.
        
    Returns:
        List[Document]: A flat list of all collected documents.
    """
    logger.info("Starting document collection based on RetrievalPlan.")
    
    # Map source names to their respective retrieval functions
    source_to_func = {
        "github_issues": retrieve_github_issues,
        "stackoverflow": retrieve_stackoverflow,
        "python_docs": retrieve_python_docs,
        "pypi_docs": retrieve_pypi_docs,
        "github_actions_docs": retrieve_github_actions_docs,
        "historical_logs": retrieve_historical_logs
    }
    
    collected_docs = []
    
    for source in plan.sources:
        func = source_to_func.get(source)
        if not func:
            logger.warning(f"Unknown source '{source}' requested. Skipping.")
            continue
            
        for query in plan.queries:
            try:
                docs = func(query=query, top_k=plan.top_k)
                collected_docs.extend(docs)
            except Exception as e:
                # Log failures but continue pipeline execution
                logger.error(f"Error retrieving from {source} for query '{query}': {e}", exc_info=True)
                
    logger.info(f"Finished collection. Retrieved {len(collected_docs)} documents in total.")
    return collected_docs


if __name__ == "__main__":
    import json
    
    # Configure basic logging for the test
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    
    # Create a sample RetrievalPlan
    sample_plan = RetrievalPlan(
        queries=[
            "No module named requests",
            "ModuleNotFoundError GitHub Actions"
        ],
        sources=[
            "github_issues",
            "stackoverflow",
            "python_docs",
            "historical_logs"
        ],
        top_k=2,
        reason="Testing the document collector."
    )
    
    print("--- Starting Document Collection ---")
    documents = collect_documents(sample_plan)
    
    print("\n--- Collected Documents ---")
    for idx, doc in enumerate(documents, start=1):
        print(f"\nDocument #{idx}")
        print(json.dumps(doc.model_dump(), indent=4))
