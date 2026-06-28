from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from app.schemas.query import QueryRequest
from app.core.redis_servcie import  get_or_create_session
from app.graphs.chats.states import QueryState
from app.graphs.chats.graph import query_graph
import time
import json
from app.core.redis_servcie import get_redis
from app.schemas.redis_schemas import Session

query_router = APIRouter()

@query_router.post("/query")
async def send_query(req: QueryRequest):
    start = time.time()
    print(f"[API] Hit at: {start}")
    if not req.query.strip():
        raise HTTPException(
            status_code=400,
            detail="Query can't be empty."
        )
    
    session_id, session = await get_or_create_session(req.session_id, True)

    print(f"session_id: {session_id} \nsession: {session}")

    if session.tokens_used >= 2000 or session.messages_count >= 50 and session.is_guest:
        raise HTTPException(
            status_code=503,
            detail="You have reached your maximum daily limit."
        )
    
    state = QueryState(
        session_id=session_id,
        subject_id=req.subject_id,
        session=session,
        queries=[req.query],
        errors=[]
    )

    async def event_stream():
        async for chunk in query_graph.astream(state, stream_mode="messages", version="v2"):
            if chunk["type"] == "messages":
                message_chunk, metadata = chunk["data"]
                if metadata["langgraph_node"] == "generate_response":
                    content = message_chunk.content
                    if isinstance(content, list) and content:
                        text = content[0].get("text", "")
                        if text:
                            yield f"data: {json.dumps({'text': text, 'ts': time.time(), 'start': start})}\n\n"
                    elif isinstance(content, str) and content:
                        yield f"data: {content}\n\n"
        redis = get_redis()
        session_data = await redis.get(session_id)
        session = Session.model_validate_json(session_data)
        yield f"""data: {json.dumps({
            'done': True,
            'session_id': session_id,
            'total_time': time.time() - start,
            'tokens_available': 2000 - session.tokens_used,
            'tokens_used': session.tokens_used
            })}\n\n"""

    print(f"Total time: {time.time() - start:.2f}s")
    return StreamingResponse(event_stream() ,media_type="text/event-stream")