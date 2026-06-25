from fastapi import APIRouter, HTTPException
from app.schemas.query import QueryRequest
from app.core.redis_servcie import  get_or_create_session
from app.graphs.chats.states import QueryState
from app.graphs.chats.graph import query_graph

query_router = APIRouter()

@query_router.post("/query")
async def send_query(req: QueryRequest):
    if not req.query.strip():
        raise HTTPException(
            status_code=400,
            detail="Query can't be empty."
        )
    
    session_id, session = await get_or_create_session(req.session_id, True)

    print(f"session_id: {session_id} \nsession: {session}")

    if session.tokens_used >= 20000 or session.messages_count >= 50 and session.is_guest:
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
    state = await query_graph.ainvoke(state)

    return {"success": True, "query": req.query ,"data": state["llm_ans"],"session_id": session_id}