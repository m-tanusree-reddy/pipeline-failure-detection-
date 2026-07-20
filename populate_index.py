import os
import sys

# Ensure backend modules can be imported if they use absolute imports like 'from models...'
sys.path.insert(0, os.path.abspath("backend"))

from backend.agents.planner import RetrievalPlan
from backend.retrieval.collector import collect_documents
from backend.retrieval.chunker import chunk_documents
from backend.retrieval.embedder import Embedder
from backend.retrieval.vector_store import VectorStore

plan = RetrievalPlan(
    queries=[
        "ModuleNotFoundError requests", 
        "npm install failure ERESOLVE", 
        "actions/cache", 
        "asyncio", 
        "json"
    ],
    sources=[
        "github_issues",
        "stackoverflow",
        "pypi",
        "python_docs",
        "github_actions_docs"
    ],
    top_k=2,
    reason="test"
)

print("Restoring real FAISS index...")
docs = collect_documents(plan)
print(f"Collected {len(docs)} documents.")
chunks = chunk_documents(docs)
print(f"Chunked into {len(chunks)} chunks.")
embedder = Embedder()
embedded_chunks = embedder.embed_chunks(chunks)
print("Building index...")
store = VectorStore()
store.build_index(embedded_chunks)
store.save_index("vector_store.faiss")
store.save_metadata("metadata.pkl")
print("Restored!")
