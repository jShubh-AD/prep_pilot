from google import genai
from google.genai import types
from app.models.chunks import Chunk, ChunkMetadata
from app.models.gemini_chunk import GeminiChunk
import pymupdf
import json
from app.core.settings import  settings

client = genai.Client(api_key=settings.GEMINI_API_KEY)

SCANNED_SYSTEM_PROMPT = """You are a technical document analyst for an exam prep RAG system.
You will receive multiple scanned PDF pages as images.

Your task is to extract content as semantically meaningful chunks ready for RAG indexing.

CHUNKING RULES:
- Split by semantic meaning — each chunk must be a complete, self-contained piece of information
- Each heading and its full content form one chunk
- Never split mid-concept, mid-explanation, or mid-table
- Merge short related points together — no chunk should be smaller than 3-4 sentences

FORMATTING RULES:
- Use # for main headings, ## for subheadings, ### for topics/subtopics
- For tables, convert to a compact columnar format in a single chunk: start with "Table: [title/topic]", then list each column name followed by its values
- For diagrams or images, describe them inline where they appear, wrapped in <!-- IMAGE_START --> and <!-- IMAGE_END --> tags

IGNORE:
- Repetitive headers or footers that do not add context
- Page numbers, watermarks, or metadata-level information

Return ONLY a JSON array of chunk objects, no other text."""

async def describe_scanned_pages(page_bytes_list: list[tuple[int, bytes]]) -> list[dict]:
    contents = [
        types.Part.from_bytes(data=image_bytes, mime_type="image/png")
        for _, image_bytes in page_bytes_list
    ]

    response = await client.aio.models.generate_content(
        model="gemini-3.5-flash",
        contents=contents,
        config=types.GenerateContentConfig(
            system_instruction=SCANNED_SYSTEM_PROMPT,
            temperature=0.1,
            response_mime_type="application/json",
            response_schema=list[GeminiChunk]
        )
    )

    return json.loads(response.text.strip())


async def extract_scanned_pdf(
        pdf_bytes: bytes,
        source_file: str,
        subject: str,
        subject_id: str,
        batch_size: int = 5
) -> list[Chunk]:
    doc = pymupdf.open(stream= pdf_bytes)

    pages: list[tuple[int, bytes]] = []
    for page in range(len(doc)):
        page_data = doc[page]
        pix = page_data.get_pixmap(dpi = 150)
        image_bytes = pix.tobytes("png")
        pages.append((page, image_bytes))

    doc.close()
    print(f"Total pages: {len(pages)}")

    batches = [pages[i:i + batch_size] for i in range(0, len(pages), batch_size)]

    all_chunks = []
    for i, batch in enumerate(batches):
        print(f"API call {i+1}/{len(batches)} with {len(batch)} pages")
        all_chunks.extend(await describe_scanned_pages(batch))


    return [
        Chunk(
            text= gc["text"],
            metadata= ChunkMetadata(
                source_file=source_file,
                subject= subject,
                subject_id= subject_id,
                chunk_index=i,
            )
        )

        for i, gc in enumerate(all_chunks)
    ]
