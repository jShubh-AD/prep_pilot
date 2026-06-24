from pydantic import BaseModel

class SubjectModel(BaseModel):
    subject_id: int
    subject_name: str
    subject_codes: list[str] | None = None
    universities : list[str] | None = None
    slugs: list[str] | None = None
    semester: int | None = None

# SubjectCreate 

# subject response

# all subjects