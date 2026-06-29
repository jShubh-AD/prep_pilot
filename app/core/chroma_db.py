import chromadb

PATH="data/chromadb"
COLLECTION_NAME="prep_pilot_documents"

client = chromadb.PersistentClient(path="data/chromadb")

def get_or_create_collection():
    return client.get_or_create_collection(
        name = COLLECTION_NAME,
        metadata = {"hnsw:space":"cosine"}
    )