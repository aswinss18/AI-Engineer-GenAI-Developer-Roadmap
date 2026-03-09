import faiss
import numpy as np
import logging
from .persistence_manager import PersistenceManager

logger = logging.getLogger(__name__)

dimension = 1536

index = faiss.IndexFlatL2(dimension)

documents = []
embeddings_store = []

# Initialize persistence manager
persistence_manager = PersistenceManager()


def clear_documents():
    """Clear all documents and reset the index"""
    global documents, index
    documents.clear()
    embeddings_store.clear()
    # Reset the index
    index = faiss.IndexFlatL2(dimension)
    
    # Clear persisted state (Requirements 8.2, 8.3)
    try:
        persistence_manager.clear_persisted_state()
        logger.info("Cleared persisted state along with in-memory documents")
    except Exception as e:
        logger.error(f"Failed to clear persisted state: {e}")
        # Continue operation even if persistence clearing fails


def add_embeddings(chunks, embeddings):
    global documents

    vectors = np.array(embeddings).astype("float32")

    index.add(vectors)

    documents.extend(chunks)
    
    # Trigger incremental save after adding embeddings (Requirements 5.1, 5.2)
    try:
        persistence_manager.save_complete_state(index, documents)
        logger.info(f"Saved state after adding {len(chunks)} chunks, total documents: {len(documents)}")
    except Exception as e:
        logger.error(f"Failed to save state after adding embeddings: {e}")
        # Continue operation even if persistence fails


def search(query_embedding, k=10):
    """
    Enhanced search with distance scores for reranking
    Returns top-k results with similarity scores
    """
    if len(documents) == 0:
        return []
    
    vector = np.array([query_embedding]).astype("float32")
    distances, indices = index.search(vector, k)
    
    results = []
    for i, distance in zip(indices[0], distances[0]):
        if i < len(documents):  # Safety check
            # Convert L2 distance to similarity score (lower distance = higher similarity)
            similarity_score = 1.0 / (1.0 + distance)
            results.append({
                "text": documents[i]["text"],
                "page": documents[i]["page"],
                "doc": documents[i]["doc"],
                "chunk_index": documents[i].get("chunk_index", i),
                "similarity_score": similarity_score,
                "distance": float(distance)
            })
    
    return results

def load_persisted_state():
    """Load persisted state on startup (Requirements 4.1, 4.2, 4.3, 4.4)"""
    global index, documents
    
    try:
        loaded_index, loaded_chunks, metadata = persistence_manager.load_complete_state(dimension)
        
        # Update global state
        index = loaded_index
        documents.clear()
        documents.extend(loaded_chunks)
        
        # Log startup information
        document_count = metadata.get("document_count", 0)
        total_chunks = len(documents)
        
        if total_chunks > 0:
            logger.info(f"Loaded persisted state: {document_count} documents, {total_chunks} chunks")
        else:
            logger.info("No persisted state found, starting with empty state")
            
        return True
        
    except Exception as e:
        logger.error(f"Failed to load persisted state: {e}")
        # Initialize with empty state on failure
        index = faiss.IndexFlatL2(dimension)
        documents.clear()
        return False


def get_persistence_status():
    """Get persistence status information"""
    return persistence_manager.get_persistence_status()