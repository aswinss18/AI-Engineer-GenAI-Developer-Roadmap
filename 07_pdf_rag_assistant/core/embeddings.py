import os
from openai import OpenAI

def get_client():
    return OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

embedding_cache = {}

def get_embedding(text):

    if text in embedding_cache:
        return embedding_cache[text]

    client = get_client()

    response = client.embeddings.create(
        model="text-embedding-3-small",
        input=text
    )
    
    vector = response.data[0].embedding
    embedding_cache[text] = vector

    return vector