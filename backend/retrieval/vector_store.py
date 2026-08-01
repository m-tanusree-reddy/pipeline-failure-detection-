import logging
import pickle
from pathlib import Path
from typing import List, Dict, Optional
import numpy as np

def _get_faiss():
    """
    Lazy loader helper for faiss.
    Defers loading faiss library until vector store index operations are invoked.
    """
    try:
        import faiss
        return faiss
    except ImportError:
        raise ImportError("faiss package is not installed. Please install faiss-cpu to use VectorStore.")

# Fallback models in case the previous modules can't be imported during isolation testing
try:
    from backend.retrieval.embedder import EmbeddedChunk
    from backend.retrieval.chunker import Chunk
except ImportError:
    from pydantic import BaseModel, Field
    class Chunk(BaseModel):
        chunk_id: str
        document_id: str
        source: str
        title: str
        content: str
        url: str
        metadata: dict
        chunk_index: int
        total_chunks: int

    class EmbeddedChunk(BaseModel):
        chunk: Chunk
        embedding: List[float]
        embedding_dimension: int
        model_name: str

BASE_DIR = Path(__file__).resolve().parent.parent
VECTOR_DB_DIR = BASE_DIR / "vector_db"
VECTOR_DB_DIR.mkdir(parents=True, exist_ok=True)

logger = logging.getLogger(__name__)

class VectorStore:
    """
    Responsible ONLY for building and managing a FAISS index and its associated metadata mapping.
    """
    
    def __init__(self):
        """
        Initializes an empty VectorStore.
        """
        self.index = None
        self.metadata_mapping: Dict[int, EmbeddedChunk] = {}

    def build_index(self, embedded_chunks: List[EmbeddedChunk]) -> None:
        """
        Builds a FAISS IndexFlatL2 from a list of EmbeddedChunks.
        
        Args:
            embedded_chunks (List[EmbeddedChunk]): The chunks containing vector embeddings.
            
        Raises:
            ValueError: If the list is empty or if dimensions are inconsistent.
        """
        logger.info("Building index...")
        
        if not embedded_chunks:
            raise ValueError("The provided list of embedded chunks is empty. Cannot build index.")
            
        # Verify consistent dimensions
        first_dim = embedded_chunks[0].embedding_dimension
        for i, ec in enumerate(embedded_chunks):
            if ec.embedding_dimension != first_dim or len(ec.embedding) != first_dim:
                raise ValueError(f"Inconsistent embedding dimensions detected at index {i}. Expected {first_dim}.")
                
        # Prepare vectors
        vectors = np.array([ec.embedding for ec in embedded_chunks], dtype=np.float32)
        
        # Initialize FAISS index
        faiss_lib = _get_faiss()
        self.index = faiss_lib.IndexFlatL2(first_dim)
        
        # Add vectors to index
        self.index.add(vectors)
        
        # Build metadata mapping (FAISS sequential ID -> EmbeddedChunk)
        self.metadata_mapping = {i: chunk for i, chunk in enumerate(embedded_chunks)}
        
        logger.info(f"Index built successfully. Dimension: {first_dim}, Number of vectors: {self.get_total_vectors()}")

    def save_index(self, filename: str = "vector_store.faiss") -> None:
        """
        Saves the FAISS index to disk.
        
        Args:
            filename (str): Filename where the index should be saved.
        """
        if self.index is None:
            logger.warning("No index to save.")
            return
            
        path = VECTOR_DB_DIR / filename
        
        logger.info(f"Saving index to {path}...")
        _get_faiss().write_index(self.index, str(path))
        logger.info("Index saved successfully.")

    def load_index(self, filename: str = "vector_store.faiss") -> None:
        """
        Loads a FAISS index from disk.
        
        Args:
            filename (str): Filename where the index is stored.
        """
        path = VECTOR_DB_DIR / filename
        if not path.exists():
            raise FileNotFoundError(f"FAISS index file not found: {path}")
            
        logger.info(f"Loading index from {path}...")
        self.index = _get_faiss().read_index(str(path))
        logger.info("Index loaded successfully.")

    def save_metadata(self, filename: str = "metadata.pkl") -> None:
        """
        Saves the metadata dictionary mapping to disk using pickle.
        
        Args:
            filename (str): Filename where metadata should be saved.
        """
        path = VECTOR_DB_DIR / filename
        
        logger.info(f"Saving metadata to {path}...")
        with open(path, "wb") as f:
            pickle.dump(self.metadata_mapping, f)
        logger.info("Metadata saved successfully.")

    def load_metadata(self, filename: str = "metadata.pkl") -> None:
        """
        Loads the metadata dictionary mapping from disk using pickle.
        
        Args:
            filename (str): Filename where metadata is stored.
        """
        path = VECTOR_DB_DIR / filename
        if not path.exists():
            raise FileNotFoundError(f"Metadata file not found: {path}")
            
        logger.info(f"Loading metadata from {path}...")
        with open(path, "rb") as f:
            self.metadata_mapping = pickle.load(f)
        logger.info("Metadata loaded successfully.")

    def get_total_vectors(self) -> int:
        """
        Gets the total number of vectors in the current FAISS index.
        
        Returns:
            int: The total number of vectors.
        """
        if self.index is None:
            return 0
        return self.index.ntotal


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    
    # Generate sample EmbeddedChunk objects
    dim = 384
    
    samples = []
    for i in range(3):
        chunk = Chunk(
            chunk_id=f"chunk_{i}",
            document_id=f"doc_{i}",
            source="test_source",
            title=f"Test Title {i}",
            content=f"Sample text content for chunk {i}",
            url="https://test.com",
            metadata={"test_key": "test_val"},
            chunk_index=1,
            total_chunks=1
        )
        
        emb_chunk = EmbeddedChunk(
            chunk=chunk,
            embedding=np.random.rand(dim).tolist(),
            embedding_dimension=dim,
            model_name="BAAI/bge-small-en-v1.5"
        )
        samples.append(emb_chunk)
        
    store = VectorStore()
    
    print("--- Building Vector Store ---")
    store.build_index(samples)
    
    print("\n--- Saving to Disk ---")
    store.save_index("vector_store.faiss")
    store.save_metadata("metadata.pkl")
    
    print("\n--- Reloading from Disk ---")
    new_store = VectorStore()
    new_store.load_index("vector_store.faiss")
    new_store.load_metadata("metadata.pkl")
    
    print("\n--- Output Validation ---")
    print("Index loaded successfully.")
    print("Metadata loaded successfully.")
    print(f"Dimension: {new_store.index.d}")
    print(f"Total vectors: {new_store.get_total_vectors()}")

    print("\nVector database location:")
    print(str(VECTOR_DB_DIR))
