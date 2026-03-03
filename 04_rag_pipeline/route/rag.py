from fastapi import APIRouter
from pydantic import BaseModel
from core.rag import rag_pipeline

router = APIRouter()


class QueryRequest(BaseModel):
    query: str


@router.post("/rag")
async def rag(request: QueryRequest):
    result = rag_pipeline(request.query)
    return result