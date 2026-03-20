"""
RAG service facade.
Single entry point for all RAG-related operations.
Routes call this; internals live in services/internals/.
"""

import logging
from app.services.internals.rag_pipeline import (
    process_pdf,
    ask_question,
    ask_question_stream,
    ask_question_stream_with_sources,
)

logger = logging.getLogger(__name__)


def process_document(file_path: str) -> None:
    """Process a PDF and store its embeddings."""
    logger.info(f"RAG service: processing document {file_path}")
    process_pdf(file_path)


def query(question: str) -> str:
    """Run a synchronous RAG query and return the answer string."""
    logger.info(f"RAG service: querying — {question[:60]}")
    return ask_question(question)


async def query_stream_async(question: str):
    """Async streaming RAG query (yields text chunks)."""
    async for chunk in ask_question_stream(question):
        yield chunk


def query_stream_with_sources(question: str):
    """Streaming RAG query with source metadata (yields dicts)."""
    return ask_question_stream_with_sources(question)
