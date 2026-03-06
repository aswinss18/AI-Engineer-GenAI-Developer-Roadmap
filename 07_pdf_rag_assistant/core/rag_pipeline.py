import os
from core.embeddings import get_embedding
from core.vector_store import add_embeddings, search
from core.pdf_loader import load_pdf
from core.chunker import chunk_text
from openai import OpenAI

def get_client():
    return OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def process_pdf(file_path):
    pages_data = load_pdf(file_path)
    chunks_with_metadata = chunk_text(pages_data)
    embeddings = []
    
    for chunk_data in chunks_with_metadata:
        embeddings.append(get_embedding(chunk_data["text"]))
    
    add_embeddings(chunks_with_metadata, embeddings)

def ask_question(question):
    query_embedding = get_embedding(question)
    context_chunks = search(query_embedding)
    
    if not context_chunks:
        return "I don't have any documents to search through. Please upload a PDF first using the /upload endpoint."
    
    # Build context from chunks
    context = "\n\n".join([chunk["text"] for chunk in context_chunks])
    
    prompt = f"""
Answer the question using the context below.

Context:
{context}

Question:
{question}
"""
    
    client = get_client()
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "user", "content": prompt}
        ]
    )
    
    return response.choices[0].message.content

async def ask_question_stream(question):
    query_embedding = get_embedding(question)
    context_chunks = search(query_embedding)
    
    if not context_chunks:
        yield "I don't have any documents to search through. Please upload a PDF first using the /upload endpoint."
        return
    
    # Build context from chunks
    context = "\n\n".join([chunk["text"] for chunk in context_chunks])
    
    prompt = f"""
Answer the question using the context below.

Context:
{context}

Question:
{question}
"""
    
    client = get_client()
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "user", "content": prompt}
        ],
        stream=True
    )
    
    # First yield the sources
    sources = []
    for chunk in context_chunks:
        sources.append({
            "doc": chunk["doc"],
            "page": chunk["page"],
            "text": chunk["text"][:100] + "..." if len(chunk["text"]) > 100 else chunk["text"]
        })
    
    # Stream the answer
    answer_chunks = []
    for chunk in response:
        if chunk.choices[0].delta.content is not None:
            content = chunk.choices[0].delta.content
            answer_chunks.append(content)
            yield content
    
def ask_question_stream_with_sources(question):
    query_embedding = get_embedding(question)
    context_chunks = search(query_embedding)
    
    if not context_chunks:
        yield {
            "answer": "I don't have any documents to search through. Please upload a PDF first using the /upload endpoint.",
            "sources": []
        }
        return
    
    # Build context from chunks
    context = "\n\n".join([chunk["text"] for chunk in context_chunks])
    
    prompt = f"""
Answer the question using the context below.

Context:
{context}

Question:
{question}
"""
    
    client = get_client()
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "user", "content": prompt}
        ],
        stream=True
    )
    
    # Prepare sources
    sources = []
    for chunk in context_chunks:
        sources.append({
            "doc": chunk["doc"],
            "page": chunk["page"],
            "text": chunk["text"][:100] + "..." if len(chunk["text"]) > 100 else chunk["text"]
        })
    
    # Stream the answer with sources
    for chunk in response:
        if chunk.choices[0].delta.content is not None:
            yield {
                "answer": chunk.choices[0].delta.content,
                "sources": sources
            }