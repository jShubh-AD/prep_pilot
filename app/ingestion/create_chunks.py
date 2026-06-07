from langchain_text_splitters import RecursiveCharacterTextSplitter
from app.models.raw_text_blocks import RawTextBlock
from app.models.chunks import Chunk, ChunkMetadata

import re

def sanitize_id(text: str) -> str:
    # replace any character not in [a-zA-Z0-9._-] with underscore
    return re.sub(r'[^a-zA-Z0-9._-]', '_', text)


splitter = RecursiveCharacterTextSplitter(
    separators = ["\n\n", "\n", ". ", " ", ""],
    chunk_size=500,
    chunk_overlap=50,
)


async def create_chunks(raw_blocks: list[RawTextBlock]) -> list[Chunk]:
    chunks=[]

    for block in raw_blocks:
        splits = splitter.split_text(block.text)
        safe_filename = sanitize_id(block.metadata.source_file)


        for i, split in enumerate(splits):
            cleaned = split.strip()
            if not cleaned or len(cleaned) < 30:
                continue

            chunks.append(
                Chunk(
                    text=split,
                    metadata=ChunkMetadata(
                        source_file= safe_filename,
                        page_no= block.metadata.page_no,
                        block_no= block.metadata.block_no,
                        chunk_index= i,
                        source_type= block.metadata.source_type,
                        content_type= block.metadata.content_type,
                        subject= block.metadata.subject
                    )
                )
            )
        
    return chunks