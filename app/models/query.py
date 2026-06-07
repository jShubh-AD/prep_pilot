# schemas.py
from pydantic import BaseModel

class QueryRequest(BaseModel):
    query: str
    subject: str
    top_k: int = 5  # optional, defaults to 5