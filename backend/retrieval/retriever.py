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
                raise ValueError("Vector store or metadata is empty after loading.")
                
            self.is_loaded = True
            logger.info("Vector store loaded successfully.")
        except Exception as e:
            logger.error(f"Failed to load vector store: {e}")
            raise

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
    
    # 1. Create Sample Chunks
    samples = [
        Chunk(
            chunk_id="chunk_1",
            document_id="doc_1",
            source="stackoverflow",
            title="ImportError Resolution",
            content="If you get No module named requests, you must run pip install requests.",
            url="https://stackoverflow.com/a/1",
            metadata={"votes": 50},
            chunk_index=1,
            total_chunks=1
        ),
        Chunk(
            chunk_id="chunk_2",
            document_id="doc_2",
            source="github_actions_docs",
            title="Exit Codes",
            content="When a step fails, GitHub Actions returns exit code 1. This stops the workflow.",
            url="https://docs.github.com/actions",
            metadata={"topic": "workflows"},
            chunk_index=1,
            total_chunks=1
        ),
        Chunk(
            chunk_id="chunk_3",
            document_id="doc_3",
            source="github_issues",
            title="Package not found",
            content="Dependency installation failed because the package doesn't exist on PyPI.",
            url="https://github.com/issues/5",
            metadata={"status": "open"},
            chunk_index=1,
            total_chunks=1
        )
    ]
    
    print("--- Preparing Test Data ---")
    embedder = Embedder()
    embedded_samples = embedder.embed_chunks(samples)
    
    store = VectorStore()
    store.build_index(embedded_samples)
    store.save_index()
    store.save_metadata()
    
    print("\n--- Testing Retriever ---")
    retriever = Retriever()
    
    test_queries = [
        "No module named requests",
        "GitHub Actions exit code 1",
        "Dependency installation failed"
    ]
    
    for query in test_queries:
        print("===================================================")
        print("Query")
        print(query)
        print("\nTop Results\n")
        
        results = retriever.retrieve(query, top_k=2)
        
        for res in results:
            print(f"Rank {res.rank}")
            print(f"Score: {res.score:.4f}")
            print(f"Chunk ID: {res.chunk.chunk_id}")
            print(f"Source: {res.chunk.source}")
            print(f"Title: {res.chunk.title}")
            
            preview = res.chunk.content[:100] + "..." if len(res.chunk.content) > 100 else res.chunk.content
            print(f"Content Preview: {preview}")
            print("------------------------")
            
        print("===================================================\n")
