from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from core.embeddings import get_embedding
from core.similarity import cosine_similarity
from core.data import documents

app = FastAPI()

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Precompute document embeddings
doc_embeddings = [get_embedding(doc) for doc in documents]

class SearchRequest(BaseModel):
    query: str

@app.get("/")
def root():
    return {"message": "Semantic Search API", "docs": "/docs"}

@app.post("/search")
def semantic_search(request: SearchRequest):
    query_embedding = get_embedding(request.query)

    scores = []

    for doc, emb in zip(documents, doc_embeddings):
        score = cosine_similarity(query_embedding, emb)
        scores.append({
            "text": doc,
            "score": float(score)
        })

    # Sort by similarity
    scores.sort(key=lambda x: x["score"], reverse=True)

    return {
        "query": request.query,
        "results": scores[:3]
    }

@app.get("/search")
def semantic_search_get(query: str = Query(..., description="Search query")):
    query_embedding = get_embedding(query)

    scores = []

    for doc, emb in zip(documents, doc_embeddings):
        score = cosine_similarity(query_embedding, emb)
        scores.append({
            "text": doc,
            "score": float(score)
        })

    # Sort by similarity
    scores.sort(key=lambda x: x["score"], reverse=True)

    return {
        "query": query,
        "results": scores[:3]
    }