from core.document_store import search_chunks
from core.generate import generate_rag_answer


def rag_pipeline(query: str):
    retrieved = search_chunks(query, k=3)
    
    if not retrieved:
        return {
            "answer": "No document has been uploaded yet. Please upload a document first.",
            "sources": []
        }
    
    answer = generate_rag_answer(query, retrieved)

    return {
        "answer": answer,
        "sources": retrieved
    }