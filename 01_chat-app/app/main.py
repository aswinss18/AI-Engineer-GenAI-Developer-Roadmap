from fastapi import FastAPI
from app.routes.chat import router as chat_router
from app.routes.stream import router as stream_router


app = FastAPI()
app.include_router(chat_router)
app.include_router(stream_router)