from openai import OpenAI
from dotenv import load_dotenv
from core.rag import build_rag_prompt

load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


def generate_rag_answer(query: str, retrieved_chunks: list):
    prompt = build_rag_prompt(query, retrieved_chunks)

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        temperature=0,
        messages=[
            {"role": "user", "content": prompt}
        ]
    )

    return response.choices[0].message.content