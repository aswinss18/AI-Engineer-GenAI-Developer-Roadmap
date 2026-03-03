from dotenv import load_dotenv
load_dotenv()  # Must be called before any module that reads env vars is imported

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from route.rag import router as rag_router



app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(rag_router)