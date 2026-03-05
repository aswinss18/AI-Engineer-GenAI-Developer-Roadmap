import faiss
import numpy as np

dimension = 1536

index = faiss.IndexFlatL2(dimension)

documents = []
embeddings_store = []


def add_embeddings(chunks, embeddings):

    global documents

    vectors = np.array(embeddings).astype("float32")

    index.add(vectors)

    documents.extend(chunks)


def search(query_embedding, k=3):

    vector = np.array([query_embedding]).astype("float32")

    distances, indices = index.search(vector, k)

    results = []

    for i in indices[0]:
        results.append(documents[i])

    return results