from google import genai
from app.core.settings import settings
import asyncio
from google.genai import types
import json
from fastapi import HTTPException
import app.core.redis_servcie as redis_client
from app.models.redis_models import Session

client = genai.Client(api_key= settings.GEMINI_API_KEY)
LLM_Model = "gemini-2.5-flash"

ans_prompt = """
You are an intelligent exam prep tutor helping a student understand and prepare for their exams.

CONTEXT:
{context}

Previous Chat: {chats}

STUDENT QUESTION: {query}

INSTRUCTIONS:
- See the previous chats to understand user behaviour and part conversations.
- Understand how and what user wants based on your past interactions. Learn from you mistakes and response accordings.
- Answer ONLY using the provided context above. Do not use outside knowledge.
- If the answer is not in the context, say "This topic is not covered in the provided material."
- Don't include resouces
- Adapt your explanation style to match how the student is asking:
  - If they ask for a simple explanation, use analogies and simple language
  - If they ask technically, be precise and use proper terminology
- Structure your answer as:
  1. Direct answer first (1-2 lines)
  2. Detailed explanation with key concepts highlighted in **bold**
  3. Example from the context if available
- For exam prep, end with a "📌 Key Point:" line summarizing what to remember

ANSWER:
"""

async def genetate_answer(
    query: str,
    retrived_chunk: list[dict],
    chats_key: str,
    session_id: str,
) -> dict:

    if not retrived_chunk:
        return {
            "answer": "I couldn't find relevant information for your query."
        }
    session_key= redis_client.get_session_key(session_id)

    session_data, chats = await asyncio.gather(
        redis_client.redis_client.get(session_key),
        redis_client.redis_client.lrange(chats_key, -10, -1)
    )

    if not session_data:
        await redis_client.delete(chats_key)
        raise HTTPException(
            status_code=400,
            detail="Couldn't find any live session, Please try again."
        )

    context = [
        f"[Source {i+1} | Confidence {chunk['confidence']}]\n{chunk['text']}"
        for i, chunk in enumerate(retrived_chunk)
    ]

    final_prompt = ans_prompt.format(
        context="\n\n".join(context),
        chats="\n".join(chats),
        query=query,
    )

    print(f"chats: {chats}")

    response = client.models.generate_content(
        model=LLM_Model,
        contents=final_prompt,
        config={
            "temperature": 0.2,
            "max_output_tokens": 1024,
        },
    )

    answer = response.text.strip()

    session = Session.model_validate_json(session_data)
    session.messages_count += 2
    session.tokens_used += response.usage_metadata.total_token_count

    await asyncio.gather(
        redis_client.redis_client.set(
            session_key,
            session.model_dump_json(),
            keepttl=True,
        ),
        redis_client.redis_client.rpush(
            chats_key,
            f"Human: {query}",
            f"Assistant: {answer}",
        ),
    )

    return {
        "answer": answer,
        "session_id": session_id
        # "llm_context": context,
        # "db_found": retrived_chunk,
    }

QUERY_EXPANSION_PROMPT = """You are a query expansion system for a student exam prep RAG application.

A student has asked a question. Your job is to rewrite it into 3 diverse variants that will help retrieve the most relevant content from a document.

Generate exactly 3 variants:
1. Formal/technical — academic language, proper terminology
2. Casual/simple — plain english, how a student would explain it
3. Keyword-focused — just the core concepts, no filler words

Rules:
- All 3 must preserve the original meaning
- Each must be lexically different, not just rephrased slightly
- Do not add information that wasn't in the original query
- Return ONLY a JSON array, no explanation, no markdown

Original query: "{user_query}"

Return format:
["variant1", "variant2", "variant3"]"""

def generallise_query(query: str) -> list[str]:
    response = client.models.generate_content(
        model= LLM_Model,
        contents=QUERY_EXPANSION_PROMPT.format(user_query=query),
        config= types.GenerateContentConfig(
            response_mime_type= "application/json",
            response_schema= list[str]
        )
    )
    text =  response.text.strip()

    print(text)
    variants = json.loads(text)
    return [query] + variants