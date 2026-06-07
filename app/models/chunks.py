from pydantic import BaseModel


class ChunkMetadata(BaseModel):
    source_file: str
    page_no: int
    block_no: int
    chunk_index: int
    source_type: str
    content_type: str
    subject: str


class Chunk(BaseModel):
    text: str
    metadata: ChunkMetadata