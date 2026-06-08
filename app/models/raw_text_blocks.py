from pydantic import BaseModel

class Metadata(BaseModel):
    source_file: str
    page_no: int
    source_type: str
    content_type: str
    subject: str

class RawTextBlock(BaseModel):
    text: str
    metadata: Metadata