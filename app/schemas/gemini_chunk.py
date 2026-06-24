from pydantic import BaseModel

class GeminiChunk(BaseModel):
    text: str
    page_no: int