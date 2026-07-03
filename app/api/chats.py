from fastapi import APIRouter, HTTPException, Request, Depends
from app.schemas.subject_schemas import ApiResponse
from fastapi.responses import StreamingResponse
from app.graphs.chats.nodes import stream_llm_response
from app.schemas.query import QueryRequest
from app.core.redis_servcie import  get_or_create_session, get_chat_session_key
from app.graphs.chats.states import QueryState
from app.graphs.chats.graph import query_graph
import time
import json
from typing import Any
from app.core.redis_servcie import get_redis, Redis
from app.schemas.redis_schemas import Session, ChatMessages

query_router = APIRouter()

@query_router.post("/query")
async def send_query(req: QueryRequest, request: Request ,redis: Redis = Depends(get_redis)):
    start = time.time()
    print(f"[API] Hit at: {start}")
    if not req.query.strip():
        raise HTTPException(400, "Query can't be empty.")
    
    session_id, session = await get_or_create_session(req.session_id, True)

    print(f"session_id: {session_id} \nsession: {session}")

    if (session.tokens_used >= 2000 or session.messages_count >= 50) and session.is_guest:
        raise HTTPException(503,"You have reached your maximum daily limit.")
    
    state = QueryState(
        session_id=session_id,
        subject_id=req.subject_id,
        session=session,
        query=req.query,
        expanded_queries=[],
        embeddings=[],
        chunks=[],
        errors=[]
    )

    new_state = await query_graph.ainvoke(state)

    if new_state.get("errors"):
        raise HTTPException(400, new_state["errors"])

    print(f"Total time: {time.time() - start:.2f}s")
    return StreamingResponse(
        stream_llm_response(state=new_state, redis= redis, request= request, start=start),
        media_type="text/event-stream",
    )


@query_router.get("/sessions/{session_id}", status_code=200)
async def get_session(session_id: str, redis: Redis = Depends(get_redis)) -> ApiResponse[Session]:
    session_data = await redis.get(f"session:{session_id}")
    if not session_data:
        raise HTTPException(404, "session not found or expired.")
    return ApiResponse(
        success=True,
        message="Fetched session succesfully.",
        data= Session.model_validate_json(session_data)
    )

@query_router.get("/{chat_id}/{subject_id}", status_code=200)
async def get_chats(chat_id: str, subject_id: int, redis: Redis = Depends(get_redis)) -> ApiResponse[list[Any]]:
    chat_key = get_chat_session_key(chat_id, subject_id)
    session_data = await redis.lrange(chat_key, 0, -1)
    if not session_data:
        raise HTTPException(404, "session not found or expired.")
    
    messages = [json.loads(m) for m in session_data]
    return ApiResponse(
        success=True,
        message="Fetched session succesfully.",
        data= messages
    )