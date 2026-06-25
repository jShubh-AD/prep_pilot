from fastapi import APIRouter, HTTPException # UploadFile, File, BackgroundTasks
# import python_multipart
# import uuid
# import os
# from app.ingestion.pdf_type_detection import get_pdf_type
# from app.ingestion.text_extractor import extract_text
# from app.ingestion.create_chunks import create_chunks
# from app.embedings.embedder import embed_chunks
# from app.embedings.store import store_embedings
# from app.core.helpers import sanitize_filename
# from app.ingestion.scanned_extractor import extract_scanned_pdf
from app.core.task_manager import get_task
from app.schemas.subject_schemas import ApiResponse, TaskModel

ingestion_router = APIRouter()

max_size = 50 * 1024 * 1024 # 50MB
TEMP_DIR = "data/temp_uploads"

# async def run_ingestion_task(task_id: str, temp_filepath: str, original_filename: str, subject_id: int):
#     try:
#         # 1. Read the saved temp file contents
#         with open(temp_filepath, "rb") as f:
#             contents = f.read()
        
#         # 2. Ingest
#         update_task_status(task_id, "EXTRACTING_TEXT")
#         pdf_type = await get_pdf_type(contents)
#         file_name = sanitize_filename(original_filename)
        
#         # Resolve subject or dynamically register it if not found
#         subj_model = resolve_subject(subject_id)
#         if not subj_model:
#             subj_model = register_subject(subject_name=subject_id)
        
#         if pdf_type == "native":
#             doc_content_md = await extract_text(contents, file_name, subj_model.subject_name, subj_model.subject_id)
            
#             update_task_status(task_id, "CHUNKING")
#             chunks = create_chunks(md=doc_content_md)
            
#             update_task_status(task_id, "EMBEDDING")
#             embeddings = embed_chunks(chunks=chunks)
            
#             update_task_status(task_id, "STORING")
#             stored = store_embedings(embeddings)
#         else:
#             chunks = await extract_scanned_pdf(contents, file_name, subj_model.subject_name, subject_id=subj_model.subject_id)
            
#             update_task_status(task_id, "EMBEDDING")
#             embeddings = embed_chunks(chunks=chunks)
            
#             update_task_status(task_id, "STORING")
#             stored = store_embedings(embeddings)
            
#         update_task_status(task_id, "COMPLETED", total_embedded=len(embeddings), stored=stored)
#     except Exception as e:
#         import traceback
#         error_msg = f"{type(e).__name__}: {str(e)}\n{traceback.format_exc()}"
#         print(f"Error in background ingestion task {task_id}: {error_msg}")
#         update_task_status(task_id, "FAILED", error_message=str(e))
#     finally:
#         # Clean up the local temp PDF file
#         try:
#             if os.path.exists(temp_filepath):
#                 os.remove(temp_filepath)
#         except Exception as e:
#             print(f"Error deleting temporary file {temp_filepath}: {e}")

# @ingestion_router.post("/{subject_id}")
# async def upload_doc(subject_id: int, background_tasks: BackgroundTasks, file: UploadFile = File(...)):
#     if not file.filename.endswith(".pdf"):
#         raise HTTPException(
#             status_code=400,
#             detail="Only PDFs are allowed"
#         )
    
#     if file.content_type != 'application/pdf':
#         raise HTTPException(
#             status_code=400,
#             detail=f"Invalid content type: {file.content_type}. Must be application/pdf."
#         )
    
#     contents = await file.read()
#     if len(contents) > max_size:
#         raise HTTPException(
#             status_code=413,
#             detail="File too large. Max allowed size is 50MB."
#         )
    
#     if len(contents) == 0:
#         raise HTTPException(
#             status_code=400,
#             detail="Uploaded file is empty."
#         )
    
#     task_id = uuid.uuid4().hex
    
#     # Save the file to disk so the background task can read it later
#     os.makedirs(TEMP_DIR, exist_ok=True)
#     temp_filepath = os.path.join(TEMP_DIR, f"{task_id}.pdf")
#     with open(temp_filepath, "wb") as f:
#         f.write(contents)
        
#     # Create task entry in database
#     create_task(task_id=task_id, file_name=file.filename, subject_id=subject_id)
    
#     # Add task to background tasks
#     background_tasks.add_task(
#         run_ingestion_task,
#         task_id=task_id,
#         temp_filepath=temp_filepath,
#         original_filename=file.filename,
#         subject=subject_id
#     )
    
#     return {
#         "success": True,
#         "task_id": task_id,
#         "status": "PROCESSING",
#         "file_name": file.filename
#     }

@ingestion_router.get("/{task_id}/status", status_code=200, response_model= ApiResponse[TaskModel])
async def get_ingestion_status(task_id: str):
    task = get_task(task_id)
    if not task:
        raise HTTPException(
            status_code=404,
            detail=f"Task {task_id} not found."
        )
    return ApiResponse(
        success=True,
        message="Task status fetched successfully.",
        data=TaskModel.model_validate(task)
    )