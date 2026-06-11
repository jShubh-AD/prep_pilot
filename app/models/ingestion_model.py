from pydantic import BaseModel

class SubjectModel(BaseModel):
    subject_name: str
    subject_id: str
    university: str | None = None
    subject_code: str | None = None