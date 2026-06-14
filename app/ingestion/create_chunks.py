from langchain_text_splitters import MarkdownTextSplitter
from app.models.md_model import MdModel
from app.models.chunks import Chunk, ChunkMetadata
import re

splitter = MarkdownTextSplitter(
    chunk_size=500,
    chunk_overlap=50,
)


IMAGE_PATTERN = re.compile(r'<!-- IMAGE_START -->.*?<!-- IMAGE_END -->', re.DOTALL)


def create_chunks(md: MdModel) -> list[Chunk]:
    content = re.sub(r'<!-- page \d+ -->\n', '', md.content)
    
    # extract image blocks and replace with placeholders
    images = {}
    def replacer(match):
        key = f"IMAGE_BLOCK_{len(images)}"
        images[key] = match.group(0)
        return f"\n{key}\n"
    
    content = IMAGE_PATTERN.sub(replacer, content)

    splits = splitter.split_text(content)
    chunks = []

    for i, split in enumerate(splits):
        cleaned = split.strip()
        if not cleaned or len(cleaned) < 30:
            continue

        # reinsert image block if has key in the chunk
        for key, block in images.items():
            if key in cleaned:
                cleaned = cleaned.replace(key, block)

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