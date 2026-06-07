from fastapi import APIRouter, HTTPException
from app.models.query import QueryRequest
from app.embedings.embedder import embed_query
from app.embedings.store import query_collection



query_router = APIRouter()

@query_router.post("/query")
async def send_query(query: QueryRequest):
    if not query.query.strip():
        raise HTTPException(
            status_code=400,
            detail="Query can't be empty."
        )
    
    query_embedings = embed_query(query=query.query)
    results = query_collection(
        query_embedings= query_embedings,
        subject= query.subject,
        top_k= query.top_k
    )

    return {"success": True, "query": query.query ,"data": results}

