"""API Endpoints for Socratic AI Hint Generation."""

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.schemas.socratic_hint import SocraticHintRequest, SocraticHintResponse
from app.services.exam_service import exam_service

router = APIRouter()


@router.post(
    "/hints/request",
    response_model=SocraticHintResponse,
    status_code=status.HTTP_200_OK,
    summary="Request a Socratic hint for an error",
    description=(
        "Invokes the Google Gemini Socratic tutor engine with strict code-concealment guardrails. "
        "Decrements student's hint quota and returns reflective guiding questions pointing to the specific error line."
    ),
    tags=["Socratic AI Engine"],
)
async def request_socratic_hint(
    payload: SocraticHintRequest,
    db: AsyncSession = Depends(get_db),
) -> SocraticHintResponse:
    """Generate guiding Socratic hint and deduct 1 from remaining quota."""
    return await exam_service.request_socratic_hint(db, payload)
