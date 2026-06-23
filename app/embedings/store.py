import chromadb
from app.models.chunks import Chunk
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


def query_collection(
        query_embedings: list[list[float]],
        top_k: int = 5
    ) -> list[dict]:
    """
    Finds top_k most similar chunks to the query embedding.
    Returns list of results with text, metadata, and similarity distance.
    """
    collection = get_or_create_collection()

    results = collection.query(
        query_embeddings = query_embedings,
        n_results= top_k,
        include=["documents", "metadatas", "distances"]
    )

    seen = {}  # chunk_id -> output dict
    freq = defaultdict(int)  # chunk_id -> how many queries retrieved it

    for q_idx in range(len(results["ids"])):
        for i in range(len(results["ids"][q_idx])):
            chunk_id = results["ids"][q_idx][i]
            freq[chunk_id] += 1
            
            if chunk_id not in seen:
                seen[chunk_id] = {
                    "text": results["documents"][q_idx][i],
                    "metadata": results["metadatas"][q_idx][i],
                    "distance": results["distances"][q_idx][i],
                }

    # attach frequency as confidence
    output = []
    for chunk_id, chunk in seen.items():
        output.append({
            **chunk,
            "confidence": round(freq[chunk_id]/ 4, 2)  # 1, 2, 3, or 4
        })
    return output