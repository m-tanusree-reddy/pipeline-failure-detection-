import logging
import uuid
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

# Import Document from collector
try:
    from backend.retrieval.collector import Document
except ImportError:
    class Document(BaseModel):
        source: str
        title: str
        content: str
        url: str
        metadata: Dict[str, Any] = Field(default_factory=dict)

logger = logging.getLogger(__name__)

class Chunk(BaseModel):
    """
    Represents a semantic chunk of a larger Document.
    """
    chunk_id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="Unique identifier for the chunk.")
    document_id: str = Field(description="Identifier mapping back to the parent document.")
    source: str = Field(description="The source where the original document was retrieved from.")
    title: str = Field(description="Title of the parent document.")
    content: str = Field(description="The semantic chunk of text.")
    url: str = Field(description="URL or unique identifier of the parent document.")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Metadata inherited from the parent document.")
    chunk_index: int = Field(description="The index number of this chunk (1-based).")
    total_chunks: int = Field(description="Total number of chunks generated from the parent document.")

def chunk_document(document: Document, document_id: Optional[str] = None) -> List[Chunk]:
    """
    Splits a single Document into a list of Chunks using a word-based strategy.
    Max chunk size: 250 words. Overlap: 50 words.
    
    Args:
        document (Document): The document to chunk.
        document_id (Optional[str]): The ID of the document. If None, a UUID is generated.
        
    Returns:
        List[Chunk]: The list of generated chunks.
    """
    if not document.content.strip():
        logger.warning(f"Document '{document.title}' is empty. Skipping chunking.")
        return []

    doc_id = document_id or str(uuid.uuid4())
    words = document.content.split()
    
    chunk_size = 250
    overlap = 50
    step = chunk_size - overlap
    
    raw_chunks = []
    
    if len(words) <= chunk_size:
        raw_chunks.append(" ".join(words))
    else:
        for i in range(0, len(words), step):
            chunk_words = words[i:i + chunk_size]
            raw_chunks.append(" ".join(chunk_words))
            if i + chunk_size >= len(words):
                break
                
    total_chunks = len(raw_chunks)
    chunk_objects = []
    
    for idx, text_content in enumerate(raw_chunks, start=1):
        chunk = Chunk(
            document_id=doc_id,
            source=document.source,
            title=document.title,
            content=text_content,
            url=document.url,
            metadata=document.metadata,
            chunk_index=idx,
            total_chunks=total_chunks
        )
        chunk_objects.append(chunk)
        
    return chunk_objects

def chunk_documents(documents: List[Document]) -> List[Chunk]:
    """
    Processes a list of Documents and returns a flat list of Chunks.
    
    Args:
        documents (List[Document]): The list of collected documents.
        
    Returns:
        List[Chunk]: A flat list containing all chunks from all documents.
    """
    logger.info(f"Starting to chunk {len(documents)} documents.")
    all_chunks = []
    
    for doc in documents:
        try:
            chunks = chunk_document(doc)
            all_chunks.extend(chunks)
        except Exception as e:
            logger.warning(f"Failed to chunk document '{doc.title}': {e}. Skipping.", exc_info=True)
            continue
            
    logger.info(f"Finished chunking. Generated {len(all_chunks)} chunks total.")
    return all_chunks

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    
    # Generate sample documents
    short_content = "This is a very short document about GitHub Actions."
    medium_content = ("ModuleNotFoundError is a common error in Python when a dependency is missing. " * 30).strip()
    long_content = ("The package installation process failed due to missing requirements. " * 100).strip()
    empty_content = "   "
    
    docs = [
        Document(
            source="github_issues",
            title="Short GitHub Issue",
            content=short_content,
            url="https://github.com/example/1",
            metadata={"priority": "low"}
        ),
        Document(
            source="stackoverflow",
            title="Medium StackOverflow Answer",
            content=medium_content,
            url="https://stackoverflow.com/a/123",
            metadata={"votes": 100}
        ),
        Document(
            source="python_docs",
            title="Long Python Documentation",
            content=long_content,
            url="https://docs.python.org/3/installation",
            metadata={"version": "3.11"}
        ),
        Document(
            source="empty_source",
            title="Empty Document Test",
            content=empty_content,
            url="https://example.com/empty",
            metadata={}
        )
    ]
    
    chunks = chunk_documents(docs)
    
    # Group chunks by document for display matching the requested format
    from collections import defaultdict
    grouped = defaultdict(list)
    for c in chunks:
        grouped[c.document_id].append(c)
        
    for doc_id, doc_chunks in grouped.items():
        first_chunk = doc_chunks[0]
        print("==================================")
        print(f"Document")
        print(f"{first_chunk.title}")
        print(f"Chunks: {first_chunk.total_chunks}")
        print()
        
        for c in doc_chunks:
            word_count = len(c.content.split())
            preview = c.content[:100] + "..." if len(c.content) > 100 else c.content
            print(f"Chunk {c.chunk_index}")
            print(f"Words: {word_count}")
            print("Preview:")
            print(preview)
            print("----------------------------------")
        print("==================================\n")
