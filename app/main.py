from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from app.api.ingestion import ingestion_router
from app.api.chats import query_router
from app.core.redis_servcie import init_redis, close_redis
from app.api.subjects import subject_router
from app.core.database import init_db

@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_redis()
    await init_db()
    
    yield

    await close_redis()

app = FastAPI(
    title="PrepPilot API",
    version="1.0.0",
    lifespan= lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.include_router(ingestion_router, prefix="/tasks", tags=["Tasks"])
app.include_router(query_router, prefix="/chats", tags= ["Chats"])
app.include_router(subject_router, prefix="/subjects", tags= ["Subjects"])

@app.get('/', tags=['HEALTH'])
async def health():
    return {'status':'ok', 'message':'server running fine'}