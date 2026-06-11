from google import genai
from app.core.settings import settings


client = genai.Client(api_key= settings.GEMINI_API_KEY)
LLM_Model = "gemini-2.5-flash-lite"

prompt = """
You are an exam prep assistant helping a student study.
CONTEXT: {context}

QUESTION: {query}

INSTRUCTIONS:
- Answer ONLY using the provided context above.
- Be concise and clear — this is for exam preparation.
- If the answer is not in the context, say "This topic is not covered in the provided material."

ANSWER:
"""

def genetate_answer(query: str, retrived_chunk: list[dict]) -> dict:
    if not retrived_chunk:
        return {
            "answer": "I couldn't find relevant information for your query.",
        } 
    
    context = []
    for i, chunk in enumerate(retrived_chunk):
        context.append(
            f"[Source {i+1} | Page {chunk['metadata']['page_no'] + 1}]\n{chunk['text']}"
        )
    context_str = "\n\n".join(context)

    # inject into prompt
    final_prompt = prompt.format(
        context=context_str,
        query=query
    )

    response = client.models.generate_content(
        model=LLM_Model,
        contents=final_prompt,
        config={"temperature": 0.2}
    )

    return {
        "answer": response.text.strip(),
    }