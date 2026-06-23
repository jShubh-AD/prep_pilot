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
    
    # chats_key = get_chat_session_key(session_id, req.subject_id) # to be removed

    # print(f"chats_key: {chats_key}")

    state = QueryState(
        session_id=session_id,
        subject_id=req.subject_id,
        session=session,
        queries=[req.query],
        errors=[]
    )
    state = await query_graph.ainvoke(state)


    # queries = generallise_query(query=req.query)
    # print(f"queries: {queries}")

    # query_embedings = embed_query(queries)
    # results = query_collection(
    #     query_embedings= query_embedings,
    #     top_k= req.top_k
    # )

    # answer = await genetate_answer(
    #     query=req.query, 
    #     retrived_chunk= results, 
    #     chats_key= chats_key, 
    #     session_id= session_id
    # )

    return {"success": True, "query": req.query ,"data": state["llm_ans"],"session_id": session_id}

@query_router.get("/subjects")
async def get_subjects():
    return get_all_subjects()


"""
These are good for testing conversational memory:

Basic
What is self-attention in the Attention Is All You Need paper?
Follow-up (depends on previous answer)
How does self-attention help the Transformer capture long-range dependencies better than RNNs?
Advanced follow-up (depends on understanding previous concepts)
Can you walk through the scaled dot-product attention calculation step by step using a simple example and explain why the scaling factor √dk is necessary?

A stronger memory test would be:

1. What is self-attention in the Attention Is All You Need paper?

2. How does it differ from recurrent neural networks?

3. Can you give a concrete example showing how it processes the sentence "The animal didn't cross the street because it was too tired"?

Query 2 relies on "it" = self-attention.
Query 3 relies on "it" = self-attention again and requires remembering the previous discussion. This is a good test of whether your Redis history is actually being used.
"""