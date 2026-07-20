import os
import sys
import codecs
from typing import List

# Ensure windows console encoding doesn't crash on fancy quotes
sys.stdout = codecs.getwriter("utf-8")(sys.stdout.detach())

from backend.retrieval.retriever import Retriever

def main():
    print("--- Testing Real FAISS Index Integration ---")
    
    index_name = "vector_store.faiss"
    metadata_name = "metadata.pkl"
        
    retriever = Retriever(index_filename=index_name, metadata_filename=metadata_name)
    
    queries = [
        "ModuleNotFoundError requests",
        "npm install failure",
        "actions/cache",
        "asyncio",
        "json"
    ]
    
    for query in queries:
        print("===================================================")
        print(f"Query: {query}")
        
        results = retriever.retrieve(query, top_k=3)
        print(f"Number of retrieved chunks: {len(results)}\n")
        
        for res in results:
            print(f"Score: {res.score:.4f}")
            print(f"Source: {res.chunk.source}")
            print(f"Title: {res.chunk.title}")
            print(f"URL: {res.chunk.url}")
            
            content = res.chunk.content
            preview = content[:200] + "..." if len(content) > 200 else content
            # Replace newlines with spaces for a cleaner preview
            preview = preview.replace("\n", " ").strip()
            print(f"Preview: {preview}")
            print("------------------------")
            
        print("===================================================\n")

if __name__ == "__main__":
    main()
