"""
RAG /ask routes (non-streaming and streaming).
"""

import json
import logging
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from app.models.schemas import AskRequest, RagResponse
from app.services.rag_service import query as rag_query, query_stream_with_sources

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/ask", response_model=RagResponse, summary="RAG question answering")
async def ask(request: AskRequest):
    """Answer a question using the uploaded PDF documents via hybrid RAG pipeline."""
    try:
        answer = rag_query(request.query)
        return RagResponse(
            success=True,
            query=request.query,
            answer=answer,
        )
    except Exception as e:
        logger.error(f"/ask failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/ask-stream", summary="Streaming RAG answer with sources")
async def ask_stream(request: AskRequest):
    """Stream the RAG answer with source metadata (Server-Sent Events)."""
    def generate():
        try:
            for chunk_data in query_stream_with_sources(request.query):
                yield f"data: {json.dumps(chunk_data)}\n\n"
        except Exception as e:
            logger.error(f"/ask-stream failed: {e}")
            yield f"data: {json.dumps({'error': str(e)})}\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")
