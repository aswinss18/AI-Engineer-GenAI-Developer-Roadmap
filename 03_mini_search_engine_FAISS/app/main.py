from dotenv import load_dotenv
load_dotenv()  # Must be called before any module that reads env vars is imported

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routes.search import router as search_router
from app.core.vector_store import initialize_faiss



app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(search_router)

@app.on_event("startup")
async def startup_event():
    initialize_faiss()
