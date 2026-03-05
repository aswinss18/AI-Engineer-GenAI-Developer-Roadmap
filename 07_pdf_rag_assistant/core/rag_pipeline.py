from core.embeddings import get_embedding
from core.vector_store import add_embeddings, search
from core.pdf_loader import load_pdf
from core.chunker import chunk_text
from openai import OpenAI

client = OpenAI()


def process_pdf(file_path):

    text = load_pdf(file_path)

    chunks = chunk_text(text)

    embeddings = []

    for chunk in chunks:
        embeddings.append(get_embedding(chunk))

    add_embeddings(chunks, embeddings)


def ask_question(question):

    query_embedding = get_embedding(question)

    context = search(query_embedding)

    prompt = f"""
Answer the question using the context below.

Context:
{context}

Question:
{question}
"""

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "user", "content": prompt}
        ]
    )

    return response.choices[0].message.content