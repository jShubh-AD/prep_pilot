from redis.asyncio import Redis
from app.schemas.redis_schemas import Session
from app.core.settings import settings
from uuid import uuid4

redis_client: Redis | None = None

def get_redis() -> Redis:
    if redis_client is None:
        raise RuntimeError("Redis not initialized")

    return redis_client

async def init_redis():
    global redis_client

    redis_client = Redis(
        host= settings.REDIS_HOST,
        port= settings.REDIS_PORT,
        decode_responses=True
    )

    await redis_client.ping()

async def close_redis() -> None:
    if redis_client:
        await redis_client.close()


def get_session_key(session_id: str)->str:
    return f"session:{session_id}"

def get_chat_session_key(session_id:str, subject_id:str)->str:
    return f"chats:{session_id}:{subject_id}"

def get_chat_summary_key(session_id:str, subject_id:str)->str:
    return f"chat_summary:{session_id}:{subject_id}"

def get_session_id() -> str:
    """
    retruns session id(uuid4) for chat sessions 
    """
    return str(uuid4())

async def get_or_create_session(
    session_id: str | None,
    is_guest: bool = True
) -> tuple[str, Session]:

    if session_id:
        data = await redis_client.get(get_session_key(session_id))

        if data:
            return (
                session_id,
                Session.model_validate_json(data)
            )

    session_id = get_session_id()
    session_key= get_session_key(session_id)

    session = Session(
        user_id=None,
        session_key= session_key,
        is_guest=is_guest,
        tokens_used=0,
        messages_count=0
    )

    await redis_client.set(
        session_key,
        session.model_dump_json(),
        ex=86400 if is_guest else None
    )

    return session_id, session