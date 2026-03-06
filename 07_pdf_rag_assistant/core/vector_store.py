import faiss
import numpy as np

dimension = 1536

index = faiss.IndexFlatL2(dimension)

documents = []
embeddings_store = []


def clear_documents():
    """Clear all documents and reset the index"""
    global documents, index
    documents.clear()
    embeddings_store.clear()
    # Reset the index
    index = faiss.IndexFlatL2(dimension)


def add_embeddings(chunks, embeddings):
    global documents

    vectors = np.array(embeddings).astype("float32")

    index.add(vectors)

    documents.extend(chunks)


def search(query_embedding, k=3):
    if len(documents) == 0:
        return []
    
    vector = np.array([query_embedding]).astype("float32")
    distances, indices = index.search(vector, k)
    
    results = []
    for i in indices[0]:
        if i < len(documents):  # Safety check
            results.append(documents[i])
    
    return results