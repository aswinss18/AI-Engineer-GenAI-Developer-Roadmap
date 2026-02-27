from fastapi import APIRouter
from app.controller.search import search_query

router = APIRouter()

@router.post("/search")
async def search(query: str):
    results = search_query(query)
    return {
        "query": query,
        "results": results
    }