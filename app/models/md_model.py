from pydantic import BaseModel

class MdModel(BaseModel):
    content: str
    source_file: str
    subject: str
    subject_id: str