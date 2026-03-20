"""
Memory management routes.
"""

import logging
from fastapi import APIRouter, HTTPException
from app.services import memory_service

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/memory/stats", summary="Memory statistics")
async def memory_stats():
    """Get current memory system statistics."""
    try:
        return {"success": True, **memory_service.get_stats()}
    except Exception as e:
        logger.error(f"/memory/stats failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/memory/info", summary="Detailed memory info")
async def memory_info():
    """Get detailed memory info including recent samples."""
    try:
        return {"success": True, **memory_service.detailed_info()}
    except Exception as e:
        logger.error(f"/memory/info failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/memory/chat", summary="Clear chat history")
async def clear_chat():
    """Clear the short-term chat history."""
    try:
        memory_service.clear_chat()
        return {"success": True, "message": "Chat history cleared"}
    except Exception as e:
        logger.error(f"/memory/chat DELETE failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/memory/all", summary="Clear all memory")
async def clear_all_memory():
    """Clear all memory (long-term + chat history)."""
    try:
        memory_service.clear_all()
        return {"success": True, "message": "All memory cleared"}
    except Exception as e:
        logger.error(f"/memory/all DELETE failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/memory/cleanup", summary="Cleanup old memories")
async def cleanup_memory(days: int = 30):
    """Remove memories older than `days` and apply decay."""
    try:
        result = memory_service.cleanup(days)
        return {"success": True, **result}
    except Exception as e:
        logger.error(f"/memory/cleanup failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
