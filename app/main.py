from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from app.api.ingestion import ingestion_router
from app.api.query import query_router
from app.core.redis_servcie import init_redis, close_redis


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_redis()

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


app.include_router(ingestion_router, prefix="/upload", tags=["UPLOAD DOCs"])
app.include_router(query_router, tags= ["Query"])

@app.get('/', tags=['HEALTH'])
async def health():
    return {'status':'ok', 'message':'server running fine'}