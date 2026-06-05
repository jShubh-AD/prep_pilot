from fastapi import FastAPI
from app.api.v1.documents import doc_router
from app.core.startup import initialize_services

from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    await initialize_services()

    yield

app = FastAPI(
    title="PrepPilot API",
    version="1.0.0",
    lifespan=lifespan,
)

app.include_router(doc_router)

@app.get('/')
async def health():
    return {'status':'ok', 'message':'server running fine'}