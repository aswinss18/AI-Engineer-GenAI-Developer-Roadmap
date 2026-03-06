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

app = FastAPI()

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

    path = UPLOAD_DIR + file.filename

    with open(path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    background_tasks.add_task(process_pdf, path)

    return {"message": "PDF upload started, processing in background"}
    

@app.post("/ask")
def ask(question: str = Form()):
    answer = ask_question(question)
    return {
        "question": question,
        "answer": answer
    }

@app.post("/ask-stream")
async def ask_stream(question: str = Form()):
    def generate():
        for chunk_data in ask_question_stream_with_sources(question):
            yield f"data: {json.dumps(chunk_data)}\n\n"
        yield f"data: {json.dumps({'done': True})}\n\n"
    
    return StreamingResponse(generate(), media_type="text/plain")