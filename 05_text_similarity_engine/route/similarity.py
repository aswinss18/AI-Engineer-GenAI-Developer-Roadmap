from fastapi import APIRouter
from pydantic import BaseModel
from core.embedding_similarity import compare_texts

router = APIRouter()

class SimilarityRequest(BaseModel):
    text1: str
    text2: str

class SimilarityResponse(BaseModel):
    similarity_score: float
    text1: str
    text2: str

@router.post("/similarity", response_model=SimilarityResponse)
async def calculate_similarity(request: SimilarityRequest):
    """
    Calculate cosine similarity between two texts using embeddings
    """
    similarity_score = compare_texts(request.text1, request.text2)
    
    return SimilarityResponse(
        similarity_score=similarity_score,
        text1=request.text1,
        text2=request.text2
    )