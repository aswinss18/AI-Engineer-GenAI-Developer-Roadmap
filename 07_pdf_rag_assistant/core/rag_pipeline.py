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
from core.hybrid_search import hybrid_search, get_hybrid_search_stats
from core.multi_document_context import (
    group_chunks_by_document, 
    build_multi_document_context, 
    create_comparison_prompt,
    analyze_document_distribution,
    extract_document_insights
)
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
    Multi-Document Hybrid RAG pipeline with cross-document analysis
    Query → Hybrid Search → Group by Document → Rerank → Multi-Doc Context → LLM
    """
    logger.info(f"Processing question with multi-document hybrid pipeline: {question}")
    
    # Step 1: Hybrid search (vector + keyword)
    initial_chunks = hybrid_search(
        query=question,
        vector_k=10,     # Increased for multi-document coverage
        keyword_k=10,    # Increased for multi-document coverage
        vector_weight=0.6,
        keyword_weight=0.4
    )
    
    hybrid_stats = get_hybrid_search_stats(initial_chunks)
    logger.info(f"Hybrid search stats: {hybrid_stats}")
    
    if not initial_chunks:
        return "I don't have any documents to search through. Please upload a PDF first using the /upload endpoint."
    
    # Step 2: Group chunks by document
    grouped_chunks = group_chunks_by_document(initial_chunks)
    document_analysis = analyze_document_distribution(grouped_chunks)
    
    # Step 3: Get query embedding for reranking
    query_embedding = get_embedding(question)
    
    # Step 4: Rerank chunks using cosine similarity
    reranked_chunks = rerank_chunks(query_embedding, initial_chunks, top_k=8)
    logger.info(f"Reranked to top {len(reranked_chunks)} chunks")
    
    # Step 5: Group reranked chunks by document
    reranked_grouped = group_chunks_by_document(reranked_chunks)
    
    # Step 6: Build multi-document context
    context, context_metadata = build_multi_document_context(reranked_grouped, max_context_length=3000)
    
    # Step 7: Create specialized prompt
    prompt = create_comparison_prompt(context, question, context_metadata)
    
    client = get_client()
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "user", "content": prompt}
        ]
    )
    
    logger.info(f"Multi-document pipeline complete. Documents: {document_analysis['document_count']}, Multi-doc: {document_analysis['multi_document']}")
    
    return response.choices[0].message.content

async def ask_question_stream(question):
    """
    Enhanced streaming RAG pipeline with hybrid retrieval, reranking and compression
    """
    logger.info(f"Processing streaming question with hybrid pipeline: {question}")
    
    # Step 1: Hybrid search (vector + keyword)
    initial_chunks = hybrid_search(
        query=question,
        vector_k=8,
        keyword_k=8,
        vector_weight=0.6,
        keyword_weight=0.4
    )
    
    if not initial_chunks:
        yield "I don't have any documents to search through. Please upload a PDF first using the /upload endpoint."
        return
    
    # Step 2: Get query embedding for reranking
    query_embedding = get_embedding(question)
    
    # Step 3: Rerank chunks using cosine similarity
    reranked_chunks = rerank_chunks(query_embedding, initial_chunks, top_k=3)
    
    # Step 4: Compress chunks if needed
    compressed_chunks = compress_chunks(reranked_chunks, max_chunk_length=600)
    
    # Step 5: Smart context selection
    final_chunks = smart_context_selection(compressed_chunks, max_context_length=2000)
    
    # Build context from final chunks
    context = "\n\n".join([chunk["text"] for chunk in final_chunks])
    
    prompt = f"""
Answer the question using the context below. The context has been selected using hybrid search (vector + keyword matching) and carefully ranked for relevance.

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
    Multi-Document Hybrid RAG pipeline with cross-document analysis
    Query → Hybrid Search → Group by Document → Rerank → Multi-Doc Context → LLM
    """
    import time
    start_time = time.time()
    
    logger.info(f"Processing question with multi-document hybrid pipeline: {question}")
    
    # Step 1: Hybrid search (vector + keyword)
    initial_chunks = hybrid_search(
        query=question,
        vector_k=10,     # Increased for multi-document coverage
        keyword_k=10,    # Increased for multi-document coverage
        vector_weight=0.6,
        keyword_weight=0.4
    )
    
    hybrid_stats = get_hybrid_search_stats(initial_chunks)
    logger.info(f"Hybrid search stats: {hybrid_stats}")
    
    if not initial_chunks:
        logger.warning("No context chunks found")
        yield {
            "answer": "I don't have any documents to search through. Please upload a PDF first using the /upload endpoint.",
            "sources": [],
            "metadata": {
                "chunks_found": 0,
                "hybrid_stats": {"total": 0},
                "document_analysis": {"documents": 0, "multi_document": False},
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
    
    # Step 2: Group chunks by document for multi-document analysis
    grouped_chunks = group_chunks_by_document(initial_chunks)
    document_analysis = analyze_document_distribution(grouped_chunks)
    document_insights = extract_document_insights(grouped_chunks)
    
    logger.info(f"Document analysis: {document_analysis['document_count']} documents, multi-doc: {document_analysis['multi_document']}")
    
    # Step 3: Get query embedding for reranking
    query_embedding = get_embedding(question)
    
    # Step 4: Rerank chunks using cosine similarity (increased for multi-doc)
    reranked_chunks = rerank_chunks(query_embedding, initial_chunks, top_k=8)
    logger.info(f"Reranked to top {len(reranked_chunks)} chunks")
    
    # Step 5: Group reranked chunks by document
    reranked_grouped = group_chunks_by_document(reranked_chunks)
    
    # Step 6: Build multi-document context with document boundaries
    context, context_metadata = build_multi_document_context(
        reranked_grouped, 
        max_context_length=3500  # Increased for multi-document analysis
    )
    
    logger.info(f"Multi-document context: {context_metadata}")
    
    # Step 7: Create specialized prompt for multi-document reasoning
    prompt = create_comparison_prompt(context, question, context_metadata)
    
    client = get_client()
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "user", "content": prompt}
        ],
        stream=True,
        stream_options={"include_usage": True}
    )
    
    # Prepare sources with multi-document metadata
    sources = []
    for chunk in reranked_chunks[:context_metadata.get("total_chunks", 10)]:
        source_text = chunk["text"][:150] + "..." if len(chunk["text"]) > 150 else chunk["text"]
        
        source = {
            "doc": chunk["doc"],
            "page": chunk["page"],
            "text": source_text
        }
        
        # Add hybrid search information
        if chunk.get("search_types"):
            source["search_types"] = chunk["search_types"]
        if chunk.get("hybrid_score"):
            source["hybrid_score"] = round(chunk["hybrid_score"], 3)
        if chunk.get("vector_score"):
            source["vector_score"] = round(chunk["vector_score"], 3)
        if chunk.get("keyword_score"):
            source["keyword_score"] = round(chunk["keyword_score"], 3)
        if chunk.get("matched_terms"):
            source["matched_terms"] = chunk["matched_terms"]
        
        # Add reranking information
        if chunk.get("reranked"):
            source["cosine_similarity"] = round(chunk.get("cosine_similarity", 0), 3)
            source["combined_score"] = round(chunk.get("combined_score", 0), 3)
        
        # Add document-specific metadata
        doc_stats = document_analysis["document_stats"].get(chunk["doc"], {})
        if doc_stats:
            source["doc_coverage"] = doc_stats.get("coverage_percentage", 0)
            source["doc_avg_score"] = doc_stats.get("avg_hybrid_score", 0)
        
        sources.append(source)
    
    logger.info(f"Prepared {len(sources)} sources with multi-document metadata")
    
    # Track usage information with multi-document stats
    usage_info = {
        "chunks_found": len(initial_chunks),
        "hybrid_stats": hybrid_stats,
        "document_analysis": document_analysis,
        "document_insights": document_insights,
        "context_metadata": context_metadata,
        "initial_chunks": len(initial_chunks),
        "reranked_chunks": len(reranked_chunks),
        "final_chunks": context_metadata.get("total_chunks", 0),
        "prompt_tokens": 0,
        "completion_tokens": 0,
        "total_tokens": 0,
        "latency": 0,
        "pipeline_version": "multi_doc_hybrid_v1"
    }
    
    # Stream the answer with multi-document metadata
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
            
            logger.info(f"Multi-document hybrid pipeline complete:")
            logger.info(f"  Documents analyzed: {document_analysis['document_count']}")
            logger.info(f"  Multi-document mode: {document_analysis['multi_document']}")
            logger.info(f"  Initial chunks: {len(initial_chunks)} (hybrid)")
            logger.info(f"  Vector only: {hybrid_stats.get('vector_only', 0)}")
            logger.info(f"  Keyword only: {hybrid_stats.get('keyword_only', 0)}")
            logger.info(f"  Both methods: {hybrid_stats.get('both_methods', 0)}")
            logger.info(f"  Reranked chunks: {len(reranked_chunks)}")
            logger.info(f"  Final chunks: {context_metadata.get('total_chunks', 0)}")
            logger.info(f"  Context length: {context_metadata.get('context_length', 0)} chars")
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