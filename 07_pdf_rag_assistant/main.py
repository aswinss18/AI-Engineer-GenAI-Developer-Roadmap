import os
from dotenv import load_dotenv

# Load environment variables from .env file FIRST
load_dotenv()

from fastapi import FastAPI, UploadFile, Form, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
import shutil
import json
from core.rag_pipeline import process_pdf, ask_question, ask_question_stream, ask_question_stream_with_sources
from core.vector_store import documents, clear_documents, load_persisted_state, get_persistence_status

app = FastAPI()

@app.on_event("startup")
async def startup_event():
    """Load persisted state on server startup"""
    import logging
    logger = logging.getLogger(__name__)
    
    try:
        success = load_persisted_state()
        if success:
            logger.info(f"Startup complete: {len(documents)} chunks loaded from persisted state")
        else:
            logger.info("Startup complete: initialized with empty state")
    except Exception as e:
        logger.error(f"Error during startup state loading: {e}")
        logger.info("Continuing with empty state")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

UPLOAD_DIR = "uploaded/"

# Ensure upload directory exists
os.makedirs(UPLOAD_DIR, exist_ok=True)


@app.post("/upload")
async def upload_pdf(file: UploadFile, background_tasks: BackgroundTasks):
    # Don't clear previous documents - support multi-document upload
    # clear_documents()  # Commented out to enable multi-document support
    
    path = UPLOAD_DIR + file.filename

    with open(path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    background_tasks.add_task(process_pdf, path)

    return {"message": f"PDF '{file.filename}' upload started, processing in background. Previous documents will be preserved for multi-document analysis."}
    

@app.post("/ask")
def ask(question: str = Form()):
    answer = ask_question(question)
    return {
        "question": question,
        "answer": answer
    }

@app.get("/cache/clear")
def clear_cache():
    """Clear all cached files"""
    import shutil
    if os.path.exists("cache/"):
        shutil.rmtree("cache/")
        os.makedirs("cache/", exist_ok=True)
    return {"message": "Cache cleared successfully"}

@app.get("/status")
def get_status():
    cache_files = len([f for f in os.listdir("cache/") if f.endswith('.json')]) if os.path.exists("cache/") else 0
    
    # Count unique documents
    unique_docs = set()
    for chunk in documents:
        unique_docs.add(chunk.get("doc", "unknown"))
    
    return {
        "documents_loaded": len(documents),
        "unique_documents": len(unique_docs),
        "document_names": list(unique_docs),
        "cached_files": cache_files,
        "status": "ready" if len(documents) > 0 else "no_documents",
        "multi_document_mode": len(unique_docs) > 1
    }

@app.get("/persistence/status")
def get_persistence_status_endpoint():
    """Get persistence health status including loaded document count, last save time, and validation status"""
    try:
        # Get persistence status from vector store
        persistence_status = get_persistence_status()
        
        # Add current runtime information
        persistence_status["loaded_document_count"] = len(documents)
        persistence_status["validation_status"] = "healthy" if not persistence_status.get("error") else "error"
        
        return persistence_status
    except Exception as e:
        return {
            "error": str(e),
            "loaded_document_count": len(documents),
            "validation_status": "error"
        }
@app.post("/documents/clear")
def clear_all_documents():
    """Clear all uploaded documents and start fresh"""
    try:
        clear_documents()
        return {
            "message": "All documents cleared successfully",
            "documents_loaded": len(documents),
            "status": "empty"
        }
    except Exception as e:
        return {
            "error": f"Failed to clear documents: {str(e)}",
            "documents_loaded": len(documents),
            "status": "error"
        }

@app.get("/documents/list")
def list_documents():
    """List all currently loaded documents"""
    try:
        # Group documents by source
        doc_info = {}
        for chunk in documents:
            doc_name = chunk.get("doc", "unknown")
            if doc_name not in doc_info:
                doc_info[doc_name] = {
                    "chunk_count": 0,
                    "pages": set()
                }
            doc_info[doc_name]["chunk_count"] += 1
            doc_info[doc_name]["pages"].add(chunk.get("page", 0))
        
        # Convert sets to sorted lists
        for doc_name in doc_info:
            doc_info[doc_name]["pages"] = sorted(list(doc_info[doc_name]["pages"]))
            doc_info[doc_name]["page_range"] = f"{min(doc_info[doc_name]['pages'])}-{max(doc_info[doc_name]['pages'])}" if doc_info[doc_name]["pages"] else "unknown"
        
        return {
            "total_documents": len(doc_info),
            "total_chunks": len(documents),
            "documents": doc_info
        }
    except Exception as e:
        return {
            "error": f"Failed to list documents: {str(e)}",
            "total_documents": 0,
            "total_chunks": len(documents)
        }

@app.post("/ask-stream")
async def ask_stream(question: str = Form()):
    def generate():
        for chunk_data in ask_question_stream_with_sources(question):
            yield f"data: {json.dumps(chunk_data)}\n\n"
        yield f"data: {json.dumps({'done': True})}\n\n"
    
    return StreamingResponse(generate(), media_type="text/plain")