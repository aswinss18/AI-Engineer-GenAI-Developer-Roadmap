import faiss
import numpy as np
from embeddings import get_embedding, normalize

def search_query(query: str, mode: str = "default") -> str:
    # 1. Your Database of documents
    documents = [
        "I love programming in Python",
        "Dogs are wonderful pets",
        "Artificial intelligence is the future",
        "FastAPI is great for building APIs"
    ]

    # 2. Convert documents to normalized embeddings
    embeddings = []
    for doc in documents:
        # Normalizing before IndexFlatIP makes it behave like Cosine Similarity
        emb = normalize(get_embedding(doc))
        embeddings.append(emb)

    # Convert to float32 (FAISS requirement)
    embeddings = np.array(embeddings).astype("float32")
    dimension = embeddings.shape[1]

    # 3. Create the FAISS Index
    # IndexFlatIP calculates the Inner Product
    index = faiss.IndexFlatIP(dimension) 
    index.add(embeddings)

    # 4. Process the User Query
    query_vector = normalize(get_embedding(query)).astype("float32")
    # Reshape to (1, dimension) because FAISS expects a batch
    query_vector = query_vector.reshape(1, -1)

    # 5. Search for the Top 1 closest match (k=1)
    distances, indices = index.search(query_vector, k=1)

    # Return the text of the best match
    best_match_idx = indices[0][0]
    return documents[best_match_idx]

# Example usage:
# print(search_query("Tell me about coding"))