from openai import OpenAI
import os
from document_store import search_chunks
from generate import generate_rag_answer

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def build_rag_prompt(query: str, retrieved_chunks: list):
    context = "\n\n".join(
        [chunk["chunk"] for chunk in retrieved_chunks]
    )

    prompt = f"""
You are a helpful AI assistant.

Answer the question using ONLY the context below.
If the answer is not in the context, say "I don't know."

Context:
{context}

Question:
{query}

Answer:
"""

    return prompt


def rag_pipeline(query: str):
    retrieved = search_chunks(query, k=3)
    answer = generate_rag_answer(query, retrieved)

    return {
        "answer": answer,
        "sources": retrieved
    }