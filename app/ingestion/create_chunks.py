from langchain_text_splitters import RecursiveCharacterTextSplitter
from app.models.raw_text_blocks import RawTextBlock
from app.models.chunks import Chunk, ChunkMetadata

splitter = RecursiveCharacterTextSplitter(
    separators = ["\n\n", "\n", ". ", " ", ""],
    chunk_size=500,
    chunk_overlap=50,
)


async def create_chunks(raw_blocks: list[RawTextBlock]) -> list[Chunk]:
    chunks=[]

    for block in raw_blocks:
        splits = splitter.split_text(block.text)

        for i, split in enumerate(splits):
            cleaned = split.strip()
            if not cleaned or len(cleaned) < 30:
                continue

            chunks.append(
                Chunk(
                    text=split,
                    metadata=ChunkMetadata(
                        source_file= block.metadata.source_file,
                        page_no= block.metadata.page_no,
                        chunk_index= i,
                        source_type= block.metadata.source_type,
                        content_type= block.metadata.content_type,
                        subject= block.metadata.subject,
                        subject_id= block.metadata.subject_id
                    )
                )
            )
        
    return chunks