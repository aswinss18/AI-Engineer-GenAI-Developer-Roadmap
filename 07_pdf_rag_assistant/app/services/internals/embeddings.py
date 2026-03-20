"""
Embeddings utility.
Moved from core/embeddings.py — updated to use centralised config.
"""

from openai import OpenAI
from app.core.config import settings

_client = None


def _get_client() -> OpenAI:
    global _client
    if _client is None:
        _client = OpenAI(api_key=settings.openai_api_key)
    return _client


def get_embedding(text: str) -> list:
    """Generate an embedding vector for the given text."""
    client = _get_client()
    response = client.embeddings.create(
        model="text-embedding-3-small",
        input=text,
    )
    return response.data[0].embedding
