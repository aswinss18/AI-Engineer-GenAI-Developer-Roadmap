from fastapi import FastAPI
from app.core.embeddings import get_embedding
from app.core.similarity import cosine_similarity
from app.core.data import documents

app = FastAPI()

# Precompute document embeddings
doc_embeddings = [get_embedding(doc) for doc in documents]


@app.post("/search")
def semantic_search(query: str):

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