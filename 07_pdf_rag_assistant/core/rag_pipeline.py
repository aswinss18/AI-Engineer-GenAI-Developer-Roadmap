import os
import logging
import hashlib
import json
from pathlib import Path
from core.embeddings import get_embedding
from core.vector_store import add_embeddings, search
from core.pdf_loader import load_pdf
from core.chunker import chunk_text
from core.reranker import rerank_chunks, compress_chunks, smart_context_selection
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
    """
    Enhanced RAG pipeline with reranking and compression
    Query → Vector search (top 10) → Rerank → Select best 3 → Send to LLM
    """
    logger.info(f"Processing question with enhanced pipeline: {question}")
    
    # Step 1: Get query embedding
    query_embedding = get_embedding(question)
    
    # Step 2: Vector search for top 10 candidates
    initial_chunks = search(query_embedding, k=10)
    logger.info(f"Initial vector search found {len(initial_chunks)} chunks")
    
    if not initial_chunks:
        return "I don't have any documents to search through. Please upload a PDF first using the /upload endpoint."
    
    # Step 3: Rerank chunks using cosine similarity
    reranked_chunks = rerank_chunks(query_embedding, initial_chunks, top_k=3)
    logger.info(f"Reranked to top {len(reranked_chunks)} chunks")
    
    # Step 4: Compress chunks if needed
    compressed_chunks = compress_chunks(reranked_chunks, max_chunk_length=600)
    
    # Step 5: Smart context selection
    final_chunks = smart_context_selection(compressed_chunks, max_context_length=2000)
    
    # Build context from final chunks
    context = "\n\n".join([chunk["text"] for chunk in final_chunks])
    
    prompt = f"""
Answer the question using the context below. The context has been carefully selected and ranked for relevance.

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
    
    logger.info(f"Enhanced pipeline complete. Used {len(final_chunks)} chunks in final context")
    
    return response.choices[0].message.content

async def ask_question_stream(question):
    """
    Enhanced streaming RAG pipeline with reranking and compression
    """
    logger.info(f"Processing streaming question with enhanced pipeline: {question}")
    
    # Step 1: Get query embedding
    query_embedding = get_embedding(question)
    
    # Step 2: Vector search for top 10 candidates
    initial_chunks = search(query_embedding, k=10)
    
    if not initial_chunks:
        yield "I don't have any documents to search through. Please upload a PDF first using the /upload endpoint."
        return
    
    # Step 3: Rerank chunks using cosine similarity
    reranked_chunks = rerank_chunks(query_embedding, initial_chunks, top_k=3)
    
    # Step 4: Compress chunks if needed
    compressed_chunks = compress_chunks(reranked_chunks, max_chunk_length=600)
    
    # Step 5: Smart context selection
    final_chunks = smart_context_selection(compressed_chunks, max_context_length=2000)
    
    # Build context from final chunks
    context = "\n\n".join([chunk["text"] for chunk in final_chunks])
    
    prompt = f"""
Answer the question using the context below. The context has been carefully selected and ranked for relevance.

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
    
    # Stream the answer
    for chunk in response:
        if chunk.choices[0].delta.content is not None:
            yield chunk.choices[0].delta.content
    
def ask_question_stream_with_sources(question):
    """
    Enhanced streaming RAG pipeline with sources, reranking and compression
    Query → Vector search (top 10) → Rerank → Select best 3 → Send to LLM
    """
    import time
    start_time = time.time()
    
    logger.info(f"Processing streaming question with enhanced pipeline: {question}")
    
    # Step 1: Get query embedding
    query_embedding = get_embedding(question)
    
    # Step 2: Vector search for top 10 candidates
    initial_chunks = search(query_embedding, k=10)
    logger.info(f"Initial vector search found {len(initial_chunks)} chunks")
    
    if not initial_chunks:
        logger.warning("No context chunks found")
        yield {
            "answer": "I don't have any documents to search through. Please upload a PDF first using the /upload endpoint.",
            "sources": [],
            "metadata": {
                "chunks_found": 0,
                "initial_chunks": 0,
                "reranked_chunks": 0,
                "final_chunks": 0,
                "prompt_tokens": 0,
                "completion_tokens": 0,
                "total_tokens": 0,
                "latency": round((time.time() - start_time) * 1000, 2)
            }
        }
        return
    
    # Step 3: Rerank chunks using cosine similarity
    reranked_chunks = rerank_chunks(query_embedding, initial_chunks, top_k=5)
    logger.info(f"Reranked to top {len(reranked_chunks)} chunks")
    
    # Step 4: Compress chunks if needed
    compressed_chunks = compress_chunks(reranked_chunks, max_chunk_length=600)
    
    # Step 5: Smart context selection
    final_chunks = smart_context_selection(compressed_chunks, max_context_length=2500)
    logger.info(f"Final context selection: {len(final_chunks)} chunks")
    
    # Build context from final chunks
    context = "\n\n".join([chunk["text"] for chunk in final_chunks])
    
    prompt = f"""
Answer the question using the context below. The context has been carefully selected and ranked for relevance.

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
        stream=True,
        stream_options={"include_usage": True}
    )
    
    # Prepare sources from final chunks (show reranking scores)
    sources = []
    for chunk in final_chunks:
        source_text = chunk["text"][:150] + "..." if len(chunk["text"]) > 150 else chunk["text"]
        
        source = {
            "doc": chunk["doc"],
            "page": chunk["page"],
            "text": source_text
        }
        
        # Add reranking information if available
        if chunk.get("reranked"):
            source["cosine_similarity"] = round(chunk.get("cosine_similarity", 0), 3)
            source["combined_score"] = round(chunk.get("combined_score", 0), 3)
        
        if chunk.get("compressed"):
            source["compressed"] = True
            source["original_length"] = chunk.get("original_length", 0)
        
        sources.append(source)
    
    logger.info(f"Prepared {len(sources)} sources with enhanced metadata")
    
    # Track usage information
    usage_info = {
        "chunks_found": len(initial_chunks),
        "initial_chunks": len(initial_chunks),
        "reranked_chunks": len(reranked_chunks),
        "final_chunks": len(final_chunks),
        "prompt_tokens": 0,
        "completion_tokens": 0,
        "total_tokens": 0,
        "latency": 0,
        "pipeline_version": "enhanced_v1"
    }
    
    # Stream the answer with enhanced metadata
    for chunk in response:
        if chunk.choices and len(chunk.choices) > 0:
            if chunk.choices[0].delta.content is not None:
                current_latency = round((time.time() - start_time) * 1000, 2)
                usage_info["latency"] = current_latency
                
                yield {
                    "answer": chunk.choices[0].delta.content,
                    "sources": sources,
                    "metadata": usage_info
                }
        
        # Capture usage information when available
        if hasattr(chunk, 'usage') and chunk.usage:
            final_latency = round((time.time() - start_time) * 1000, 2)
            usage_info.update({
                "prompt_tokens": chunk.usage.prompt_tokens,
                "completion_tokens": chunk.usage.completion_tokens,
                "total_tokens": chunk.usage.total_tokens,
                "latency": final_latency
            })
            
            logger.info(f"Enhanced pipeline complete:")
            logger.info(f"  Initial chunks: {len(initial_chunks)}")
            logger.info(f"  Reranked chunks: {len(reranked_chunks)}")
            logger.info(f"  Final chunks: {len(final_chunks)}")
            logger.info(f"  Prompt tokens: {chunk.usage.prompt_tokens}")
            logger.info(f"  Completion tokens: {chunk.usage.completion_tokens}")
            logger.info(f"  Total tokens: {chunk.usage.total_tokens}")
            logger.info(f"  Latency: {final_latency}ms")
            
            # Send final chunk with complete usage info
            yield {
                "answer": "",
                "sources": sources,
                "metadata": usage_info,
                "usage_complete": True
            }