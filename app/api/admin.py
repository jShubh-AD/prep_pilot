from fastapi import APIRouter, HTTPException, Query, UploadFile, File, BackgroundTasks
from typing import Optional
from app.core.chroma_db import get_or_create_collection
from app.schemas.chunks import Chunk, ChunkMetadata
import os
import uuid
from app.core.task_manager import create_task, run_ingestion_task

admin_router = APIRouter()

max_size = 50 * 1024 * 1024 # 50MB
TEMP_DIR = "data/temp_uploads"


@admin_router.get("/chunks")
def get_chunks(
    subject_id: Optional[int] = Query(None, description= "Ex. 0, 1, 2"),
    doc_type: Optional[str] = Query(None, description= "pyq | Notes"),
    source_file: Optional[str] = Query(None, description= "ex. dbms_pyq_2024.pdf"),
    limit: int = Query(50)
):
    collection = get_or_create_collection()

    where = {}
    if subject_id is not None:
        where["subject_id"] = subject_id
    if doc_type is not None:
        where["doc_type"] = doc_type
    if source_file is not None:
        where["source_file"] = source_file

    if len(where) > 1:
        where = {"$and": [{k: v} for k, v in where.items()]}

    results = collection.get(
        where=where if where else None,
        limit=limit,
        include=["documents", "metadatas"]
    )

    chunks = []
    for i, chunk_id in enumerate(results["ids"]):
        chunks.append({
            "chunk_id": chunk_id,
            "text": results["documents"][i],
            "metadata": results["metadatas"][i]
        })

    return {"total": len(chunks), "chunks": chunks}


@admin_router.get("/chunks/{chunk_id}")
def get_chunk(chunk_id: str):
    collection = get_or_create_collection()

    result = collection.get(
        ids=[chunk_id],
        include=["documents", "metadatas"]
    )

    if not result["ids"]:
        raise HTTPException(status_code=404, detail="Chunk not found")

    return {
        "chunk_id": chunk_id,
        "text": result["documents"][0],
        "metadata": result["metadatas"][0]
    }


@admin_router.delete("/chunks/{chunk_id}")
def delete_chunk(chunk_id: str):
    collection = get_or_create_collection()

    result = collection.get(ids=[chunk_id])
    if not result["ids"]:
        raise HTTPException(status_code=404, detail="Chunk not found")

    collection.delete(ids=[chunk_id])
    return {"message": f"Chunk {chunk_id} deleted"}


@admin_router.delete("/chunks")
def delete_chunks_by_filter(
    subject_id: Optional[int] = Query(None, description= "Ex. 0, 1, 2"),
    doc_type: Optional[str] = Query(None, description= "pyq | Notes"),
    source_file: Optional[str] = Query(None, description= "ex. dbms_pyq_2024.pdf"),
):
    if not subject_id and not doc_type and not source_file:
        raise HTTPException(status_code=400, detail="Provide at least subject_id or doc_type or source_file")

    collection = get_or_create_collection()

    where = {}
    if subject_id is not None:
        where["subject_id"] = subject_id
    if doc_type is not None:
        where["doc_type"] = doc_type
    if source_file is not None:
        where["source_file"] =source_file

    if len(where) > 1:
        where = {"$and": [{k: v} for k, v in where.items()]}

    results = collection.get(where=where, include=[])
    if not results["ids"]:
        raise HTTPException(status_code=404, detail="No chunks found for given filters")

    collection.delete(where=where)
    return {"message": f"Deleted {len(results['ids'])} chunks", "deleted_ids": results["ids"]}

# upload notes by id
@admin_router.post("/{subject_id}/upload/{doc_type}")
async def upload_notes(
    subject_id: int,
    doc_type:str,
    background_task: BackgroundTasks,
    file: UploadFile=File(...),
    ):
    if not file.filename.endswith(".pdf"):
        raise HTTPException(
            status_code=400,
            detail="Only PDFs are allowed"
        )

    if doc_type not in ["notes", "pyq"]:
        raise HTTPException(
            status_code=400,
            detail="can only upload eithe notes or pyq."
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
    
    task_id = uuid.uuid4().hex

    # Save the file to disk so the background task can read it later
    os.makedirs(TEMP_DIR, exist_ok=True)
    temp_filepath = os.path.join(TEMP_DIR, f"{task_id}.pdf")
    with open(temp_filepath, "wb") as f:
        f.write(contents)

    # Create task entry in database
    create_task(task_id=task_id, file_name=file.filename, subject_id=subject_id)
    
    # Add task to background tasks
    background_task.add_task(
        run_ingestion_task,
        task_id=task_id,
        temp_filepath=temp_filepath,
        original_filename=file.filename,
        doc_type= doc_type,
        subject_id=subject_id,
    )
    
    return {
        "success": True,
        "task_id": task_id,
        "status": "PROCESSING",
        "file_name": file.filename
    }
