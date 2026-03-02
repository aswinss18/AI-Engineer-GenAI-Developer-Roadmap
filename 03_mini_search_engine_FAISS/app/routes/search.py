from fastapi import APIRouter
from app.controller.search import search_query
from app.core.document_store import initialize_document, search_chunks

router = APIRouter()

@router.post("/search")
async def search(query: str):
    results = search_query(query)
    return {
        "query": query,
        "results": results
    }


@router.post("/upload")
async def upload(text: str):
    """Upload and index a document for retrieval."""
    initialize_document(text)
    return {"message": "Document indexed successfully"}


@router.post("/retrieve")
async def retrieve(query: str, k: int = 3):
    """Retrieve relevant chunks from indexed document."""
    results = search_chunks(query, k)
    return {"results": results}
