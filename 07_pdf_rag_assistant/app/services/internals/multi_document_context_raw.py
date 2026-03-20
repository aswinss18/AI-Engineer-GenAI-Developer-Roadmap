"""
Multi-document context builder for cross-document analysis and comparison
"""

import logging
from typing import List, Dict, Any, Tuple
from collections import defaultdict, Counter

logger = logging.getLogger(__name__)

def group_chunks_by_document(results: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
    """
    Group chunks by their source document
    
    Args:
        results: List of chunk dictionaries with document metadata
        
    Returns:
        Dictionary mapping document names to lists of chunks
    """
    grouped = defaultdict(list)
    
    for chunk in results:
        doc_name = chunk.get("doc", "unknown_document")
        grouped[doc_name].append(chunk)
    
    # Sort chunks within each document by page number and chunk index
    for doc_name in grouped:
        grouped[doc_name].sort(key=lambda x: (x.get("page", 0), x.get("chunk_index", 0)))
    
    logger.info(f"Grouped {len(results)} chunks into {len(grouped)} documents")
    for doc_name, chunks in grouped.items():
        logger.info(f"  {doc_name}: {len(chunks)} chunks")
    
    return dict(grouped)

def analyze_document_distribution(grouped_chunks: Dict[str, List[Dict[str, Any]]]) -> Dict[str, Any]:
    """
    Analyze the distribution of chunks across documents
    
    Args:
        grouped_chunks: Dictionary mapping document names to chunk lists
        
    Returns:
        Analysis statistics
    """
    total_chunks = sum(len(chunks) for chunks in grouped_chunks.values())
    doc_count = len(grouped_chunks)
    
    # Calculate document coverage
    doc_stats = {}
    for doc_name, chunks in grouped_chunks.items():
        chunk_count = len(chunks)
        coverage_percentage = (chunk_count / total_chunks) * 100 if total_chunks > 0 else 0
        
        # Get page range
        pages = [chunk.get("page", 0) for chunk in chunks]
        page_range = f"{min(pages)}-{max(pages)}" if pages else "unknown"
        
        # Calculate average scores
        hybrid_scores = [chunk.get("hybrid_score", 0) for chunk in chunks if chunk.get("hybrid_score")]
        avg_score = sum(hybrid_scores) / len(hybrid_scores) if hybrid_scores else 0
        
        doc_stats[doc_name] = {
            "chunk_count": chunk_count,
            "coverage_percentage": float(round(coverage_percentage, 1)),
            "page_range": page_range,
            "avg_hybrid_score": float(round(avg_score, 3)),
            "search_types": list(set(
                search_type 
                for chunk in chunks 
                for search_type in chunk.get("search_types", [])
            ))
        }
    
    return {
        "total_chunks": total_chunks,
        "document_count": doc_count,
        "multi_document": doc_count > 1,
        "document_stats": doc_stats
    }

def build_multi_document_context(grouped_chunks: Dict[str, List[Dict[str, Any]]], 
                               max_context_length: int = 3000) -> Tuple[str, Dict[str, Any]]:
    """
    Build structured context from multiple documents with clear boundaries
    
    Args:
        grouped_chunks: Dictionary mapping document names to chunk lists
        max_context_length: Maximum total context length
        
    Returns:
        Tuple of (formatted_context, context_metadata)
    """
    if not grouped_chunks:
        return "", {"documents": 0, "total_chunks": 0}
    
    context_parts = []
    current_length = 0
    included_docs = {}
    
    # Sort documents by average relevance score (highest first)
    doc_scores = {}
    for doc_name, chunks in grouped_chunks.items():
        scores = [chunk.get("hybrid_score", chunk.get("combined_score", 0)) for chunk in chunks]
        doc_scores[doc_name] = sum(scores) / len(scores) if scores else 0
    
    sorted_docs = sorted(grouped_chunks.items(), key=lambda x: doc_scores[x[0]], reverse=True)
    
    for doc_name, chunks in sorted_docs:
        # Calculate space needed for this document
        doc_header = f"\n=== Document: {doc_name} ===\n"
        doc_content = ""
        
        for i, chunk in enumerate(chunks):
            chunk_text = chunk.get("text", "")
            chunk_header = f"\n[Page {chunk.get('page', '?')}] "
            
            chunk_content = chunk_header + chunk_text
            
            # Check if adding this chunk would exceed limit
            potential_length = current_length + len(doc_header) + len(doc_content) + len(chunk_content)
            
            if potential_length > max_context_length and context_parts:
                # Stop if we would exceed limit and we already have some content
                break
            
            doc_content += chunk_content
        
        if doc_content.strip():  # Only add if we have content
            full_doc_section = doc_header + doc_content
            context_parts.append(full_doc_section)
            current_length += len(full_doc_section)
            
            included_docs[doc_name] = {
                "chunks_included": len([c for c in chunks if c.get("text", "") in doc_content]),
                "total_chunks": len(chunks),
                "pages": list(set(chunk.get("page", 0) for chunk in chunks)),
                "avg_score": float(doc_scores[doc_name])  # Ensure Python float
            }
    
    # Build final context
    context = "".join(context_parts)
    
    # Add summary header if multiple documents
    if len(included_docs) > 1:
        doc_list = ", ".join(included_docs.keys())
        summary_header = f"Multi-Document Analysis ({len(included_docs)} documents: {doc_list})\n"
        context = summary_header + context
    
    metadata = {
        "documents": len(included_docs),
        "total_chunks": sum(doc_info["chunks_included"] for doc_info in included_docs.values()),
        "context_length": len(context),
        "included_documents": included_docs,
        "multi_document_analysis": len(included_docs) > 1
    }
    
    logger.info(f"Built multi-document context: {len(included_docs)} docs, {metadata['total_chunks']} chunks, {len(context)} chars")
    
    return context, metadata

def create_comparison_prompt(context: str, question: str, context_metadata: Dict[str, Any]) -> str:
    """
    Create a specialized prompt for multi-document comparison and analysis
    
    Args:
        context: The multi-document context
        question: User's question
        context_metadata: Metadata about the context
        
    Returns:
        Formatted prompt for multi-document reasoning
    """
    is_multi_doc = context_metadata.get("multi_document_analysis", False)
    doc_count = context_metadata.get("documents", 1)
    
    if is_multi_doc:
        # Multi-document comparison prompt
        prompt = f"""You are an AI research assistant specializing in multi-document analysis and comparison.

TASK: Analyze the provided documents to answer the question. Pay special attention to:
- Comparing viewpoints across different documents
- Identifying agreements and disagreements between sources
- Synthesizing information from multiple perspectives
- Clearly citing which document supports each point

DOCUMENTS PROVIDED: {doc_count} documents with relevant information
{context}

QUESTION: {question}

INSTRUCTIONS:
1. Answer the question using information from the provided documents
2. When multiple documents discuss the same topic, compare their viewpoints
3. Clearly indicate which document each piece of information comes from
4. If documents disagree, present both perspectives fairly
5. Synthesize insights that emerge from combining multiple sources
6. Use format: "According to [Document Name]..." when citing sources

ANSWER:"""
    else:
        # Single document prompt (enhanced)
        doc_name = list(context_metadata.get("included_documents", {}).keys())[0] if context_metadata.get("included_documents") else "the document"
        
        prompt = f"""You are an AI research assistant analyzing document content.

DOCUMENT: {doc_name}
{context}

QUESTION: {question}

INSTRUCTIONS:
1. Answer the question using the information from the provided document
2. Reference specific sections or pages when possible
3. If the document doesn't contain enough information, clearly state this
4. Provide detailed explanations based on the document content

ANSWER:"""
    
    return prompt

def extract_document_insights(grouped_chunks: Dict[str, List[Dict[str, Any]]]) -> Dict[str, Any]:
    """
    Extract insights about document characteristics and relationships
    
    Args:
        grouped_chunks: Dictionary mapping document names to chunk lists
        
    Returns:
        Document insights and relationships
    """
    insights = {
        "document_types": {},
        "common_themes": [],
        "document_relationships": {},
        "coverage_analysis": {}
    }
    
    # Analyze document types based on content patterns
    for doc_name, chunks in grouped_chunks.items():
        all_text = " ".join(chunk.get("text", "") for chunk in chunks).lower()
        
        # Simple document type detection
        doc_type = "general"
        if any(term in all_text for term in ["research", "study", "methodology", "results"]):
            doc_type = "research_paper"
        elif any(term in all_text for term in ["chapter", "section", "introduction"]):
            doc_type = "book"
        elif any(term in all_text for term in ["manual", "guide", "instructions"]):
            doc_type = "manual"
        
        insights["document_types"][doc_name] = doc_type
    
    # Find common themes across documents
    if len(grouped_chunks) > 1:
        # Extract common keywords
        all_keywords = []
        for chunks in grouped_chunks.values():
            for chunk in chunks:
                if chunk.get("matched_terms"):
                    all_keywords.extend(chunk["matched_terms"])
        
        # Find frequently mentioned terms across documents
        keyword_counts = Counter(all_keywords)
        insights["common_themes"] = [term for term, count in keyword_counts.most_common(5) if count > 1]
    
    return insights