from pydantic import BaseModel

class UploadResponse(BaseModel):
    success: bool
    message: str
    aws_key: str
    doc_id: str