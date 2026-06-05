from fastapi import APIRouter, File, UploadFile, HTTPException
from app.services.documents import DocumentService
from app.storage.s3 import s3_service

doc_router = APIRouter()


@doc_router.post('/')
async def upload(file: UploadFile = File(...)):
    document_service = DocumentService(s3_service)

    return await document_service.upload_file(file)

