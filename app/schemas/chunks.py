from pydantic import BaseModel


class ChunkMetadata(BaseModel):
    source_file: str
    chunk_index: int
    subject: str
    subject_id: int
    doc_type: str


class Chunk(BaseModel):
    text: str
    metadata: ChunkMetadata
    confidence: float | None = None