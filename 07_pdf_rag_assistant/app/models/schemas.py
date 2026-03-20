"""
Pydantic schemas for all API request and response bodies.
Provides a standardised response shape across every endpoint.
"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Standard wrapper
# ---------------------------------------------------------------------------

class StandardResponse(BaseModel):
    """Base response shape used by all endpoints."""
    success: bool = True
    error: Optional[str] = None


# ---------------------------------------------------------------------------
# Request bodies
# ---------------------------------------------------------------------------

class AskRequest(BaseModel):
    query: str = Field(..., description="The question to ask the RAG pipeline")


class AgentRequest(BaseModel):
    query: str = Field(..., description="The query for the ReAct agent")
    conversation_history: Optional[List[Dict[str, str]]] = Field(
        default=None, description="Optional prior conversation messages"
    )


# ---------------------------------------------------------------------------
# Upload
# ---------------------------------------------------------------------------

class UploadResponse(StandardResponse):
    filename: str
    chunks_created: int = 0
    documents_loaded: int = 0


# ---------------------------------------------------------------------------
# Ask / RAG
# ---------------------------------------------------------------------------

class SourceItem(BaseModel):
    doc: str
    page: int
    text: str
    hybrid_score: Optional[float] = None
    cosine_similarity: Optional[float] = None

class AskResponse(StandardResponse):
    query: str
    answer: str
    sources: List[SourceItem] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)

# Alias used in rag routes
RagResponse = AskResponse


# ---------------------------------------------------------------------------
# Agent
# ---------------------------------------------------------------------------

class ToolCallItem(BaseModel):
    tool_name: str
    arguments: Dict[str, Any] = Field(default_factory=dict)
    result: Dict[str, Any] = Field(default_factory=dict)

class AgentResponse(StandardResponse):
    query: str
    answer: str
    tools_used: int = 0
    tool_calls: List[ToolCallItem] = Field(default_factory=list)
    has_tool_calls: bool = False
    react_pattern: bool = True
    memory_used: bool = False
    memory_context_info: Optional[Dict[str, Any]] = None
    reasoning_steps: List[Dict[str, Any]] = Field(default_factory=list)
    optimization_applied: bool = True
    prompt_architecture: str = "modular_optimized"


# ---------------------------------------------------------------------------
# Status / Documents
# ---------------------------------------------------------------------------

class StatusResponse(StandardResponse):
    documents_loaded: int
    unique_documents: int
    document_names: List[str]
    cached_files: int
    status: str
    multi_document_mode: bool

class DocumentInfo(BaseModel):
    chunk_count: int
    pages: List[int]
    page_range: str
    total_pages: Optional[int] = None

class DocumentListResponse(StandardResponse):
    total_documents: int
    total_chunks: int
    documents: Dict[str, Any] = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# Memory
# ---------------------------------------------------------------------------

class MemoryStatsResponse(StandardResponse):
    memory_stats: Dict[str, Any] = Field(default_factory=dict)

class MemoryActionResponse(StandardResponse):
    message: str

class MemoryCleanupResponse(StandardResponse):
    cleanup_result: Dict[str, Any] = Field(default_factory=dict)
    message: str

class MemoryDecayResponse(StandardResponse):
    decay_result: Dict[str, Any] = Field(default_factory=dict)
    message: str

class MemoryDetailedResponse(StandardResponse):
    memory_stats: Dict[str, Any] = Field(default_factory=dict)
    recent_memories: List[Dict[str, Any]] = Field(default_factory=list)
    system_health: Dict[str, Any] = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# Persistence
# ---------------------------------------------------------------------------

class PersistenceStatusResponse(StandardResponse):
    loaded_document_count: int
    validation_status: str
