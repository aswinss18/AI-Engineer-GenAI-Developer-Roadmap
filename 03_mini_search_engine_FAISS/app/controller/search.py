from app.core.vector_store import search_faiss

def search_query(query: str):
    return search_faiss(query)