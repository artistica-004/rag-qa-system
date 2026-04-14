import os
import time
from dotenv import load_dotenv
from groq import Groq

load_dotenv()

client = Groq(api_key=os.getenv("GROQ_API_KEY"))

def generate_answer(query: str, chunks: list) -> tuple:
    """
    Generate an answer using Groq API with context from document chunks.
    Uses mixtral-8x7b-32768 which is fast, free-tier compatible, and currently supported.
    """
    context = "\n\n---\n\n".join(chunks)

    prompt = f"""You are a helpful assistant. Answer the question using ONLY the context below.
If the answer cannot be found in the provided context, respond with: "I don't have enough information in the uploaded documents to answer this."

Context from documents:
{context}

Question: {query}

Answer:"""

    try:
        start_time = time.time()

        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",  # Latest LLaMA 3.3 - currently supported on Groq
            messages=[{"role": "user", "content": prompt}],
            max_tokens=500,
            temperature=0.7
        )

        latency_ms = (time.time() - start_time) * 1000
        answer_text = response.choices[0].message.content.strip()

        return answer_text, latency_ms

    except Exception as e:
        print(f"LLM ERROR: {e}")
        raise