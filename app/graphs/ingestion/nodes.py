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
from app.embedings.store import get_or_create_collection

splitter = MarkdownTextSplitter(
    chunk_size=500,
    chunk_overlap=50,
)


IMAGE_PATTERN = re.compile(r'<!-- IMAGE_START -->.*?<!-- IMAGE_END -->', re.DOTALL)

PLACEHOLDER_PATTERN = re.compile(r'==>.*?<==')

# Get pdf_type node
async def get_pdf_type(state: IngestionState):
    doc = pymupdf.open(filename=state['tempfile_path'])
    pages = doc[:3]
    total_text=""

    for page in pages:
        total_text += page.get_text().strip()
    
    doc.close()
    if len(total_text) > 300:
        return {"pdf_type": "native"}
    return {"pdf_type": "vision"}


#  Extract native_pdf node
async def extract_native(state: IngestionState):
    update_task_status(state["task_id"], "EXTRACTING_TEXT")
    doc = pymupdf.open(state["tempfile_path"])
    pages_md = []

    for page_no in range(len(doc)):
        print(f"[EXTRACTING]: page no. {page_no}")
        md = pymupdf4llm.to_markdown(doc, pages= [page_no], header=False, footer=False).strip()
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
                    image_data= doc.extract_image(xref)
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


# create chunks
def create_chunks(state: IngestionState):
    update_task_status(state["task_id"], "CHUNKING")
    content = re.sub(r'<!-- page \d+ -->\n', '', state["mark_down"])
    
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
                    doc_type= state["doc_type"],
                    source_file=state["file_name"],
                    subject= state["subject_name"],
                    subject_id= state["subject_id"],
                    chunk_index=i,
                )
            )
        )
    return {"chunks":chunks}


#  Extract vision_pdf node
async def extract_scanned_pdf(state: IngestionState):
    update_task_status(state["task_id"], "EXTRACTING_TEXT")
    doc = pymupdf.open(state["tempfile_path"])
    pages: list[tuple[int, bytes]] = []
    for page in range(len(doc)):
        page_data = doc[page]
        pix = page_data.get_pixmap(dpi = 150)
        image_bytes = pix.tobytes("png")
        pages.append((page, image_bytes))

    doc.close()
    print(f"Total pages: {len(pages)}")

    batches = [pages[i:i + 5] for i in range(0, len(pages), 5)]

    all_chunks = []
    for i, batch in enumerate(batches):
        print(f"API call {i+1}/{len(batches)} with {len(batch)} pages")
        all_chunks.extend(await describe_scanned_pages(batch))
        print(f"[SCANNED]: adding chunks {i}")
    return {
        "chunks": [
            Chunk(
                text= gc["text"],
                metadata= ChunkMetadata(
                    doc_type= state["doc_type"],
                    source_file=state["file_name"],
                    subject= state["subject_name"],
                    subject_id= state["subject_id"],
                    chunk_index=i,
            )
        )
        for i, gc in enumerate(all_chunks)
    ]}

# chunk embedder
async def embed_chunks(state: IngestionState):
    update_task_status(state["task_id"],"EMBEDDING")
    embeddings: list[tuple[Chunk, list[float]]] = []
    embedder = GoogleGenerativeAIEmbeddings(model="gemini-embedding-2", api_key=settings.GEMINI_API_KEY)
    for i in range(0,len(state["chunks"]), 50):
        print(f"[embedding]: embeddings chunks {i}/{len(state['chunks'])}")
        chunk_batch = state["chunks"][i: i+50]
        chunk_text = [c.text for c in chunk_batch]
        batch_embeddings = await embedder.aembed_documents(texts=chunk_text, output_dimensionality=768)
        if not batch_embeddings:
            continue

        embeddings.extend(list(zip(chunk_batch, batch_embeddings)))
    return {"embeddings": embeddings}

#  store embeddings
def store_embedings(state: IngestionState):
    update_task_status(state["task_id"], "STORING")
    collection = get_or_create_collection()

    ids = []
    documents = []
    embeddings = []
    metadatas = []

    for chunk, embedding in state["embeddings"]:
        print("[storring]: embedded chunks")
        chunk_id = (
            f"{chunk.metadata.subject_id}_"
            f"s{chunk.metadata.source_file}_"
            f"c{chunk.metadata.chunk_index}"
        )

        ids.append(chunk_id)
        documents.append(chunk.text)
        embeddings.append(embedding)
        metadatas.append(chunk.metadata.model_dump())
    
    collection.upsert(
        ids=ids,
        embeddings=embeddings,
        documents=documents,
        metadatas=metadatas
    )

    return {"stored": len(ids)}