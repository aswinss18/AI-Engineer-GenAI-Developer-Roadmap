import os
from dotenv import load_dotenv

# Load environment variables from .env file FIRST
load_dotenv()

from fastapi import FastAPI, UploadFile, Form
from fastapi.middleware.cors import CORSMiddleware
import shutil
from core.rag_pipeline import process_pdf, ask_question

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


@app.post("/upload")
async def upload_pdf(file: UploadFile):

    path = UPLOAD_DIR + file.filename

    with open(path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    process_pdf(path)

    return {"message": "PDF processed successfully"}
    

@app.post("/ask")
def ask(question: str = Form()):

    answer = ask_question(question)

    return {
        "question": question,
        "answer": answer
    }