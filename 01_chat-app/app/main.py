from dotenv import load_dotenv
load_dotenv()  # Must be called before any module that reads env vars is imported

from fastapi import FastAPI
from app.routes.chat import router as chat_router
from app.routes.stream import router as stream_router
from app.routes.structered_stream import router as structered_stream_router


app = FastAPI()
app.include_router(chat_router)
app.include_router(stream_router)
app.include_router(structered_stream_router)