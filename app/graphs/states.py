from typing import TypedDict, Annotated
from operator import add
from app.models.chunks import Chunk
from app.models.redis_models import Session

class QueryState(TypedDict):
    session: Session
    session_id: str
    subject_id: str
    llm_ans: str
    queries: Annotated[list[str], add]
    embeddings: list[list[float]]
    chunks: list[Chunk]
    tokens_used: int # used to complete processing request
    tokens_available: int
    errors: Annotated[list[str], add]