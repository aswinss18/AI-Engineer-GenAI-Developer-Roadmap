# main.py
from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from fastapi import APIRouter
from openai import OpenAI
import os
import json
import asyncio


router = APIRouter()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

app = FastAPI()
client = OpenAI()


async def structured_stream_response(prompt: str):
    stream = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "You are a precise AI. Always respond in valid JSON with keys: summary, confidence."},
            {"role": "user", "content": prompt}
        ],
        stream=True
    )

    for chunk in stream:
        if chunk.choices[0].delta.content:
            yield chunk.choices[0].delta.content
            await asyncio.sleep(0.01)

@app.post("/structured_stream")
async def stream(prompt: str):
    return StreamingResponse(stream_response(prompt), media_type="text/plain")