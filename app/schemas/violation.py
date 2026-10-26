"""Pydantic schemas for Anti-Cheat violation monitoring and alerts."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ViolationReportRequest(BaseModel):
    """Schema for student kiosk reporting focus loss or Alt+Tab attempt."""

    student_id: int = Field(..., description="Student session ID", examples=[1])
    event_type: str = Field(
        ...,
        description="Type of violation: alt_tab, window_blur, devtools_opened, etc.",
        examples=["alt_tab"],
    )
    is_kiosk_active: bool = Field(
        True,
        description="Whether the kiosk low-level keyboard/window hook is currently active",
        examples=[True],
    )
    details: str | None = Field(
        None,
        description="Optional diagnostic context from the desktop kiosk client",
        examples=["Student pressed Alt+Tab or switched active application window"],
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "student_id": 1,
                "event_type": "alt_tab",
                "details": "Student pressed Alt+Tab or switched active application window",
            }
        }
    )


class ViolationReportResponse(BaseModel):
    """Acknowledgement of logged violation."""

    violation_count: int = Field(
        ..., description="Accumulated violation count for this student", examples=[1]
    )
    event_type: str = Field(..., examples=["alt_tab"])
    timestamp: datetime
    message: str = Field(..., examples=["Violation recorded and broadcasted to teacher dashboard."])

    model_config = ConfigDict(from_attributes=True)


class ViolationLogResponse(BaseModel):
    """Full detail of a violation entry in the audit log."""

    id: int
    student_session_id: int
    event_type: str
    details: str | None = None
    timestamp: datetime

    model_config = ConfigDict(from_attributes=True)
