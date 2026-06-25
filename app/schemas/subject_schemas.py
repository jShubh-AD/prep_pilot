from pydantic import BaseModel
from typing import Generic, TypeVar

T = TypeVar("T")

class SubjectBase(BaseModel):
    subject_id: int
    subject_name: str
    subject_codes: list[str] | None = None
    universities : list[str] | None = None
    slugs: list[str] | None = None
    semester: int | None = None

    model_config={
        "from_attributes": True
    }

# SubjectCreate 
class CreateSubject(BaseModel):
    subject_name: str
    subject_codes: list[str] | None = None
    universities : list[str] | None = None
    slugs: list[str] | None = None
    semester: int | None = None

    model_config={
        "from_attributes": True
    }

# subject response
class SubjectResponse(BaseModel):
    subject_id: int
    subject_name: str

    model_config = {
        "from_attributes": True
    }

class UpdateSubject(BaseModel):
    subject_name: str | None=None
    subject_codes: list[str] | None = None
    universities : list[str] | None = None
    slugs: list[str] | None = None
    semester: int | None = None


class ApiResponse(BaseModel, Generic[T]):
    success: bool
    message: str | None = None
    data: T | None = None

class TaskModel(BaseModel):
    task_id: str
    status: str
    file_name: str
    subject_id: int
    total_embedded: int
    stored: int
    error_message: int
    created_at: int
    updated_at: int

    model_config={
        "from_attributes": True
    }