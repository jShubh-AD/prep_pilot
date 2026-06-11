import chromadb
from app.models.chunks import Chunk

import re

def sanitize_id(text: str) -> str:
    # replace any character not in [a-zA-Z0-9._-] with underscore
    return re.sub(r'[^a-zA-Z0-9._-]', '_', text)

client = chromadb.PersistentClient(path="data/chromadb")


def get_or_create_collection(subject: str):
    safe_name = subject.strip().lower().replace(" ", "_")
    if len(safe_name) < 3:
        safe_name = f"sub_{safe_name}"  # "os" → "sub_os"

    return client.get_or_create_collection(
        name = safe_name,
        metadata = {"hnsw:space":"cosine"}
    )

def store_embedings(
        embedded: list[tuple[Chunk, list[float]]],
        subject: str
    ):

    collection = get_or_create_collection(subject)

    ids = []
    documents = []
    embeddings = []
    metadatas = []

    for chunk, embedding in embedded:

        safe_filename = sanitize_id(chunk.metadata.source_file)

        chunk_id = (
            f"{safe_filename}_"
            f"p{chunk.metadata.page_no}_"
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


def query_collection(
        query_embedings: list[float],
        subject: str,
        top_k: int = 5
    ) -> list[dict]:
    """
    Finds top_k most similar chunks to the query embedding.
    Returns list of results with text, metadata, and similarity distance.
    """
    collection = get_or_create_collection(subject=subject)

    results = collection.query(
        query_embeddings=[query_embedings],
        n_results= top_k,
        include=["documents", "metadatas", "distances"]
    )

    output = []

    for i in range(len(results["ids"][0])):
        output.append({
            "text": results["documents"][0][i],
            "metadata": results["metadatas"][0][i],
            "distance": results["distances"][0][i]
        })

    return output