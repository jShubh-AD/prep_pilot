from langchain_text_splitters import MarkdownTextSplitter
from app.models.md_model import MdModel
from app.models.chunks import Chunk, ChunkMetadata
import re

splitter = MarkdownTextSplitter(
    chunk_size=500,
    chunk_overlap=50,
)


def create_chunks(md: MdModel) -> list[Chunk]:
    content = re.sub(r'<!-- page \d+ -->\n', '', md.content)

    splits = splitter.split_text(content)
    chunks = []

    for i, split in enumerate(splits):
        cleaned = split.strip()
        if not cleaned or len(cleaned) < 30:
            continue

        chunks.append(
            Chunk(
                text=cleaned,
                metadata=ChunkMetadata(
                    source_file=md.source_file,
                    chunk_index=i,
                    source_type=md.source_type,
                    content_type="text",
                    subject=md.subject,
                    subject_id=md.subject_id,
                )
            )
        )

    return chunks