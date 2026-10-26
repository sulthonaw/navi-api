"""API Endpoints for Student Kiosk participation."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.student_session import StudentSession
from app.schemas.student import (
    StudentJoinRequest,
    StudentJoinResponse,
    StudentStatusResponse,
)
from app.services.exam_service import exam_service

router = APIRouter()


@router.post(
    "/students/join",
    response_model=StudentJoinResponse,
    status_code=status.HTTP_200_OK,
    summary="Join an exam room from student kiosk",
    description="Validates room code, registers student participant, and delivers the problem story, starter code, and hint quota.",
    tags=["Student Sessions"],
)
async def join_exam_room(
    payload: StudentJoinRequest,
    db: AsyncSession = Depends(get_db),
) -> StudentJoinResponse:
    """Enter exam room and acquire problem package."""
    return await exam_service.join_room(db, payload)


@router.get(
    "/students/{student_id}",
    response_model=StudentStatusResponse,
    summary="Get current student status and quota",
    description="Returns current metrics for a specific student, including hint usage and violation counter.",
    tags=["Student Sessions"],
)
async def get_student_status(
    student_id: int,
    db: AsyncSession = Depends(get_db),
) -> StudentStatusResponse:
    """Retrieve participant session status."""
    student = await db.get(StudentSession, student_id)
    if not student:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Student #{student_id} not found.",
        )
    return StudentStatusResponse(
        student_id=student.id,
        student_name=student.student_name,
        student_id_number=student.student_id_number,
        hints_used=student.hints_used,
        violation_count=student.violation_count,
        last_status=student.last_status,
        is_submitted=student.is_submitted,
        submitted_code=student.submitted_code,
    )
