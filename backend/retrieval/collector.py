import logging
from typing import List, Dict, Any
from pydantic import BaseModel, Field

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
    # TODO: Implement actual GitHub Search API integration.
    return [
        Document(
            source="github_issues",
            title=f"Issue matching '{query}'",
            content=f"This is a simulated GitHub Issue discussion related to: {query}. It contains stack traces and developer comments.",
            url="https://github.com/example/repo/issues/42",
            metadata={"status": "closed", "author": "dev1"}
        )
    ]

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
    # TODO: Implement actual StackExchange API integration.
    return [
        Document(
            source="stackoverflow",
            title=f"StackOverflow Thread: {query}",
            content=f"Simulated StackOverflow accepted answer for {query}. The solution involves checking your dependencies and environment variables.",
            url="https://stackoverflow.com/questions/123456",
            metadata={"score": 150, "is_accepted": True}
        )
    ]

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
    # TODO: Implement actual docs scraping or search integration (e.g. Sphinx search API).
    return [
        Document(
            source="python_docs",
            title="Python Standard Library Reference",
            content=f"Documentation excerpt related to '{query}'. Describes the built-in modules and syntax.",
            url="https://docs.python.org/3/library/index.html",
            metadata={"version": "3.11"}
        )
    ]

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
    # TODO: Implement actual PyPI JSON API integration.
    return [
        Document(
            source="pypi_docs",
            title=f"PyPI Package Info: {query}",
            content=f"Simulated PyPI package readme and metadata for query: '{query}'.",
            url="https://pypi.org/search/?q=" + query.replace(" ", "+"),
            metadata={"package": query.split()[0]}
        )
    ]

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
    # TODO: Implement actual GitHub Docs search integration.
    return [
        Document(
            source="github_actions_docs",
            title="GitHub Actions Workflow Syntax",
            content=f"Simulated GitHub Actions documentation snippet covering topics like: '{query}'.",
            url="https://docs.github.com/en/actions",
            metadata={"topic": "workflows"}
        )
    ]

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
