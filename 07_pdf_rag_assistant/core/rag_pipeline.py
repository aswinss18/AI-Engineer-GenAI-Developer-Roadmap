import os
import logging
import hashlib
import json
from pathlib import Path
from core.embeddings import get_embedding
from core.vector_store import add_embeddings, search
from core.pdf_loader import load_pdf
from core.chunker import chunk_text
from openai import OpenAI

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Cache directory for processed files
CACHE_DIR = "cache/"
os.makedirs(CACHE_DIR, exist_ok=True)

def get_file_hash(file_path):
    """Generate MD5 hash of file content"""
    hash_md5 = hashlib.md5()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()

def get_cache_path(file_hash):
    """Get cache file path for a given file hash"""
    return os.path.join(CACHE_DIR, f"{file_hash}.json")

def save_to_cache(file_hash, chunks_with_metadata, embeddings):
    """Save processed chunks and embeddings to cache"""
    cache_data = {
        "chunks": chunks_with_metadata,
        "embeddings": embeddings
    }
    cache_path = get_cache_path(file_hash)
    with open(cache_path, 'w', encoding='utf-8') as f:
        json.dump(cache_data, f, ensure_ascii=False, indent=2)
    logger.info(f"Saved cache to {cache_path}")

def load_from_cache(file_hash):
    """Load processed chunks and embeddings from cache"""
    cache_path = get_cache_path(file_hash)
    if os.path.exists(cache_path):
        try:
            with open(cache_path, 'r', encoding='utf-8') as f:
                cache_data = json.load(f)
            logger.info(f"Loaded from cache: {cache_path}")
            return cache_data["chunks"], cache_data["embeddings"]
        except Exception as e:
            logger.error(f"Error loading cache: {e}")
            return None, None
    return None, None

def get_client():
    return OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def process_pdf(file_path):
    logger.info(f"Starting PDF processing for: {file_path}")
    
    try:
        # Calculate file hash
        file_hash = get_file_hash(file_path)
        logger.info(f"File hash: {file_hash}")
        
        # Try to load from cache first
        cached_chunks, cached_embeddings = load_from_cache(file_hash)
        
        if cached_chunks and cached_embeddings:
            logger.info("Using cached data - skipping PDF processing and embedding generation")
            add_embeddings(cached_chunks, cached_embeddings)
            logger.info("PDF processing completed using cache")
            return
        
        # Process PDF if not in cache
        logger.info("No cache found - processing PDF from scratch")
        pages_data = load_pdf(file_path)
        logger.info(f"Loaded {len(pages_data)} pages from PDF")
        
        chunks_with_metadata = chunk_text(pages_data)
        logger.info(f"Created {len(chunks_with_metadata)} chunks")
        
        embeddings = []
        
        for i, chunk_data in enumerate(chunks_with_metadata):
            logger.info(f"Processing chunk {i+1}/{len(chunks_with_metadata)}")
            embeddings.append(get_embedding(chunk_data["text"]))
        
        # Save to cache for future use
        save_to_cache(file_hash, chunks_with_metadata, embeddings)
        
        # Add to vector store
        add_embeddings(chunks_with_metadata, embeddings)
        logger.info("PDF processing completed successfully")
        
    except Exception as e:
        logger.error(f"Error processing PDF: {e}")
        raise

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
    logger.info(f"Received question: {question}")
    query_embedding = get_embedding(question)
    context_chunks = search(query_embedding)
    
    logger.info(f"Found {len(context_chunks)} context chunks")
    
    if not context_chunks:
        logger.warning("No context chunks found")
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
    
    logger.info(f"Prepared {len(sources)} sources")
    
    # Stream the answer with sources
    for chunk in response:
        if chunk.choices[0].delta.content is not None:
            yield {
                "answer": chunk.choices[0].delta.content,
                "sources": sources
            }