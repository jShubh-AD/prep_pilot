from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, BackgroundTasks
from app.schemas.subject_schemas import CreateSubject, ApiResponse, SubjectResponse, UpdateSubject, SubjectBase
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.models.subject_models import Subject
from sqlalchemy import select
import os
import uuid
from app.core.task_manager import create_task, run_ingestion_task

subject_router = APIRouter()

max_size = 50 * 1024 * 1024 # 50MB
TEMP_DIR = "data/temp_uploads"

# create subject
@subject_router.post(
        path="",
        response_model= ApiResponse[SubjectResponse],
        status_code=201
        )
async def create_subject(req: CreateSubject, db: AsyncSession = Depends(get_db)):
    try:
        subject = Subject(**req.model_dump())
        db.add(subject)
        await db.commit()
        await db.refresh(subject)
        return ApiResponse(
            success=True,
            message="Subject created successfully.",
            data= SubjectResponse(
                subject_id= subject.subject_id,
                subject_name=subject.subject_name
            )
        )
    except Exception as e:
        print(e)
        await db.rollback()
        raise HTTPException(500, "Something went wrong please try again.")


# get all supjects
@subject_router.get("", response_model=ApiResponse[list[SubjectResponse]])
async def get_subjects(db: AsyncSession = Depends(get_db)):
    try:
        results = await db.execute(select(Subject))
        subjects = results.scalars().all()
        data = [
            SubjectResponse.model_validate(subject)
            for subject in subjects
        ]
        return ApiResponse(
            success=True,
            message="All subjects fetched successfully.",
            data=data
        )
    except Exception as e:
        print(e)
        raise HTTPException(500, detail="Something went wrong, please try again.")


# get subject by id
@subject_router.get("/{subject_id}", status_code=200, response_model= ApiResponse[SubjectBase])
async def get_subject(subject_id: int, db: AsyncSession =Depends(get_db)):
    try:
        subject = await db.get(Subject, subject_id)
        if not subject:
            raise HTTPException(404, detail="Subject not found")
        
        return ApiResponse(
            success=True,
            message="Subject fetched successfully.",
            data=SubjectBase.model_validate(subject)
        )
    except Exception as e:
        print(e)
        raise HTTPException(500, "Something went wrong please try again.")


# update subject by id
@subject_router.patch("/{subject_id}/update", status_code=200, response_model= ApiResponse[SubjectResponse])
async def update_subject(
    req: UpdateSubject,
    subject_id: int, 
    db: AsyncSession = Depends(get_db)
):
    try:
        subject = await db.get(Subject, subject_id)
        if not subject:
            raise HTTPException(404, detail="Subject not found")
        
        updates = req.model_dump(exclude_unset=True)

        for field, value in updates.items():
            setattr(subject, field, value)
        
        await db.commit()
        await db.refresh(subject)

        return ApiResponse(
                success=True,
                message="Subject created successfully.",
                data= SubjectResponse(
                    subject_id= subject.subject_id,
                    subject_name=subject.subject_name
                )
            )
    except Exception as e:
        print(e)
        await db.rollback()
        raise HTTPException(500, "Something went wrong please try again.")

# delete subject by id
@subject_router.delete("/{subject_id}", status_code=200, response_model= ApiResponse)
async def delete_subject(subject_id: int, db: AsyncSession = Depends(get_db)):
    try:
        subject = await db.get(Subject, subject_id)
        if not subject:
            raise HTTPException(404, detail= "Subject not found")
        await db.delete(subject)
        await db.commit()
        return ApiResponse(
            success=True,
            message="Subject deleted successfully."
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, detail="Something whent wrong.")


# upload notes by id
@subject_router.post("/{subject_id}/upload/notes")
async def upload_notes(
    subject_id: int,
    background_task: BackgroundTasks,
    file: UploadFile=File(...),
    ):
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
        doc_type= "notes",
        subject_id=subject_id,
    )
    
    return {
        "success": True,
        "task_id": task_id,
        "status": "PROCESSING",
        "file_name": file.filename
    }

# upload subject pyqs by id
