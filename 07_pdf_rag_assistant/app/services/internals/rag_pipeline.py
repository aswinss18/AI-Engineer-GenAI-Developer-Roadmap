"""
RAG pipeline: process PDFs and answer questions using hybrid search.
Moved from core/rag_pipeline.py — imports updated to app package paths.
"""

import os
import logging
import hashlib
import json
import time
from app.services.internals.embeddings import get_embedding
from app.db.vector_store import add_embeddings, search
from app.services.internals.chunker import chunk_text
from app.services.internals.pdf_loader import load_pdf
from app.services.internals.reranker import rerank_chunks, compress_chunks, smart_context_selection
from app.services.internals.hybrid_search import hybrid_search, get_hybrid_search_stats
from app.services.internals.multi_document_context import (
    group_chunks_by_document,
    build_multi_document_context,
    create_comparison_prompt,
    analyze_document_distribution,
    extract_document_insights,
)
from app.services.internals.prompt_templates import build_optimized_prompt, optimize_context
from app.core.config import settings
from openai import OpenAI

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

CACHE_DIR = settings.cache_dir
os.makedirs(CACHE_DIR, exist_ok=True)


def _get_client() -> OpenAI:
    return OpenAI(api_key=settings.openai_api_key)


def get_file_hash(file_path: str) -> str:
    hash_md5 = hashlib.md5()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()


def get_cache_path(file_hash: str) -> str:
    return os.path.join(CACHE_DIR, f"{file_hash}.json")


def save_to_cache(file_hash: str, chunks_with_metadata, embeddings):
    cache_data = {"chunks": chunks_with_metadata, "embeddings": embeddings}
    cache_path = get_cache_path(file_hash)
    with open(cache_path, "w", encoding="utf-8") as f:
        json.dump(cache_data, f, ensure_ascii=False, indent=2)
    logger.info(f"Saved cache to {cache_path}")


def load_from_cache(file_hash: str):
    cache_path = get_cache_path(file_hash)
    if os.path.exists(cache_path):
        try:
            with open(cache_path, "r", encoding="utf-8") as f:
                cache_data = json.load(f)
            logger.info(f"Loaded from cache: {cache_path}")
            return cache_data["chunks"], cache_data["embeddings"]
        except Exception as e:
            logger.error(f"Error loading cache: {e}")
            return None, None
    return None, None


def process_pdf(file_path: str):
    """Process a PDF file and store embeddings in the vector store."""
    logger.info(f"Starting PDF processing for: {file_path}")
    try:
        file_hash = get_file_hash(file_path)
        cached_chunks, cached_embeddings = load_from_cache(file_hash)
        if cached_chunks and cached_embeddings:
            logger.info("Using cached data — skipping PDF processing")
            add_embeddings(cached_chunks, cached_embeddings)
            return
        logger.info("No cache found — processing PDF from scratch")
        pages_data = load_pdf(file_path)
        chunks_with_metadata = chunk_text(pages_data)
        embeddings = []
        for i, chunk_data in enumerate(chunks_with_metadata):
            logger.info(f"Processing chunk {i + 1}/{len(chunks_with_metadata)}")
            embeddings.append(get_embedding(chunk_data["text"]))
        save_to_cache(file_hash, chunks_with_metadata, embeddings)
        add_embeddings(chunks_with_metadata, embeddings)
        logger.info("PDF processing completed successfully")
    except Exception as e:
        logger.error(f"Error processing PDF: {e}")
        raise


def ask_question(question: str) -> str:
    """Optimised multi-document hybrid RAG pipeline (non-streaming)."""
    logger.info(f"Processing question with optimised hybrid pipeline: {question}")
    initial_chunks = hybrid_search(
        query=question, vector_k=8, keyword_k=8, vector_weight=0.6, keyword_weight=0.4
    )
    if not initial_chunks:
        return "I don't have any documents to search through. Please upload a PDF first using the /upload endpoint."
    query_embedding = get_embedding(question)
    reranked_chunks = rerank_chunks(query_embedding, initial_chunks, top_k=5)
    optimized_context = optimize_context(reranked_chunks, question)
    optimized_prompt = build_optimized_prompt(query=question, context=optimized_context)
    client = _get_client()
    response = client.chat.completions.create(
        model=settings.model_name,
        messages=[{"role": "user", "content": optimized_prompt}],
        temperature=0.1,
        max_tokens=1000,
    )
    return response.choices[0].message.content


async def ask_question_stream(question: str):
    """Streaming RAG pipeline with hybrid retrieval and reranking."""
    initial_chunks = hybrid_search(query=question, vector_k=8, keyword_k=8)
    if not initial_chunks:
        yield "I don't have any documents to search through. Please upload a PDF first."
        return
    query_embedding = get_embedding(question)
    reranked_chunks = rerank_chunks(query_embedding, initial_chunks, top_k=3)
    compressed_chunks = compress_chunks(reranked_chunks, max_chunk_length=600)
    final_chunks = smart_context_selection(compressed_chunks, max_context_length=2000)
    context = "\n\n".join([chunk["text"] for chunk in final_chunks])
    prompt = f"""Answer the question using the context below.\n\nContext:\n{context}\n\nQuestion:\n{question}"""
    client = _get_client()
    response = client.chat.completions.create(
        model=settings.model_name,
        messages=[{"role": "user", "content": prompt}],
        stream=True,
    )
    for chunk in response:
        if chunk.choices[0].delta.content is not None:
            yield chunk.choices[0].delta.content


def ask_question_stream_with_sources(question: str):
    """Multi-document hybrid RAG pipeline with cross-document analysis (streaming)."""
    start_time = time.time()
    initial_chunks = hybrid_search(
        query=question, vector_k=10, keyword_k=10, vector_weight=0.6, keyword_weight=0.4
    )
    hybrid_stats = get_hybrid_search_stats(initial_chunks)
    if not initial_chunks:
        yield {
            "answer": "I don't have any documents to search through. Please upload a PDF first.",
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
                "latency": round((time.time() - start_time) * 1000, 2),
            },
        }
        return
    grouped_chunks = group_chunks_by_document(initial_chunks)
    document_analysis = analyze_document_distribution(grouped_chunks)
    document_insights = extract_document_insights(grouped_chunks)
    query_embedding = get_embedding(question)
    reranked_chunks = rerank_chunks(query_embedding, initial_chunks, top_k=8)
    reranked_grouped = group_chunks_by_document(reranked_chunks)
    context, context_metadata = build_multi_document_context(reranked_grouped, max_context_length=3500)
    prompt = create_comparison_prompt(context, question, context_metadata)
    client = _get_client()
    response = client.chat.completions.create(
        model=settings.model_name,
        messages=[{"role": "user", "content": prompt}],
        stream=True,
        stream_options={"include_usage": True},
    )
    sources = []
    for chunk in reranked_chunks[: context_metadata.get("total_chunks", 10)]:
        source_text = chunk["text"][:150] + "..." if len(chunk["text"]) > 150 else chunk["text"]
        source = {"doc": chunk["doc"], "page": chunk["page"], "text": source_text}
        if chunk.get("search_types"):
            source["search_types"] = chunk["search_types"]
        if chunk.get("hybrid_score"):
            source["hybrid_score"] = round(chunk["hybrid_score"], 3)
        if chunk.get("cosine_similarity"):
            source["cosine_similarity"] = round(chunk.get("cosine_similarity", 0), 3)
        if chunk.get("combined_score"):
            source["combined_score"] = round(chunk.get("combined_score", 0), 3)
        doc_stats = document_analysis["document_stats"].get(chunk["doc"], {})
        if doc_stats:
            source["doc_coverage"] = doc_stats.get("coverage_percentage", 0)
        sources.append(source)
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
        "pipeline_version": "multi_doc_hybrid_v1",
    }
    for chunk in response:
        if chunk.choices and chunk.choices[0].delta.content is not None:
            usage_info["latency"] = round((time.time() - start_time) * 1000, 2)
            yield {"answer": chunk.choices[0].delta.content, "sources": sources, "metadata": usage_info}
        if hasattr(chunk, "usage") and chunk.usage:
            final_latency = round((time.time() - start_time) * 1000, 2)
            usage_info.update({
                "prompt_tokens": chunk.usage.prompt_tokens,
                "completion_tokens": chunk.usage.completion_tokens,
                "total_tokens": chunk.usage.total_tokens,
                "latency": final_latency,
            })
            yield {"answer": "", "sources": sources, "metadata": usage_info, "usage_complete": True}
