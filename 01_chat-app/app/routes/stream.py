from fastapi.responses import StreamingResponse
from fastapi import APIRouter
from openai import OpenAI
from controllers.prompt import build_system_prompt
import os

router = APIRouter()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

@router.post("/stream")
async def stream_chat(message: str,temperature: float = 0.2,mode:str = "default"):

    def generate():
        stream = client.chat.completions.create(
            model="gpt-4o-mini",
            temperature=temperature,
            messages=[
                {"role": "system", "content": build_system_prompt(mode)},
                {"role": "user", "content": message}
            ],
            stream=True,
        )

        for chunk in stream:
            if chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content

    return StreamingResponse(generate(), media_type="text/event-stream")