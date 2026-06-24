from fastapi import APIRouter, HTTPException, Depends
from app.schemas.subject_schemas import CreateSubject, ApiResponse, SubjectResponse, UpdateSubject
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.models.subject_models import Subject
from sqlalchemy import select

subject_router = APIRouter()

# create subject
@subject_router.post(
        path="",
        response_model= ApiResponse[SubjectResponse],
        status_code=201
        )
async def create_subject(req: CreateSubject, db: AsyncSession = Depends(get_db)):
    try:
        subject = Subject(**req.model_dump())
        db.add(subject)
        await db.commit()
        await db.refresh(subject)
        return ApiResponse(
            success=True,
            message="Subject created successfully.",
            data= SubjectResponse(
                subject_id= subject.subject_id,
                subject_name=subject.subject_name
            )
        )
    except Exception as e:
        print(e)
        await db.rollback()
        raise HTTPException(500, "Something went wrong please try again.")



# get all supject
@subject_router.get("", response_model=ApiResponse[list[SubjectResponse]])
async def get_subjects(db: AsyncSession = Depends(get_db)):
    try:
        results = await db.execute(select(Subject))
        subjects = results.scalars().all()
        data = [
            SubjectResponse.model_validate(subject)
            for subject in subjects
        ]
        return ApiResponse(
            success=True,
            message="All subjects fetched successfully.",
            data=data
        )
    except Exception as e:
        print(e)
        raise HTTPException(500, detail="Something went wrong, please try again.")


@subject_router.get("/{subject_id}", status_code=200, response_model= ApiResponse[CreateSubject])
async def get_subject(subject_id: int, db: AsyncSession =Depends(get_db)):
    try:
        subject = await db.get(Subject, subject_id)
        if not subject:
            raise HTTPException(404, detail="Subject not found")
        
        return ApiResponse(
            success=True,
            message="Subject fetched successfully.",
            data=CreateSubject.model_validate(subject)
        )
    except Exception as e:
        print(e)
        raise HTTPException(500, "Something went wrong please try again.")



# upload subject notes by id
@subject_router.patch("/{subject_id}/update", status_code=200, response_model= ApiResponse[SubjectResponse])
async def update_subject(
    req: UpdateSubject,
    subject_id: int, 
    db: AsyncSession = Depends(get_db)
):
    try:
        subject = await db.get(Subject, subject_id)
        if not subject:
            raise HTTPException(404, detail="Subject not found")
        
        updates = req.model_dump(exclude_unset=True)

        for field, value in updates.items():
            setattr(subject, field, value)
        
        await db.commit()
        await db.refresh(subject)

        return ApiResponse(
                success=True,
                message="Subject created successfully.",
                data= SubjectResponse(
                    subject_id= subject.subject_id,
                    subject_name=subject.subject_name
                )
            )
    except Exception as e:
        print(e)
        await db.rollback()
        raise HTTPException(500, "Something went wrong please try again.")


# upoad subject pyqs bby id

# update subject by id

#  delete subject by id