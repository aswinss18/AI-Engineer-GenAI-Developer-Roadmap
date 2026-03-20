"""
Vector store DB layer.
Wraps FAISS index + document store with persistence support.
Moved from core/vector_store.py — imports updated to new paths.
"""

import faiss
import numpy as np
import logging
from app.db.persistence_manager import PersistenceManager
from app.services.internals.keyword_search import keyword_search, build_keyword_index

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

    # Clear persisted state
    try:
        persistence_manager.clear_persisted_state()
        logger.info("Cleared persisted state along with in-memory documents")
    except Exception as e:
        logger.error(f"Failed to clear persisted state: {e}")


def add_embeddings(chunks, embeddings):
    global documents

    vectors = np.array(embeddings).astype("float32")
    index.add(vectors)
    documents.extend(chunks)

    # Build keyword search index after adding documents
    try:
        build_keyword_index(documents)
        logger.info(f"Built keyword index for {len(documents)} total documents")
    except Exception as e:
        logger.error(f"Failed to build keyword index: {e}")

    # Trigger incremental save after adding embeddings
    try:
        persistence_manager.save_complete_state(index, documents)
        logger.info(
            f"Saved state after adding {len(chunks)} chunks, total documents: {len(documents)}"
        )
    except Exception as e:
        logger.error(f"Failed to save state after adding embeddings: {e}")


def search(query_embedding, k=10):
    """
    Enhanced search with distance scores for reranking.
    Returns top-k results with similarity scores.
    """
    if len(documents) == 0:
        return []

    vector = np.array([query_embedding]).astype("float32")
    distances, indices = index.search(vector, k)

    results = []
    for i, distance in zip(indices[0], distances[0]):
        if i < len(documents):
            similarity_score = 1.0 / (1.0 + float(distance))
            results.append(
                {
                    "text": documents[i]["text"],
                    "page": documents[i]["page"],
                    "doc": documents[i]["doc"],
                    "chunk_index": documents[i].get("chunk_index", i),
                    "similarity_score": similarity_score,
                    "distance": float(distance),
                }
            )

    return results


def load_persisted_state():
    """Load persisted state on startup."""
    global index, documents

    try:
        loaded_index, loaded_chunks, metadata = persistence_manager.load_complete_state(
            dimension
        )

        index = loaded_index
        documents.clear()
        documents.extend(loaded_chunks)

        if documents:
            try:
                build_keyword_index(documents)
                logger.info(f"Rebuilt keyword index for {len(documents)} documents")
            except Exception as e:
                logger.error(f"Failed to rebuild keyword index: {e}")

        total_chunks = len(documents)
        if total_chunks > 0:
            logger.info(
                f"Loaded persisted state: {metadata.get('document_count', 0)} documents, {total_chunks} chunks"
            )
        else:
            logger.info("No persisted state found, starting with empty state")

        return True

    except Exception as e:
        logger.error(f"Failed to load persisted state: {e}")
        index = faiss.IndexFlatL2(dimension)
        documents.clear()
        return False


def get_persistence_status():
    """Get persistence status information."""
    return persistence_manager.get_persistence_status()
