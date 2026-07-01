from langchain_google_genai import GoogleGenerativeAIEmbeddings
from fastapi import Request
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from app.core.chroma_db import get_or_create_collection
from app.graphs.chats.states import QueryState
from app.core.settings import settings
from pydantic import BaseModel, Field
from collections import defaultdict
from app.schemas.chunks import Chunk
from app.core.redis_servcie import get_chat_session_key, Redis
from fastapi import HTTPException
import asyncio
import json
import time
from app.core.llm import _make_chain, base_llm

class QueryExpansion(BaseModel):
    queries: list[str] = Field(description="Three query variants")


async def query_expansion(state: QueryState):
    """
    **Node for QueryGraph**, used to expand query by user into 4 as [original, q1, q2, q3]
    """
    llm = _make_chain(query_expansion)
    res = await llm.ainvoke(f"""
    Generate 3 retrieval-focused variants:
    - formal
    - simple
    - keyword-focused
    Rules:
    - Preserve the original meaning.
    - Do not add new information.
    - Make each variant meaningfully different.

    Query: {state['queries'][0]}
    """)
    return {"queries": res.queries}

async def query_embedings(state: QueryState):
    """
    **Node for QueryGraph**, used to generate batch embeddings for all queries.\n
    **Model used**= gemini-embedding-2
    """
    embedder = GoogleGenerativeAIEmbeddings(model= "gemini-embedding-2", api_key= settings.GEMINI_API_KEY)
    embeddings = await embedder.aembed_documents(texts=state["queries"], output_dimensionality=768)
    if not embeddings:
        raise HTTPException(
            status_code=400,
            detail="Could not create embeddings, please try again."
        )
    return {"embeddings": embeddings}

async def retrive_chunks(state: QueryState):
    """
    **Node for QueryGraph**, used to extracted **top=5** chunks for each query from ChromaDB.\n
    and returns list[Chunk], with **retrival frequency**
    """
    db = get_or_create_collection()
    results = db.query(
        query_embeddings=state["embeddings"],
        n_results=5,
        where={"subject_id": state["subject_id"]}
    )

    seen = {}
    freq = defaultdict(int)

    for ids, docs, metas, distances in zip(
        results["ids"],
        results["documents"],
        results["metadatas"],
        results["distances"]
    ):
        for chunk_id, doc, meta, distance in zip(
            ids, docs, metas, distances
        ):
            freq[chunk_id] += 1

            if chunk_id not in seen:
                seen[chunk_id] = {
                    "text": doc,
                    "metadata": meta,
                }

    output = [
    Chunk(
        text=chunk["text"],
        metadata=chunk["metadata"],
        confidence=round(freq[chunk_id] / len(state["embeddings"]), 2)
    )
    for chunk_id, chunk in seen.items()
    ]

    if not output:
        raise HTTPException(404, "no data found for your query.")
    return {"chunks": output}


SYSTEM_PROMPT = """
        You are PrepPilot, an AI tutor.

        Use the provided context as the primary source for your answer.
        If the context is insufficient, clearly state that.
        Do not invent facts.
        Answer directly and adapt the depth to the user's question.
        DOn't generate code, don't do anything exccept teaching.
    """


async def build_messages(state, redis: Redis):
    chats_key = get_chat_session_key(session_id=state["session_id"], subject_id=state["subject_id"])
    history_messages = []
    for msg in await redis.lrange(name=chats_key, start=-6, end=-1):
        data = json.loads(msg)
        if data["r"] == "u":
            history_messages.append(HumanMessage(content=data["c"]))
        else:
            history_messages.append(AIMessage(content=data["c"]))

    context = "\n\n".join(chunk.text for chunk in state["chunks"])

    return chats_key, [
        SystemMessage(content=SYSTEM_PROMPT),
        *history_messages,
        HumanMessage(content=f"context:\n{context}\n\nQuestion:\n{state['queries'][0]}"),
    ]

async def stream_llm_response(state: QueryState, redis: Redis, request: Request, start):
    chats_key, messages = await build_messages(state, redis)

    full_text = ""
    usage = None
    try:
        async for chunk in base_llm.astream(messages):
            if await request.is_disconnected():
                print("client disconnected stopping stream.")
                return
        
            content = chunk.content

            if isinstance(content, str):
                full_text += content
                yield f"event: token\ndata: {json.dumps({'text': content, 'time': time.time()})}\n\n"

            if usage is None and chunk.usage_metadata:
                usage = chunk.usage_metadata
    except Exception as e:
        yield f"event:error\ndata: {json.dumps({'message':e})}"
        return
    
    token_used = usage["total_tokens"] if usage else 0
    session = state["session"]
    session.messages_count += 2
    session.tokens_used += token_used
    try:
        await asyncio.gather(
            redis.rpush(
                chats_key,
                json.dumps({"r": "u", "c": state["queries"][0]}),
                json.dumps({"r": "a", "c": full_text}),
            ),
            redis.set(
                name=state["session"].session_key,
                value=session.model_dump_json(),
                keepttl=True
            )
        )
    except Exception as e:
        print(f"Redis persist failed for session {state['session_id']}: {e}")

    yield f"""event: done\ndata: {json.dumps({
        'session_id': state['session_id'],
        'tokens_used': token_used,
        'tokens_available': 2000 - session.tokens_used,
        'total_time': round(time.time() - start, 2)
    })}\n\n"""

