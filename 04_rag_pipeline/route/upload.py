from fastapi import APIRouter, UploadFile, File, HTTPException
from core.document_store import initialize_document, index, chunks_store
import PyPDF2
import io

router = APIRouter()


@router.get("/status")
async def get_status():
    """
    Check if a document is loaded and indexed.
    """
    return {
        "indexed": index is not None,
        "chunks_count": len(chunks_store) if chunks_store else 0
    }


@router.post("/upload")
async def upload_document(file: UploadFile = File(...)):
    """
    Upload and process a document (txt or pdf).
    """
    try:
        content = await file.read()
        
        if file.filename.endswith('.txt'):
            text = content.decode('utf-8')
        elif file.filename.endswith('.pdf'):
            pdf_reader = PyPDF2.PdfReader(io.BytesIO(content))
            text = ""
            for page in pdf_reader.pages:
                text += page.extract_text() + "\n"
        else:
            raise HTTPException(status_code=400, detail="Only .txt and .pdf files are supported")
        
        if not text.strip():
            raise HTTPException(status_code=400, detail="Document is empty")
        
        # Initialize the document store
        initialize_document(text)
        
        return {
            "message": "Document uploaded and indexed successfully",
            "filename": file.filename,
            "size": len(text)
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
