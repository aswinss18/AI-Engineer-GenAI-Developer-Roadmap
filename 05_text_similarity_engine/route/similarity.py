from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from core.embedding_similarity import compare_texts
import openai

router = APIRouter()

class SimilarityRequest(BaseModel):
    text1: str
    text2: str

class SimilarityResponse(BaseModel):
    similarity_score: float
    text1: str
    text2: str

class ErrorResponse(BaseModel):
    error: str
    message: str

@router.post("/similarity", response_model=SimilarityResponse)
async def calculate_similarity(request: SimilarityRequest):
    """
    Calculate cosine similarity between two texts using embeddings
    """
    try:
        similarity_score = compare_texts(request.text1, request.text2)
        
        return SimilarityResponse(
            similarity_score=similarity_score,
            text1=request.text1,
            text2=request.text2
        )
    except openai.AuthenticationError:
        raise HTTPException(
            status_code=401,
            detail="OpenAI API key is invalid or not set. Please check your .env file and ensure OPENAI_API_KEY is set correctly."
        )
    except openai.RateLimitError:
        raise HTTPException(
            status_code=429,
            detail="OpenAI API rate limit exceeded. Please try again later."
        )
    except openai.APIError as e:
        raise HTTPException(
            status_code=500,
            detail=f"OpenAI API error: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"An unexpected error occurred: {str(e)}"
        )