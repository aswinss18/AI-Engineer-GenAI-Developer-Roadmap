"""
Document tools for the agent — search and listing.
Moved from core/tools.py. Imports updated to app package paths.
"""

import logging
from typing import Dict, Any
from app.services.internals.rag_pipeline import ask_question as rag_search
from app.db.vector_store import documents
from app.services.internals.multi_document_context import (
    group_chunks_by_document,
    analyze_document_distribution,
)

logger = logging.getLogger(__name__)


def search_documents(query: str) -> Dict[str, Any]:
    """Search through uploaded PDF documents using hybrid RAG pipeline."""
    try:
        if not documents:
            return {
                "success": False,
                "error": "No documents are currently loaded. Please upload PDF documents first.",
                "answer": None,
                "document_count": 0,
            }
        answer = rag_search(query)
        unique_docs = set(chunk.get("doc", "unknown") for chunk in documents)
        return {
            "success": True,
            "answer": answer,
            "document_count": len(unique_docs),
            "total_chunks": len(documents),
            "documents": list(unique_docs),
            "query": query,
        }
    except Exception as e:
        logger.error(f"Error in document search: {e}")
        return {
            "success": False,
            "error": f"Document search failed: {str(e)}",
            "answer": None,
            "document_count": len(set(chunk.get("doc", "unknown") for chunk in documents)) if documents else 0,
        }


def list_available_documents() -> Dict[str, Any]:
    """List all currently loaded documents with their statistics."""
    try:
        if not documents:
            return {
                "success": True,
                "message": "No documents are currently loaded.",
                "documents": {},
                "total_documents": 0,
                "total_chunks": 0,
            }
        doc_info = {}
        for chunk in documents:
            doc_name = chunk.get("doc", "unknown")
            if doc_name not in doc_info:
                doc_info[doc_name] = {"chunk_count": 0, "pages": set()}
            doc_info[doc_name]["chunk_count"] += 1
            doc_info[doc_name]["pages"].add(chunk.get("page", 0))
        for doc_name in doc_info:
            pages = sorted(list(doc_info[doc_name]["pages"]))
            doc_info[doc_name]["pages"] = pages
            doc_info[doc_name]["page_range"] = f"{min(pages)}-{max(pages)}" if pages else "unknown"
            doc_info[doc_name]["total_pages"] = len(pages)
        return {
            "success": True,
            "documents": doc_info,
            "total_documents": len(doc_info),
            "total_chunks": len(documents),
            "message": f"Found {len(doc_info)} documents with {len(documents)} total chunks.",
        }
    except Exception as e:
        logger.error(f"Error listing documents: {e}")
        return {
            "success": False,
            "error": f"Failed to list documents: {str(e)}",
            "documents": {},
            "total_documents": 0,
            "total_chunks": 0,
        }
