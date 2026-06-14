from fastapi import APIRouter, HTTPException
from app.models.query import QueryRequest
from app.embedings.embedder import embed_query
from app.embedings.store import query_collection
from app.generation.generator import genetate_answer, generallise_query



from app.core.subject_registry import resolve_subject

query_router = APIRouter()

@query_router.post("/query")
async def send_query(query: QueryRequest):
    if not query.query.strip():
        raise HTTPException(
            status_code=400,
            detail="Query can't be empty."
        )
    
    # Resolve subject and validate
    subj_model = resolve_subject(query.subject)
    if not subj_model:
        raise HTTPException(
            status_code=404,
            detail=f"Subject '{query.subject}' not found in registry."
        )
    # Make generallise user query and generate multiple(3) similar querys
    queries = generallise_query(query=query.query)

    print(f"queries: {queries}")

    query_embedings = embed_query(queries)
    results = query_collection(
        query_embedings= query_embedings,
        subject= subj_model.subject_id,
        top_k= query.top_k
    )

    answer = genetate_answer(query=query.query, retrived_chunk= results)

    return {"success": True, "query": query.query ,"data": answer}