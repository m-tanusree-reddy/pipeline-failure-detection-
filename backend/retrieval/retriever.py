import logging
import time
import numpy as np
from typing import List, Optional
from pydantic import BaseModel, Field

from backend.retrieval.chunker import Chunk
from backend.retrieval.embedder import Embedder, EmbeddedChunk
from backend.retrieval.vector_store import VectorStore

logger = logging.getLogger(__name__)

class RetrievedDocument(BaseModel):
    """
    Represents a chunk retrieved from the vector store during a similarity search.
    """
    chunk: Chunk = Field(description="The original semantic chunk recovered from metadata.")
    score: float = Field(description="The L2 distance score from FAISS. Lower is better.")
    rank: int = Field(description="The sorted rank position of this document in the top-k results.")

class Retriever:
    """
    Responsible ONLY for performing semantic similarity search against the vector store.
    """
    
    def __init__(self, index_filename: str = "vector_store.faiss", metadata_filename: str = "metadata.pkl"):
        """
        Initializes the Retriever.
        
        Args:
            index_filename (str): The filename of the FAISS index to load.
            metadata_filename (str): The filename of the metadata mapping to load.
        """
        self.index_filename = index_filename
        self.metadata_filename = metadata_filename
        self.vector_store = VectorStore()
        self.embedder = Embedder()
        self.embedder.load_model()
        self.is_loaded = False

    def load_vector_store(self) -> None:
        """
        Loads the FAISS index and metadata mapping from disk into memory.
        """
        if self.is_loaded:
            return
            
        logger.info("Loading vector store and metadata...")
        try:
            self.vector_store.load_index(self.index_filename)
            self.vector_store.load_metadata(self.metadata_filename)
            
            if self.vector_store.index is None or not self.vector_store.metadata_mapping:
                logger.warning("Vector store or metadata is empty after loading. Retrieval will return empty results.")
                self.is_loaded = False
                return
                
            self.is_loaded = True
            logger.info("Vector store loaded successfully.")
        except FileNotFoundError:
            logger.warning(f"Vector store index '{self.index_filename}' not found. Retrieval will return empty results.")
            self.is_loaded = False
        except Exception as e:
            logger.error(f"Failed to load vector store: {e}")
            self.is_loaded = False

    def embed_query(self, query: str) -> np.ndarray:
        """
        Converts a plain text query into a dense embedding vector using the Embedder.
        
        Args:
            query (str): The user search query.
            
        Returns:
            np.ndarray: The dense vector representing the query.
        """
        if not query or not query.strip():
            raise ValueError("The search query cannot be empty.")
            
        logger.info(f"Embedding query: '{query}'")
        
        # We wrap the query in a dummy Chunk to satisfy the embedder interface.
        # However, the embedder actually has a model.encode() method we can use directly for speed
        # if we instantiate the model. The cleanest way is to use the Embedder's model directly 
        # or create a temporary chunk. Let's create a temporary chunk.
        
        dummy_chunk = Chunk(
            chunk_id="query",
            document_id="query",
            source="user",
            title="query",
            content=query,
            url="",
            metadata={},
            chunk_index=1,
            total_chunks=1
        )
        
        embedded_chunk = self.embedder.embed_chunk(dummy_chunk)
        if not embedded_chunk:
            raise RuntimeError("Failed to generate embedding for the query.")
            
        return np.array([embedded_chunk.embedding], dtype=np.float32)

    def retrieve(self, query: str, top_k: int = 5) -> List[RetrievedDocument]:
        """
        Performs a semantic similarity search to find the nearest chunks.
        
        Args:
            query (str): The search query.
            top_k (int): The number of closest matches to return.
            
        Returns:
            List[RetrievedDocument]: The ranked retrieved documents.
        """
        if top_k <= 0:
            raise ValueError("top_k must be greater than 0.")
            
        # Ensure resources are loaded
        self.load_vector_store()
        if not self.is_loaded:
            logger.warning("Vector store is not loaded or missing. Returning empty results.")
            return []
        
        start_time = time.time()
        
        # 1. Convert query to vector
        query_vector = self.embed_query(query)
        
        # 2. Perform FAISS search
        logger.info(f"Searching index for top {top_k} results...")
        distances, indices = self.vector_store.index.search(query_vector, top_k)
        
        # 3. Recover matching chunks from metadata
        retrieved_docs = []
        rank = 1
        
        # distances and indices are 2D arrays, we take the first row since we only have one query
        for dist, idx in zip(distances[0], indices[0]):
            # FAISS returns -1 if there are not enough vectors in the index to fill top_k
            if idx == -1:
                continue
                
            embedded_chunk = self.vector_store.metadata_mapping.get(idx)
            if not embedded_chunk:
                logger.error(f"Missing metadata for vector ID {idx}. Database is corrupted.")
                raise ValueError(f"Missing metadata mapping for retrieved vector ID {idx}.")
                
            doc = RetrievedDocument(
                chunk=embedded_chunk.chunk,
                score=float(dist),
                rank=rank
            )
            retrieved_docs.append(doc)
            rank += 1
            
        search_time = time.time() - start_time
        logger.info(f"Retrieved {len(retrieved_docs)} chunks in {search_time:.3f} seconds.")
        
        return retrieved_docs

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    
    # 1. Create Sample Chunks simulating multiple sources to test semantic matching
    samples = [
        Chunk(
            chunk_id="chunk_req_docs", document_id="doc_req", source="python_docs", title="requests Docs",
            content="The requests module in Python allows you to send HTTP requests easily.", url="https://docs.python.org/requests",
            metadata={"module": "requests"}, chunk_index=1, total_chunks=1
        ),
        Chunk(
            chunk_id="chunk_pypi", document_id="doc_pypi", source="pypi", title="requests Package",
            content="PyPI package for requests. To install, run pip install requests.", url="https://pypi.org/project/requests/",
            metadata={"version": "2.31.0"}, chunk_index=1, total_chunks=1
        ),
        Chunk(
            chunk_id="chunk_so_req", document_id="doc_so1", source="stackoverflow", title="ModuleNotFoundError requests",
            content="If you get ModuleNotFoundError: No module named requests, you haven't installed the package in your virtualenv.", url="https://so.com/q/1",
            metadata={"votes": 120}, chunk_index=1, total_chunks=1
        ),
        Chunk(
            chunk_id="chunk_npm_gh", document_id="doc_npm1", source="github_issues", title="npm install fails in CI",
            content="My GitHub Actions workflow fails on npm install with a network timeout error.", url="https://github.com/issues/npm",
            metadata={"status": "open"}, chunk_index=1, total_chunks=1
        ),
        Chunk(
            chunk_id="chunk_npm_so", document_id="doc_npm2", source="stackoverflow", title="npm install ERESOLVE",
            content="NPM install failure due to ERESOLVE unable to resolve dependency tree.", url="https://so.com/q/2",
            metadata={"votes": 45}, chunk_index=1, total_chunks=1
        ),
        Chunk(
            chunk_id="chunk_cache_docs", document_id="doc_cache1", source="github_actions_docs", title="actions/cache",
            content="The actions/cache action allows caching dependencies to speed up workflows.", url="https://docs.github.com/en/actions/using-workflows/caching",
            metadata={"topic": "cache"}, chunk_index=1, total_chunks=1
        ),
        Chunk(
            chunk_id="chunk_cache_gh", document_id="doc_cache2", source="github_issues", title="actions/cache not restoring",
            content="My actions/cache step doesn't restore the npm cache properly across different runners.", url="https://github.com/issues/cache",
            metadata={"status": "closed"}, chunk_index=1, total_chunks=1
        )
    ]
    
    print("--- Preparing Test Data ---")
    embedder = Embedder()
    embedded_samples = embedder.embed_chunks(samples)
    
    store = VectorStore()
    store.build_index(embedded_samples)
    store.save_index("test_vector_store.faiss")
    store.save_metadata("test_metadata.pkl")
    
    print("\n--- Testing Retriever ---")
    retriever = Retriever(index_filename="test_vector_store.faiss", metadata_filename="test_metadata.pkl")
    
    test_queries = [
        "ModuleNotFoundError requests",
        "npm install failure",
        "actions/cache"
    ]
    
    for query in test_queries:
        print("===================================================")
        print("Query:", query)
        print("\nTop Results\n")
        
        results = retriever.retrieve(query, top_k=3)
        
        for res in results:
            print(f"Rank {res.rank} | Score: {res.score:.4f} | Source: {res.chunk.source}")
            print(f"Title: {res.chunk.title}")
            print(f"Metadata: {res.chunk.metadata}")
            preview = res.chunk.content[:80] + "..." if len(res.chunk.content) > 80 else res.chunk.content
            print(f"Preview: {preview}")
            print("------------------------")
            
        print("===================================================\n")
