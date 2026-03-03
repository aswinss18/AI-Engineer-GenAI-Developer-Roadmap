from openai import OpenAI
from dotenv import load_dotenv
import os

load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


def generate_rag_answer(query: str, retrieved_chunks: list):
    # Build context from retrieved chunks with clear separation
    context_parts = []
    for i, chunk in enumerate(retrieved_chunks):
        context_parts.append(f"Document Excerpt {i+1}:\n{chunk['chunk']}")
    
    context = "\n\n".join(context_parts)

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        temperature=0,
        messages=[
            {
                "role": "system", 
                "content": """You are a helpful AI assistant. Your task is to answer questions using ONLY the information provided in the document excerpts below. 

Rules:
1. Base your answer ONLY on the provided excerpts
2. If the excerpts contain relevant information, use it to answer
3. Be specific and cite which parts of the excerpts you're using
4. If the excerpts don't contain the answer, say so clearly"""
            },
            {
                "role": "user", 
                "content": f"""Here are the relevant document excerpts:

{context}

Based on these excerpts, please answer this question: {query}"""
            }
        ]
    )

    return response.choices[0].message.content