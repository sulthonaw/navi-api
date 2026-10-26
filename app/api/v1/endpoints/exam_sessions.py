"""API Endpoints for Exam Sessions managed by teachers."""

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.schemas.exam_session import (
    ExamSessionCreate,
    ExamSessionDetailResponse,
    ExamSessionResponse,
)
from app.services.exam_service import exam_service

router = APIRouter()


@router.post(
    "/rooms",
    response_model=ExamSessionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new exam session",
    description="Allows a teacher to create a new exam room with starter code, test cases, and hint rules. Returns a unique room code.",
    tags=["Exam Sessions"],
)
async def create_exam_room(
    payload: ExamSessionCreate,
    db: AsyncSession = Depends(get_db),
) -> ExamSessionResponse:
    """Create exam room and generate 8-character invitation room code."""
    exam_session = await exam_service.create_exam_session(db, payload)
    return ExamSessionResponse.model_validate(exam_session)


@router.get(
    "/rooms/{room_code}",
    response_model=ExamSessionDetailResponse,
    summary="Get exam room details and student roster",
    description="Fetches room status, problem statement, test cases, and the list of active students for the teacher's live dashboard.",
    tags=["Exam Sessions"],
)
async def get_exam_room(
    room_code: str,
    db: AsyncSession = Depends(get_db),
) -> ExamSessionDetailResponse:
    """Query live exam room details and registered students."""
    exam_session = await exam_service.get_exam_session_by_code(db, room_code, include_students=True)
    return ExamSessionDetailResponse.model_validate(exam_session)


@router.patch(
    "/rooms/{room_code}/close",
    response_model=ExamSessionResponse,
    summary="Conclude and close an exam session",
    description="Marks the exam room as inactive and broadcasts a conclusion notification to all connected clients.",
    tags=["Exam Sessions"],
)
async def close_exam_room(
    room_code: str,
    db: AsyncSession = Depends(get_db),
) -> ExamSessionResponse:
    """Close an active exam session."""
    closed_session = await exam_service.close_exam_session(db, room_code)
    return ExamSessionResponse.model_validate(closed_session)
