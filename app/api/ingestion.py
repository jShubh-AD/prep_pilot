from fastapi import APIRouter, HTTPException, UploadFile, File
import python_multipart
from app.ingestion.pdf_type_detection import get_pdf_type
from app.ingestion.text_extractor import extract_text
from app.ingestion.create_chunks import create_chunks
from app.embedings.embedder import embed_chunks
from app.embedings.store import store_embedings

ingestion_router = APIRouter()

max_size = 50 * 1024 *1024 # 50MB

@ingestion_router.post("/")
async def upload_doc(subject: str, file: UploadFile = File(...)):
    if not file.filename.endswith(".pdf"):
        raise HTTPException(
            status_code=400,
            detail="Only PDFs are allowed"
        )
    
    if file.content_type != 'application/pdf':
        raise HTTPException(
            status_code=400,
            detail=f"Invalid content type: {file.content_type}. Must be application/pdf."
        )
    
    contents = await file.read()
    if len(contents) > max_size:
        raise HTTPException(
            status_code=413,
            detail="File too large. Max allowed size is 50MB."
        )
    
    if len(contents) == 0:
        raise HTTPException(
            status_code=400,
            detail="Uploaded file is empty."
        )
    
    await file.seek(0)

    #  check pdf type is it native or scanned images
    type = await get_pdf_type(contents)

    if type == "native":
        raw_blocks = await extract_text(contents, file.filename, subject)
        chunks = await create_chunks(raw_blocks=raw_blocks)
        embeddings = embed_chunks(chunks=chunks)
        stored = store_embedings(embeddings, subject= subject)
        return {
        "success": True,
        "total_embedded": len(embeddings),
        "stored": stored
    }
    return {"success": False, "data": "vison pdf encountered"}