"""
Agent routes — ReAct pattern with tool calling.
"""

import json
import logging
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from app.models.schemas import AgentRequest, AgentResponse
from app.services.agent_service import run, run_stream

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/agent", response_model=AgentResponse, summary="ReAct agent query")
async def agent(request: AgentRequest):
    """Run the ReAct agent on a query. The agent can call tools like document search."""
    try:
        result = run(request.query, request.conversation_history)
        return AgentResponse(
            success=result.get("success", False),
            query=request.query,
            answer=result.get("answer", ""),
            tools_used=result.get("tools_used", 0),
            tool_calls=result.get("tool_calls", []),
            reasoning_steps=result.get("reasoning_steps", []),
            memory_used=result.get("memory_used", False),
        )
    except Exception as e:
        logger.error(f"/agent failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/agent-stream", summary="Streaming ReAct agent query")
async def agent_stream(request: AgentRequest):
    """Stream the ReAct agent response (Server-Sent Events)."""
    def generate():
        try:
            for chunk in run_stream(request.query, request.conversation_history):
                yield f"data: {json.dumps(chunk)}\n\n"
        except Exception as e:
            logger.error(f"/agent-stream failed: {e}")
            yield f"data: {json.dumps({'type': 'error', 'error': str(e)})}\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")
