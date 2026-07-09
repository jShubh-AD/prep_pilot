from typing import TypedDict, Annotated
from operator import add
from app.schemas.chunks import Chunk
from app.schemas.redis_schemas import Session
from app.schemas.query import QueryAnalysis

class QueryState(TypedDict):
    session: Session
    session_id: str
    subject_id: int
    subject_name: str
    format: str

    query: str  # Original query from user
    analysis: QueryAnalysis | None
    expanded_queries: list[str]

    embeddings: list[list[float]]  # List of vectors for each expanded query
    chunks: list[Chunk]

    errors: Annotated[list[str], add]