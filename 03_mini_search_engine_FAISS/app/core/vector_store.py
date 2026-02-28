import faiss
import numpy as np
from app.core.embeddings import get_embedding, normalize

documents = [
    "I love programming in Python",
    "Dogs are wonderful pets",
    "Artificial intelligence is the future",
    "FastAPI is great for building APIs"
]

index = None

def initialize_faiss():
    global index

    embeddings = []

    for doc in documents:
        emb = normalize(get_embedding(doc))
        embeddings.append(emb)

    embeddings = np.array(embeddings).astype("float32")

    dimension = embeddings.shape[1]

    index = faiss.IndexFlatIP(dimension)
    index.add(embeddings)

    print("✅ FAISS index initialized")


def search_faiss(query: str, k: int = 3):
    global index

    query_vector = normalize(get_embedding(query))
    query_vector = np.array([query_vector]).astype("float32")

    scores, indices = index.search(query_vector, k)

    results = []

    for i, idx in enumerate(indices[0]):
        results.append({
            "text": documents[idx],
            "score": float(scores[0][i])
        })

    return results