from app.storage.s3 import S3Service
from fastapi import UploadFile, HTTPException
import uuid
from app.models.upload import UploadResponse

class DocumentService():
    def __init__(self, s3_service: S3Service):
        self.s3_service = s3_service

    

    async def upload_file(self,file: UploadFile) -> UploadResponse:

        if not file.filename:
            raise HTTPException(
                status_code=400,
                detail="No filename provided"
            )
        
        if file.content_type != "application/pdf":
            raise HTTPException(
                status_code=400,
                detail="Only PDF files are allowed"
            )

        document_id = str(uuid.uuid4())
        s3_key = f"documents/{document_id}.pdf"

        try:
            self.s3_service.upload_file(
                file_obj= file.file,
                key=s3_key,
                # content_type=file.content_type
            )

            return UploadResponse(
                success=True,
                message="File uploaded successfully",
                aws_key= s3_key,
                doc_id= document_id,
            )
        except Exception as e :
            raise HTTPException(
                status_code=500,
                detail=f"Failed to upload file: {str(e)}"
            )