from fastapi import APIRouter
from core.rag import rag_pipeline

router = APIRouter()


@router.post("/rag")
async def rag(query: str):
    result = rag_pipeline(query)
    return result