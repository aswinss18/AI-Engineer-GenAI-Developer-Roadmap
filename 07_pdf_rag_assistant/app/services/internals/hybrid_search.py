"""
Hybrid search combining vector similarity and keyword matching.
Moved from core/hybrid_search.py — imports updated.
"""

import logging
from typing import List, Dict, Any
from app.db.vector_store import search as vector_search
from app.services.internals.keyword_search import keyword_search
from app.services.internals.embeddings import get_embedding

logger = logging.getLogger(__name__)


def hybrid_search(
    query: str,
    vector_k: int = 10,
    keyword_k: int = 10,
    vector_weight: float = 0.6,
    keyword_weight: float = 0.4,
) -> List[Dict[str, Any]]:
    """Perform hybrid search combining vector similarity and keyword matching."""
    logger.info(f"Performing hybrid search: vector_k={vector_k}, keyword_k={keyword_k}")

    query_embedding = get_embedding(query)

    vector_results = vector_search(query_embedding, k=vector_k)
    logger.info(f"Vector search returned {len(vector_results)} results")

    keyword_results = keyword_search(query, k=keyword_k)
    logger.info(f"Keyword search returned {len(keyword_results)} results")

    combined_results = {}

    if vector_results:
        max_vector_score = max(r.get("similarity_score", 0) for r in vector_results)
        min_vector_score = min(r.get("similarity_score", 0) for r in vector_results)
        vector_range = max_vector_score - min_vector_score if max_vector_score > min_vector_score else 1

        for result in vector_results:
            chunk_key = _get_chunk_key(result)
            normalized_vector_score = float(
                (result.get("similarity_score", 0) - min_vector_score) / vector_range
            )
            combined_results[chunk_key] = {
                **result,
                "vector_score": float(result.get("similarity_score", 0)),
                "normalized_vector_score": normalized_vector_score,
                "keyword_score": 0.0,
                "normalized_keyword_score": 0.0,
                "search_types": ["vector"],
            }

    if keyword_results:
        max_keyword_score = max(r.get("keyword_score", 0) for r in keyword_results)
        min_keyword_score = min(r.get("keyword_score", 0) for r in keyword_results)
        keyword_range = (
            max_keyword_score - min_keyword_score
            if max_keyword_score > min_keyword_score
            else 1
        )

        for result in keyword_results:
            chunk_key = _get_chunk_key(result)
            normalized_keyword_score = float(
                (result.get("keyword_score", 0) - min_keyword_score) / keyword_range
            )
            if chunk_key in combined_results:
                combined_results[chunk_key].update(
                    {
                        "keyword_score": float(result.get("keyword_score", 0)),
                        "normalized_keyword_score": normalized_keyword_score,
                        "matched_terms": result.get("matched_terms", []),
                    }
                )
                combined_results[chunk_key]["search_types"].append("keyword")
            else:
                combined_results[chunk_key] = {
                    **result,
                    "vector_score": 0.0,
                    "normalized_vector_score": 0.0,
                    "keyword_score": float(result.get("keyword_score", 0)),
                    "normalized_keyword_score": normalized_keyword_score,
                    "search_types": ["keyword"],
                }

    final_results = []
    for chunk_key, result in combined_results.items():
        hybrid_score = (
            vector_weight * result["normalized_vector_score"]
            + keyword_weight * result["normalized_keyword_score"]
        )
        if len(result["search_types"]) > 1:
            hybrid_score *= 1.2

        result.update(
            {
                "hybrid_score": float(hybrid_score),
                "search_method": "hybrid",
                "vector_weight": float(vector_weight),
                "keyword_weight": float(keyword_weight),
            }
        )
        final_results.append(result)

    final_results.sort(key=lambda x: x["hybrid_score"], reverse=True)

    logger.info(f"Hybrid search combined {len(final_results)} unique results")
    return final_results


def _get_chunk_key(chunk: Dict[str, Any]) -> str:
    if "chunk_index" in chunk:
        return f"chunk_{chunk['chunk_index']}"
    text_snippet = chunk.get("text", "")[:50]
    return f"text_{hash(text_snippet)}"


def get_hybrid_search_stats(results: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Get statistics about hybrid search results."""
    if not results:
        return {"total": 0}

    vector_only = sum(1 for r in results if r.get("search_types") == ["vector"])
    keyword_only = sum(1 for r in results if r.get("search_types") == ["keyword"])
    both_methods = sum(1 for r in results if len(r.get("search_types", [])) > 1)
    avg_hybrid_score = sum(r.get("hybrid_score", 0) for r in results) / len(results)

    return {
        "total": len(results),
        "vector_only": vector_only,
        "keyword_only": keyword_only,
        "both_methods": both_methods,
        "avg_hybrid_score": float(round(avg_hybrid_score, 3)),
        "top_score": float(round(results[0].get("hybrid_score", 0), 3)) if results else 0.0,
    }
