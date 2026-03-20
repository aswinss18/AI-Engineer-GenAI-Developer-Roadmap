"""
Advanced reranking and context compression for RAG pipeline.
Moved from core/reranker.py — imports updated.
"""

import numpy as np
import logging
from typing import List, Dict, Any
from app.services.internals.embeddings import get_embedding

logger = logging.getLogger(__name__)


def cosine_similarity(vec1: np.ndarray, vec2: np.ndarray) -> float:
    dot_product = np.dot(vec1, vec2)
    norm_a = np.linalg.norm(vec1)
    norm_b = np.linalg.norm(vec2)
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return float(dot_product / (norm_a * norm_b))


def rerank_chunks(
    query_embedding: List[float],
    chunks: List[Dict[str, Any]],
    top_k: int = 3,
) -> List[Dict[str, Any]]:
    """Rerank chunks using cosine similarity for better precision."""
    if not chunks:
        return []

    logger.info(f"Reranking {len(chunks)} chunks to select top {top_k}")
    query_vec = np.array(query_embedding)
    scored_chunks = []

    for chunk in chunks:
        try:
            chunk_embedding = get_embedding(chunk["text"])
            chunk_vec = np.array(chunk_embedding)
            cosine_score = cosine_similarity(query_vec, chunk_vec)
            original_score = chunk.get("similarity_score", 0.5)
            combined_score = 0.7 * cosine_score + 0.3 * original_score
            chunk_copy = chunk.copy()
            chunk_copy.update(
                {
                    "cosine_similarity": float(cosine_score),
                    "combined_score": float(combined_score),
                    "reranked": True,
                }
            )
            scored_chunks.append((combined_score, chunk_copy))
        except Exception as e:
            logger.error(f"Error reranking chunk: {e}")
            scored_chunks.append((chunk.get("similarity_score", 0.0), chunk))

    scored_chunks.sort(key=lambda x: x[0], reverse=True)
    top_chunks = [chunk for _, chunk in scored_chunks[:top_k]]
    logger.info(
        f"Reranking complete. Top scores: {[chunk.get('combined_score', 0) for chunk in top_chunks[:3]]}"
    )
    return top_chunks


def compress_chunks(
    chunks: List[Dict[str, Any]], max_chunk_length: int = 500
) -> List[Dict[str, Any]]:
    """Compress chunks to reduce token usage."""
    compressed_chunks = []
    for chunk in chunks:
        text = chunk["text"]
        if len(text) <= max_chunk_length:
            compressed_chunks.append(chunk)
        else:
            compressed_text = text[: max_chunk_length - 3] + "..."
            compressed_chunk = chunk.copy()
            compressed_chunk.update(
                {
                    "text": compressed_text,
                    "original_length": len(text),
                    "compressed": True,
                }
            )
            compressed_chunks.append(compressed_chunk)

    total_original = sum(len(chunk["text"]) for chunk in chunks)
    total_compressed = sum(len(chunk["text"]) for chunk in compressed_chunks)
    compression_ratio = (
        (total_original - total_compressed) / total_original if total_original > 0 else 0
    )
    logger.info(
        f"Compression: {total_original} → {total_compressed} chars ({compression_ratio:.1%} reduction)"
    )
    return compressed_chunks


def smart_context_selection(
    chunks: List[Dict[str, Any]], max_context_length: int = 2000
) -> List[Dict[str, Any]]:
    """Intelligently select chunks to fit within context length."""
    selected_chunks = []
    current_length = 0
    sorted_chunks = sorted(
        chunks,
        key=lambda x: x.get("combined_score", x.get("similarity_score", 0)),
        reverse=True,
    )
    for chunk in sorted_chunks:
        chunk_length = len(chunk["text"])
        if current_length + chunk_length <= max_context_length:
            selected_chunks.append(chunk)
            current_length += chunk_length
        else:
            remaining_space = max_context_length - current_length
            if remaining_space > 100:
                truncated_chunk = chunk.copy()
                truncated_chunk["text"] = chunk["text"][: remaining_space - 3] + "..."
                truncated_chunk["truncated_for_context"] = True
                selected_chunks.append(truncated_chunk)
                break

    logger.info(f"Context selection: {len(selected_chunks)} chunks, {current_length} total chars")
    return selected_chunks
