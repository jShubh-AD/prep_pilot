# schemas.py
from pydantic import BaseModel

class QueryRequest(BaseModel):
    query: str
    subject_id: int
    session_id: str | None = None
    top_k: int = 5  # optional, defaults to 5