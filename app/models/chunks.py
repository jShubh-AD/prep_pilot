from pydantic import BaseModel


class ChunkMetadata(BaseModel):
    source_file: str
    chunk_index: int
    subject: str
    subject_id: str


class Chunk(BaseModel):
    text: str
    metadata: ChunkMetadata