from fastapi import APIRouter, HTTPException
from app.schemas.subject_schemas import CreateSubjectModel

subject_router = APIRouter()

# create subject
@subject_router.post("")
async def create_subject(req: CreateSubjectModel):
    return {"msg": "ok"}


# get all supject

# upload subject notes by id

# upoad subject pyqs bby id

# update subject by id

#  delete subject by id