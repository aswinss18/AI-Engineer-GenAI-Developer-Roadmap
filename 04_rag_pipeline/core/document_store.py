import faiss
import numpy as np
from app.core.embeddings import get_embedding, normalize
from app.core.chunker import chunk_text

index = None
chunks_store = []


def initialize_document(text: str):
    """
    Initialize document store with chunked text and FAISS index.
    
    Args:
        text: Document text to index
    """
    global index, chunks_store
    
    chunks_store = []
    chunks = chunk_text(text)
    
    embeddings = []
    
    for i, chunk in enumerate(chunks):
        emb = normalize(get_embedding(chunk))
        embeddings.append(emb)
        
        chunks_store.append({
            "id": i,
            "text": chunk
        })
    
    embeddings = np.array(embeddings).astype("float32")
    
    dimension = embeddings.shape[1]
    index = faiss.IndexFlatIP(dimension)
    index.add(embeddings)
    
    print(f"Indexed chunks: {len(chunks)}")


def search_chunks(query: str, k: int = 3):
    """
    Search for relevant chunks using semantic similarity.
    
    Args:
        query: Search query
        k: Number of top results to return
    
    Returns:
        List of matching chunks with scores
    """
    global index
    
    if index is None:
        return []
    
    query_vector = normalize(get_embedding(query))
    query_vector = np.array([query_vector]).astype("float32")
    
    scores, indices = index.search(query_vector, k)
    
    results = []
    
    for i, idx in enumerate(indices[0]):
        results.append({
            "chunk": chunks_store[idx]["text"],
            "score": round(float(scores[0][i]), 4)
        })
    
    return results
