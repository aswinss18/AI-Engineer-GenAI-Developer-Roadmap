"""
FastAPI application factory.
All app config, middleware, and route registration lives here.
Import `create_app()` from this module to build the application.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import logging

from app.core.config import settings
from app.core.logging import setup_logging
from app.api.routes import documents, rag, agent, memory
from app.db.vector_store import load_persisted_state


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    setup_logging()
    logger = logging.getLogger(__name__)

    app = FastAPI(
        title="PDF RAG Assistant",
        description="Production-ready PDF Retrieval-Augmented Generation API with multi-document support, hybrid search, ReAct agent, and persistent memory.",
        version="2.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
    )

    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Register all routers
    app.include_router(documents.router, tags=["Documents"])
    app.include_router(rag.router, tags=["RAG"])
    app.include_router(agent.router, tags=["Agent"])
    app.include_router(memory.router, tags=["Memory"])

    @app.on_event("startup")
    async def startup_event():
        logger.info("Starting PDF RAG Assistant...")
        try:
            result = load_persisted_state()
            if result:
                logger.info("Persisted state loaded successfully")
            else:
                logger.info("No persisted state found — starting fresh")
        except Exception as e:
            logger.warning(f"Could not load persisted state: {e}")

    @app.get("/health", tags=["Health"])
    async def health():
        """Health check endpoint."""
        return {"status": "ok", "version": "2.0.0"}

    logger.info("PDF RAG Assistant app created")
    return app
