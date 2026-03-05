import os
from openai import OpenAI

def get_client():
    return OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def get_embedding(text):
    client = get_client()
    response = client.embeddings.create(
        model="text-embedding-3-small",
        input=text
    )
    return response.data[0].embedding