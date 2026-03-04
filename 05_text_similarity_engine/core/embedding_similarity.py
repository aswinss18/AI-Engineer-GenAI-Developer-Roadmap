from openai import OpenAI
import numpy as np

client = OpenAI()

def get_embedding(text):
    response = client.embeddings.create(
        model="text-embedding-3-small",
        input=text
    )
    return response.data[0].embedding


def cosine_similarity(a, b):
    a = np.array(a)
    b = np.array(b)
    return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))


def compare_texts(text1, text2):
    emb1 = get_embedding(text1)
    emb2 = get_embedding(text2)

    similarity = cosine_similarity(emb1, emb2)

    return similarity


if __name__ == "__main__":
    # Example usage - only runs when script is executed directly
    text1 = "I love playing football"
    text2 = "I enjoy soccer"

    similarity_score = compare_texts(text1, text2)
    print("Similarity Score:", similarity_score)