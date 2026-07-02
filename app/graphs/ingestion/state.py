from typing import TypedDict, NotRequired, Annotated
import operator
from app.schemas.chunks import Chunk

class IngestionState(TypedDict):
    task_id: str
    tempfile_path: str
    file_name: str
    subject_id: int
    subject_name: str
    doc_type: str
    
    # Inferred/runtime states
    pdf_type: NotRequired[str]
    total_pages: NotRequired[int]
    current_page: NotRequired[int]
    
    # Processed data per-batch
    mark_down: NotRequired[str | None]
    chunks: NotRequired[list[Chunk]]
    
    # Accumulate embeddings across all batches
    embeddings: Annotated[list[tuple[Chunk, list[float]]], operator.add]
    stored: NotRequired[int]
    error: NotRequired[list[str]]