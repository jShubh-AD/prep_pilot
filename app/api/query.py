from fastapi import APIRouter, HTTPException
from app.models.query import QueryRequest
from app.embedings.embedder import embed_query
from app.embedings.store import query_collection
from app.generation.generator import genetate_answer, generallise_query
from uuid import uuid4
from app.core.redis_servcie import get_chat_session_key, get_session_key, redis_client, get_or_create_session
from app.models.redis_models import Session



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

    if session.tokens_used >= 2000 or session.messages_count >= 50 and session.is_guest:
        raise HTTPException(
            status_code=503,
            detail="You have reached your maximum daily limit."
        )
    
    chats_key = get_chat_session_key(session_id, req.subject_id)

    print(f"chats_key: {chats_key}")

    queries = generallise_query(query=req.query)
    print(f"queries: {queries}")

    query_embedings = embed_query(queries)
    results = query_collection(
        query_embedings= query_embedings,
        top_k= req.top_k
    )

    answer = await genetate_answer(
        query=req.query, 
        retrived_chunk= results, 
        chats_key= chats_key, 
        session_id= session_id
    )

    return {"success": True, "query": req.query ,"data": answer}

@query_router.get("/subjects")
async def get_subjects():
    return get_all_subjects()
