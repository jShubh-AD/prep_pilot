from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from app.embedings.store import get_or_create_collection
from app.graphs.chats.states import QueryState
from app.core.settings import settings
from pydantic import BaseModel, Field
from collections import defaultdict
from app.schemas.chunks import Chunk
from app.core.redis_servcie import get_redis, get_chat_session_key
from fastapi import HTTPException
import asyncio
import json

class QueryExpansion(BaseModel):
    queries: list[str] = Field(description="Three query variants")


async def query_expansion(state: QueryState):
    """
    **Node for QueryGraph**, used to expand query by user into 4 as [original, q1, q2, q3]
    """
    llm = ChatGoogleGenerativeAI(model="gemini-3.1-flash-lite", api_key = settings.GEMINI_API_KEY)
    structed_llm = llm.with_structured_output(QueryExpansion)
    res = await structed_llm.ainvoke(f"""
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
            detail="Something went wrong please try again."
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
        n_results=5
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
        raise HTTPException(
            status_code=400,
            detail="Could not find relevant informmation for your query."
        )
    return {"chunks": output}


async def generate_response(state: QueryState):
    llm = ChatGoogleGenerativeAI(model="gemini-3.1-flash-lite", api_key = settings.GEMINI_API_KEY)
    redis = get_redis()
    chats_key = get_chat_session_key(session_id=state["session_id"], subject_id= state["subject_id"])
    history_messages = []
    for msg in await redis.lrange(name=chats_key, start= -6,end= -1):
        data = json.loads(msg)
        if data["r"] == "u":
            history_messages.append(HumanMessage(content=data["c"]))
        else:
            history_messages.append(AIMessage(content=data["c"]))

    context = "\n\n".join(
        chunk.text
        for chunk in state["chunks"]
    )

    system_prompt = """
        You are PrepPilot, an AI tutor.

        Use the provided context as the primary source for your answer.
        If the context is insufficient, clearly state that.
        Do not invent facts.
        Answer directly and adapt the depth to the user's question.
    """

    messages = [
        SystemMessage(content= system_prompt),
        *history_messages, 
        HumanMessage(
            content=f"""
                    context: 
                    {context}

                    Question: 
                    {state['queries'][0]}"""
                )
    ]

    response =  await llm.ainvoke(messages)

    # add both human msg and ai response to redis chats and add token usage in redis session and msg lenth +2
    token_used = response.usage_metadata["total_tokens"]
    session = state["session"]
    session.messages_count += 2
    session.tokens_used += token_used
    await asyncio.gather(
        redis.rpush(
            chats_key,
            json.dumps({"r": "u", "c": state["queries"][0]}),
            json.dumps({"r": "a", "c": response.content}),
        ),
        redis.set(
            name=state["session_id"],
            value=session.model_dump_json(),
            keepttl=True
        )
    )

    # return response to state with token usage, token left in state
    tokens_available = 20000 - session.tokens_used
    return {"llm_ans": response.content[0]["text"], "session": session, "tokens_used": token_used, "tokens_available": tokens_available}

