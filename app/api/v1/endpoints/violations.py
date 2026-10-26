"""API Endpoints for Anti-Cheat Monitoring and Violation Alerts."""

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.schemas.violation import ViolationReportRequest, ViolationReportResponse
from app.services.exam_service import exam_service

router = APIRouter()


@router.post(
    "/violations",
    response_model=ViolationReportResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Report an anti-cheat kiosk violation",
    description="Logged when student kiosk detects window blur, Alt+Tab, or unauthorized keys. Immediately alerts teacher dashboard via WebSockets.",
    tags=["Violations & Anti-Cheat"],
)
async def report_violation(
    payload: ViolationReportRequest,
    db: AsyncSession = Depends(get_db),
) -> ViolationReportResponse:
    """Record violation event and broadcast alarm to teacher dashboard."""
    return await exam_service.log_violation(db, payload)
