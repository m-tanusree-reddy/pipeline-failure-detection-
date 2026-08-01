import logging
import time
import numpy as np
from typing import List, Optional
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

_MODEL_CACHE = {}

def _get_sentence_transformer(model_name: str):
    """
    Lazy singleton helper to load and cache SentenceTransformer models on CPU.
    Defers importing heavy ML packages (torch, sentence_transformers) until called.
    """
    if model_name not in _MODEL_CACHE:
        try:
            import torch
            from sentence_transformers import SentenceTransformer
        except ImportError:
            raise ImportError("sentence-transformers library is not installed. Please install it to use the Embedder.")

        logger.info(f"Loading embedding model: {model_name} on CPU...")
        start_time = time.time()
        _MODEL_CACHE[model_name] = SentenceTransformer(model_name, device="cpu")
        logger.info(f"Model loaded successfully in {time.time() - start_time:.2f} seconds.")
    return _MODEL_CACHE[model_name]

try:
    from backend.retrieval.chunker import Chunk
except ImportError:
    # Fallback definition if chunker.py is not available in the environment
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
    """
    Represents a chunk of text that has been converted into a dense vector embedding.
    """
    chunk: Chunk = Field(description="The original Chunk object.")
    embedding: List[float] = Field(description="The dense vector representation of the chunk.")
    embedding_dimension: int = Field(description="The dimensionality of the embedding vector.")
    model_name: str = Field(description="The name of the model used to generate the embedding.")

class Embedder:
    """
    Responsible for converting Chunk objects into dense vector embeddings using SentenceTransformers.
    """
    def __init__(self, model_name: str = "BAAI/bge-small-en-v1.5"):
        self.model_name = model_name
        self.model = None

    def load_model(self) -> None:
        """
        Loads the SentenceTransformer model into memory (CPU only).
        Ensures the model is loaded only once.
        """
        if self.model is not None:
            return
            
        self.model = _get_sentence_transformer(self.model_name)

    def embed_chunk(self, chunk: Chunk) -> Optional[EmbeddedChunk]:
        """
        Embeds a single chunk.
        
        Args:
            chunk (Chunk): The chunk to embed.
            
        Returns:
            Optional[EmbeddedChunk]: The embedded chunk, or None if an error occurred.
        """
        result = self.embed_chunks([chunk])
        return result[0] if result else None

    def embed_chunks(self, chunks: List[Chunk], batch_size: int = 32) -> List[EmbeddedChunk]:
        """
        Embeds a list of chunks efficiently using batching.
        
        Args:
            chunks (List[Chunk]): The chunks to embed.
            batch_size (int): The number of chunks to process at once.
            
        Returns:
            List[EmbeddedChunk]: The successfully embedded chunks.
        """
        if not chunks:
            return []

        self.load_model()
        
        logger.info(f"Embedding started for {len(chunks)} chunks using model {self.model_name}...")
        start_time = time.time()
        
        embedded_chunks = []
        texts = [chunk.content for chunk in chunks]
        
        try:
            # Generate embeddings in batches. Setting show_progress_bar=False to keep logs clean.
            # Convert to numpy array for easier manipulation if needed, then to list of floats.
            embeddings = self.model.encode(texts, batch_size=batch_size, show_progress_bar=False, convert_to_numpy=True)
            
            # The dimension is the length of the first embedding vector
            embedding_dimension = embeddings.shape[1]
            
            for i, chunk in enumerate(chunks):
                try:
                    # Convert the numpy array for this specific chunk to a standard Python list of floats
                    emb_list = embeddings[i].tolist()
                    
                    embedded_chunk = EmbeddedChunk(
                        chunk=chunk,
                        embedding=emb_list,
                        embedding_dimension=embedding_dimension,
                        model_name=self.model_name
                    )
                    embedded_chunks.append(embedded_chunk)
                except Exception as e:
                    logger.error(f"Failed to create EmbeddedChunk for chunk_id {chunk.chunk_id}: {e}")
                    continue
                    
        except Exception as e:
            logger.error(f"Fatal error during batch embedding generation: {e}", exc_info=True)
            
        logger.info(f"Embedding completed. Successfully embedded {len(embedded_chunks)} chunks in {time.time() - start_time:.2f} seconds.")
        
        return embedded_chunks

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    
    # Create sample chunks
    sample_chunks = [
        Chunk(
            chunk_id="chunk_001",
            document_id="doc_123",
            source="github_issues",
            title="ModuleNotFoundError during CI",
            content="The pipeline failed with ModuleNotFoundError: No module named 'requests'.",
            url="https://github.com/example/issues/1",
            metadata={"priority": "high"},
            chunk_index=1,
            total_chunks=2
        ),
        Chunk(
            chunk_id="chunk_002",
            document_id="doc_123",
            source="github_issues",
            title="ModuleNotFoundError during CI",
            content="To fix this, you need to add requests to your requirements.txt file.",
            url="https://github.com/example/issues/1",
            metadata={"priority": "high"},
            chunk_index=2,
            total_chunks=2
        ),
        Chunk(
            chunk_id="chunk_003",
            document_id="doc_456",
            source="python_docs",
            title="Requests Library",
            content="Requests is an elegant and simple HTTP library for Python.",
            url="https://requests.readthedocs.io/",
            metadata={"version": "2.31.0"},
            chunk_index=1,
            total_chunks=1
        )
    ]
    
    embedder = Embedder()
    
    print("\nStarting batch embedding...")
    embedded_results = embedder.embed_chunks(sample_chunks)
    
    print("\n--- Output Validation ---")
    for result in embedded_results:
        print("====================================")
        print("Chunk")
        print(result.chunk.chunk_id)
        print("Dimension")
        print(result.embedding_dimension)
        print("Embedding Preview")
        # Format the first 10 floats to 4 decimal places
        preview = [round(val, 4) for val in result.embedding[:10]]
        print(str(preview).replace("]", ", ...]"))
        print("====================================\n")
