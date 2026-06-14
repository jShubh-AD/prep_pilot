from fastapi import APIRouter, HTTPException, UploadFile, File
import python_multipart
from app.ingestion.pdf_type_detection import get_pdf_type
from app.ingestion.text_extractor import extract_text
from app.ingestion.create_chunks import create_chunks
from app.embedings.embedder import embed_chunks
from app.embedings.store import store_embedings
from app.core.helpers import sanitize_filename
from app.core.subject_registry import resolve_subject, register_subject

ingestion_router = APIRouter()

max_size = 50 * 1024 *1024 # 50MB

@ingestion_router.post("/{subject}")
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
        file_name = sanitize_filename(file.filename)
        # Resolve subject or dynamically register it if not found
        subj_model = resolve_subject(subject)
        if not subj_model:
            subj_model = register_subject(subject_name=subject)
            
        doc_content_md = await extract_text(contents, file_name, subj_model.subject_name, subj_model.subject_id)
        chunks = create_chunks(md=doc_content_md)
        embeddings = embed_chunks(chunks=chunks)
        stored = store_embedings(embeddings)
        return {
        "success": True,
        "total_embedded": len(embeddings),
        "stored": stored
    }
    return {"success": False, "data": "vison pdf encountered"}