import chromadb
from chromadb import PersistentClient
import json

# ── config ──────────────────────────────────────────────────────────────────
CHROMA_PATH = "D:/GenAI/prep_pilot/data/chromadb"
COLLECTION_NAME="prep_pilot_documents"   # change this
SOURCE_FILE = "dbms_pyq_2024.pdf"          # change this to exact filename stored
# ────────────────────────────────────────────────────────────────────────────

client = chromadb.PersistentClient(path=CHROMA_PATH)
collection = client.get_collection(COLLECTION_NAME)

print(f"\n{'='*60}")
print(f"  ChromaDB Chunk Inspector")
print(f"  File: {SOURCE_FILE}")
print(f"{'='*60}\n")

results = collection.get(
    where={"source_file": SOURCE_FILE},
    include=["documents", "metadatas"]
)

chunks = list(zip(results["ids"], results["documents"], results["metadatas"]))

if not chunks:
    print("❌ No chunks found. Check your source_file name or collection name.")
else:
    print(f"✅ Found {len(chunks)} chunks\n")
    print(f"{'─'*60}")

    for i, (chunk_id, doc, meta) in enumerate(chunks, 1):
        print(f"\n📦 Chunk {i}/{len(chunks)}")
        print(f"   ID       : {chunk_id}")
        print(f"   Metadata : {json.dumps(meta, indent=14)}")
        print(f"   Text     :\n")
        # indent the text for readability
        for line in doc.strip().split("\n"):
            print(f"      {line}")
        print(f"\n{'─'*60}")

print(f"\n✅ Done. Total chunks: {len(chunks)}\n")