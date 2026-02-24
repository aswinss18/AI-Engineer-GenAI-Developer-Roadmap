from fastapi import APIRouter
from openai import OpenAI
import os

router = APIRouter()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

@router.post("/chat")
async def chat(message: str):
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        temperature=0.3,
        messages=[
            {"role": "system", "content": "You are concise."},
            {"role": "user", "content": message}
        ]
    )

    return {"response": response.choices[0].message.content}