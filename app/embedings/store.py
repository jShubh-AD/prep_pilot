import chromadb
from app.schemas.chunks import Chunk
from collections import defaultdict
from app.core.helpers import sanitize_filename

PATH="data/chromadb"
COLLECTION_NAME="prep_pilot_documents"

client = chromadb.PersistentClient(path="data/chromadb")

def get_or_create_collection():
    return client.get_or_create_collection(
        name = COLLECTION_NAME,
        metadata = {"hnsw:space":"cosine"}
    )

def store_embedings(
        embedded: list[tuple[Chunk, list[float]]],
    ):

    collection = get_or_create_collection()

    ids = []
    documents = []
    embeddings = []
    metadatas = []

    for chunk, embedding in embedded:

        safe_filename = sanitize_filename(chunk.metadata.source_file)

        chunk_id = (
            f"{chunk.metadata.subject_id}_"
            f"s{safe_filename}_"
            # f"p{chunk.metadata.page_no}_"
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

    return len(ids)