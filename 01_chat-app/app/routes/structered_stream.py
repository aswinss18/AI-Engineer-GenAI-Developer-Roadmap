# main.py
from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from fastapi import APIRouter
from openai import OpenAI
import os
import json
import asyncio

client = OpenAI()

router = APIRouter()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))




@router.post("/structured_stream")
async def structured_stream_response(prompt: str):
    stream = client.responses.stream(
        model="gpt-4.1",
        input=prompt,
        response_format={
            "type": "json_schema",
            "json_schema": {
                "name": "summary_schema",
                "schema": {
                    "type": "object",
                    "properties": {
                        "summary": {"type": "string"},
                        "confidence": {"type": "number"}
                    },
                    "required": ["summary", "confidence"]
                }
            }
        }
    )

    async for event in stream:
        if event.type == "response.output_text.delta":
            yield event.delta