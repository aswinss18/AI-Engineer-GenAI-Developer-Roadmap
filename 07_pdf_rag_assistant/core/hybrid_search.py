"""
Hybrid search combining vector similarity and keyword matching
"""

import logging
from typing import List, Dict, Any
from .vector_store import search as vector_search
from .keyword_search import keyword_search
from .embeddings import get_embedding

logger = logging.getLogger(__name__)

def hybrid_search(query: str, vector_k: int = 10, keyword_k: int = 10, 
                 vector_weight: float = 0.6, keyword_weight: float = 0.4) -> List[Dict[str, Any]]:
    """
    Perform hybrid search combining vector similarity and keyword matching
    
    Args:
        query: Search query string
        vector_k: Number of results from vector search
        keyword_k: Number of results from keyword search
        vector_weight: Weight for vector search scores (0-1)
        keyword_weight: Weight for keyword search scores (0-1)
        
    Returns:
        Combined and deduplicated results with hybrid scores
    """
    logger.info(f"Performing hybrid search: vector_k={vector_k}, keyword_k={keyword_k}")
    
    # Get query embedding for vector search
    query_embedding = get_embedding(query)
    
    # Perform vector search
    vector_results = vector_search(query_embedding, k=vector_k)
    logger.info(f"Vector search returned {len(vector_results)} results")
    
    # Perform keyword search
    keyword_results = keyword_search(query, k=keyword_k)
    logger.info(f"Keyword search returned {len(keyword_results)} results")
    
    # Normalize scores and combine results
    combined_results = {}
    
    # Process vector results
    if vector_results:
        # Normalize vector similarity scores (0-1 range)
        max_vector_score = max(r.get("similarity_score", 0) for r in vector_results)
        min_vector_score = min(r.get("similarity_score", 0) for r in vector_results)
        vector_range = max_vector_score - min_vector_score if max_vector_score > min_vector_score else 1
        
        for result in vector_results:
            chunk_key = _get_chunk_key(result)
            normalized_vector_score = (result.get("similarity_score", 0) - min_vector_score) / vector_range
            
            combined_results[chunk_key] = {
                **result,
                "vector_score": result.get("similarity_score", 0),
                "normalized_vector_score": normalized_vector_score,
                "keyword_score": 0.0,
                "normalized_keyword_score": 0.0,
                "search_types": ["vector"]
            }
    
    # Process keyword results
    if keyword_results:
        # Normalize keyword TF-IDF scores (0-1 range)
        max_keyword_score = max(r.get("keyword_score", 0) for r in keyword_results)
        min_keyword_score = min(r.get("keyword_score", 0) for r in keyword_results)
        keyword_range = max_keyword_score - min_keyword_score if max_keyword_score > min_keyword_score else 1
        
        for result in keyword_results:
            chunk_key = _get_chunk_key(result)
            normalized_keyword_score = (result.get("keyword_score", 0) - min_keyword_score) / keyword_range
            
            if chunk_key in combined_results:
                # Update existing result with keyword data
                combined_results[chunk_key].update({
                    "keyword_score": result.get("keyword_score", 0),
                    "normalized_keyword_score": normalized_keyword_score,
                    "matched_terms": result.get("matched_terms", [])
                })
                combined_results[chunk_key]["search_types"].append("keyword")
            else:
                # Add new keyword-only result
                combined_results[chunk_key] = {
                    **result,
                    "vector_score": 0.0,
                    "normalized_vector_score": 0.0,
                    "keyword_score": result.get("keyword_score", 0),
                    "normalized_keyword_score": normalized_keyword_score,
                    "search_types": ["keyword"]
                }
    
    # Calculate hybrid scores
    final_results = []
    for chunk_key, result in combined_results.items():
        # Calculate weighted hybrid score
        hybrid_score = (
            vector_weight * result["normalized_vector_score"] + 
            keyword_weight * result["normalized_keyword_score"]
        )
        
        # Boost score if found by both methods
        if len(result["search_types"]) > 1:
            hybrid_score *= 1.2  # 20% boost for multi-method matches
        
        result.update({
            "hybrid_score": hybrid_score,
            "search_method": "hybrid",
            "vector_weight": vector_weight,
            "keyword_weight": keyword_weight
        })
        
        final_results.append(result)
    
    # Sort by hybrid score
    final_results.sort(key=lambda x: x["hybrid_score"], reverse=True)
    
    logger.info(f"Hybrid search combined {len(final_results)} unique results")
    logger.info(f"Multi-method matches: {sum(1 for r in final_results if len(r['search_types']) > 1)}")
    
    return final_results

def _get_chunk_key(chunk: Dict[str, Any]) -> str:
    """Generate unique key for chunk deduplication"""
    # Use chunk index if available, otherwise use text hash
    if "chunk_index" in chunk:
        return f"chunk_{chunk['chunk_index']}"
    else:
        # Fallback to text-based key
        text_snippet = chunk.get("text", "")[:50]
        return f"text_{hash(text_snippet)}"

def get_hybrid_search_stats(results: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Get statistics about hybrid search results"""
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
        "avg_hybrid_score": round(avg_hybrid_score, 3),
        "top_score": round(results[0].get("hybrid_score", 0), 3) if results else 0
    }