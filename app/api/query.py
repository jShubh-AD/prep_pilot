from fastapi import APIRouter, HTTPException
from app.models.query import QueryRequest
from app.embedings.embedder import embed_query
from app.embedings.store import query_collection
from app.generation.generator import genetate_answer, generallise_query
from uuid import uuid4
from app.core.redis_servcie import get_chat_session_key, get_session_key, redis_client, get_or_create_session
from app.models.redis_models import Session
from app.graphs.states import QueryState
from app.graphs.graph import query_graph



from app.core.subject_registry import resolve_subject, get_all_subjects

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

@query_router.get("/subjects")
async def get_subjects():
    return get_all_subjects()