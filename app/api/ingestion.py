from fastapi import APIRouter, HTTPException 
from app.core.task_manager import get_task
from app.schemas.subject_schemas import ApiResponse, TaskModel

ingestion_router = APIRouter()

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