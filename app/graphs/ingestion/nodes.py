from app.graphs.ingestion.state import IngestionState
import pymupdf
import pymupdf4llm
import re
from app.ingestion.vision import describe_image, describe_scanned_pages
from app.core.task_manager import update_task_status
from app.schemas.chunks import Chunk, ChunkMetadata
from langchain_text_splitters import MarkdownTextSplitter
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from app.core.settings import settings
from app.core.chroma_db import get_or_create_collection

splitter = MarkdownTextSplitter(
    chunk_size=500,
    chunk_overlap=50,
)

IMAGE_PATTERN = re.compile(r'<!-- IMAGE_START -->.*?<!-- IMAGE_END -->', re.DOTALL)
PLACEHOLDER_PATTERN = re.compile(r'==>.*?<==')


# Get pdf_type node
async def get_pdf_type(state: IngestionState):
    doc = pymupdf.open(filename=state['tempfile_path'])
    total_pages = len(doc)
    pages = doc[:3]
    total_text = ""

    for page in pages:
        total_text += page.get_text().strip()
    
    doc.close()
    pdf_type = "native" if len(total_text) > 300 else "vision"
    
    return {
        "pdf_type": pdf_type,
        "total_pages": total_pages,
        "current_page": 0,
        "stored": 0,
        "embeddings": []
    }


# Extract native_pdf batch node
async def extract_native_batch(state: IngestionState):
    update_task_status(state["task_id"], "EXTRACTING_TEXT")
    
    current_page = state.get("current_page", 0)
    total_pages = state.get("total_pages", 0)
    
    doc = pymupdf.open(state["tempfile_path"])
    pages_md = []

    start_page = current_page
    end_page = min(current_page + 5, total_pages)

    print(f"[EXTRACTING NATIVE]: Processing batch pages {start_page} to {end_page - 1} of {total_pages}")

    for page_no in range(start_page, end_page):
        print(f"[EXTRACTING]: page no. {page_no}")
        md = pymupdf4llm.to_markdown(doc, pages=[page_no], header=False, footer=False).strip()
        if not md:
            continue

        images = doc[page_no].get_images()

        if images:
            print("Found Image")
            md = re.sub(r'\*\*(==>.*?<==)\*\*', r'\1', md)
            placeholders = PLACEHOLDER_PATTERN.findall(md)
            for img_tuple, placeholder in zip(images, placeholders):
                try:
                    xref = img_tuple[0]
                    image_data = doc.extract_image(xref)
                    image_bytes = image_data["image"]
                    image_format = image_data["ext"]
                    description = await describe_image(image_bytes, image_format)
                    wrapped = f"<!-- IMAGE_START -->\n{description}\n<!-- IMAGE_END -->"
                    md = md.replace(placeholder, wrapped, 1)
                except Exception as e:
                    print(e)
                    md = md.replace(placeholder, "", 1)
        pages_md.append(f"<!-- page {page_no} -->\n{md}")
    
    doc.close()
    full_md = "\n".join(pages_md)
    return {"mark_down": full_md}


# create chunks batch node
def create_chunks(state: IngestionState):
    update_task_status(state["task_id"], "CHUNKING")
    
    mark_down_content = state.get("mark_down")
    if not mark_down_content:
        return {"chunks": []}
        
    content = re.sub(r'<!-- page \d+ -->\n', '', mark_down_content)
    
    # extract image blocks and replace with placeholders
    images = {}
    def replacer(match):
        key = f"IMAGE_BLOCK_{len(images)}"
        images[key] = match.group(0)
        return f"\n{key}\n"
    
    content = IMAGE_PATTERN.sub(replacer, content)

    splits = splitter.split_text(content)
    chunks = []
    
    total_embedded = len(state.get("embeddings", []))

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
                    doc_type=state["doc_type"],
                    source_file=state["file_name"],
                    subject=state["subject_name"],
                    subject_id=state["subject_id"],
                    chunk_index=total_embedded + len(chunks),
                )
            )
        )
    return {"chunks": chunks}


# Extract vision_pdf batch node
async def extract_scanned_batch(state: IngestionState):
    update_task_status(state["task_id"], "EXTRACTING_TEXT")

    current_page = state.get("current_page", 0)
    total_pages = state.get("total_pages", 0)
    total_embedded = len(state.get("embeddings", []))

    doc = pymupdf.open(state["tempfile_path"])
    batch = []

    start_page = current_page
    end_page = min(current_page + 5, total_pages)

    print(f"[SCANNED EXTRACTION]: Processing batch pages {start_page} to {end_page - 1} of {total_pages}")

    for page_num in range(start_page, end_page):
        pix = doc[page_num].get_pixmap(dpi=150)
        batch.append((page_num, pix.tobytes("png")))

    doc.close()

    scanned_chunks = await describe_scanned_pages(batch)
    print(f"[SCANNED EXTRACTION] Generated {len(scanned_chunks)} chunks for batch.")

    chunks = [
        Chunk(
            text=gc.text,
            metadata=ChunkMetadata(
                doc_type=state["doc_type"],
                source_file=state["file_name"],
                subject=state["subject_name"],
                subject_id=state["subject_id"],
                chunk_index=total_embedded + i,
            ),
        )
        for i, gc in enumerate(scanned_chunks)
    ]

    return {"chunks": chunks}


# chunk embedder node
async def embed_chunks(state: IngestionState):
    update_task_status(state["task_id"], "EMBEDDING")
    embeddings: list[tuple[Chunk, list[float]]] = []
    embedder = GoogleGenerativeAIEmbeddings(model="gemini-embedding-2", api_key=settings.GEMINI_API_KEY)
    
    chunks = state.get("chunks", [])
    for i in range(0, len(chunks), 50):
        print(f"[EMBEDDING CHUNKS]: embedding chunks {i}/{len(chunks)}")
        chunk_batch = chunks[i: i+50]
        chunk_text = [c.text for c in chunk_batch]
        batch_embeddings = await embedder.aembed_documents(texts=chunk_text, output_dimensionality=768)
        if not batch_embeddings:
            continue

        embeddings.extend(list(zip(chunk_batch, batch_embeddings)))
    return {"embeddings": embeddings}


# store embeddings node
def store_embedings(state: IngestionState):
    update_task_status(state["task_id"], "STORING")
    collection = get_or_create_collection()

    ids = []
    documents = []
    embeddings = []
    metadatas = []

    all_embeddings = state.get("embeddings", [])
    stored_count = state.get("stored", 0)
    current_page = state.get("current_page", 0)
    total_pages = state.get("total_pages", 0)

    # Slice only the newly appended embeddings from this batch
    new_embeddings = all_embeddings[stored_count:]

    for chunk, embedding in new_embeddings:
        print(f"[STORING]: storing chunk index {chunk.metadata.chunk_index} ({len(ids) + 1}/{len(new_embeddings)} in current batch)")
        chunk_id = (
            f"{chunk.metadata.subject_id}_"
            f"s{chunk.metadata.source_file}_"
            f"c{chunk.metadata.chunk_index}"
        )

        ids.append(chunk_id)
        documents.append(chunk.text)
        embeddings.append(embedding)
        metadatas.append(chunk.metadata.model_dump())
    
    if ids:
        collection.upsert(
            ids=ids,
            embeddings=embeddings,
            documents=documents,
            metadatas=metadatas
        )

    new_stored = stored_count + len(ids)
    next_page = min(current_page + 5, total_pages)

    print(f"[STORING BATCH DONE]: Stored {len(ids)} chunks. Next page cursor: {next_page}/{total_pages}")

    # Return reset states to keep memory usage flat
    return {
        "stored": new_stored,
        "current_page": next_page,
        "chunks": [],
        "mark_down": None
    }