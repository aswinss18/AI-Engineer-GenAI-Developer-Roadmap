from dotenv import load_dotenv
load_dotenv()  # Must be called before any module that reads env vars is imported

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from route.similarity import router as similarity_router

app = FastAPI(title="Text Similarity Engine", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(similarity_router, prefix="/api", tags=["similarity"])
