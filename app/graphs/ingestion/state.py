from typing import TypedDict
from typing import NotRequired
from app.schemas.chunks import Chunk

class IngestionState(TypedDict):
    task_id: str
    tempfile_path: str
    file_name:str
    subject_id: int
    subject_name: str
    pdf_type: str
    mark_down: NotRequired[str | None]
    chunks: list[Chunk]
    embeddings: list[tuple[Chunk, list[float]]]
    stored: int
    doc_type: str
    error: list[str]