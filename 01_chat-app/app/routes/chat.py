from fastapi import APIRouter
from openai import OpenAI
from app.controllers.prompt import build_system_prompt
import os

router = APIRouter()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

@router.post("/chat")
async def chat(message: str, temperature: float = 0.3, mode: str = "default"):
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        temperature=temperature,
        messages=[
            {"role": "system", "content": build_system_prompt(mode)},
            {"role": "user", "content": message}
        ]
    )

    return {"response": response.choices[0].message.content}