from fastapi import FastAPI
from contextlib import asynccontextmanager
from app.api.ingestion import ingestion_router
from app.api.query import query_router


app = FastAPI(
    title="PrepPilot API",
    version="1.0.0"
)

app.include_router(ingestion_router, prefix="/upload", tags=["UPLOAD DOCs"])
app.include_router(query_router, tags= ["Query"])

@app.get('/', tags=['HEALTH'])
async def health():
    return {'status':'ok', 'message':'server running fine'}