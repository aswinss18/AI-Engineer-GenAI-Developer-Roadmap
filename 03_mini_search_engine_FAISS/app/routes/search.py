from fastapi import APIRouter

from app.controllers.search import search_query
import os

router = APIRouter()


@router.post("/search")
async def search(
    query: str,
    mode: str = "default",
):
    response = search_query(query, mode)
    return {"response": response}