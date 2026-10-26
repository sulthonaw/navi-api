"""Pydantic schemas for Student room access and status."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.problem import PublicProblemResponse


class StudentJoinRequest(BaseModel):
    """Schema for student joining an exam room from the kiosk application."""

    room_code: str = Field(
        ...,
        min_length=4,
        max_length=32,
        description="Exam room invitation code",
        examples=["NAVI-8392"],
    )
    student_name: str = Field(
        ...,
        min_length=2,
        max_length=150,
        description="Full student name",
        examples=["Willy Gregory"],
    )
    student_id_number: str = Field(
        ...,
        min_length=2,
        max_length=100,
        description="Student ID / NIM",
        examples=["215150200111001"],
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "room_code": "NAVI-8392",
                "student_name": "Willy Gregory",
                "student_id_number": "215150200111001",
            }
        }
    )


class StudentJoinResponse(BaseModel):
    """Payload delivered to student kiosk upon successful room entry."""

    student_id: int = Field(..., description="Unique student session ID", examples=[1])
    room_code: str = Field(..., examples=["NAVI-8392"])
    student_name: str = Field(..., examples=["Willy Gregory"])
    student_id_number: str = Field(..., examples=["215150200111001"])
    duration_minutes: int = Field(90, description="Exam duration in minutes", examples=[90])
    expires_at: datetime | None = Field(
        None, description="Absolute expiration timestamp", examples=["2026-10-27T10:30:00Z"]
    )
    hint_quota: int = Field(5, description="Total hint quota", examples=[5])
    hints_used: int = Field(0, description="Hints consumed so far", examples=[0])
    remaining_hints: int = Field(5, description="Remaining hints available", examples=[5])
    allow_syntax_hints: bool = Field(True, examples=[True])
    allow_logic_hints: bool = Field(True, examples=[True])
    problems: list[PublicProblemResponse] = Field(
        default_factory=list, description="List of problems in this exam session"
    )

    model_config = ConfigDict(from_attributes=True)


class StudentStatusResponse(BaseModel):
    """Current live status and progress of a student participant."""

    student_id: int = Field(..., examples=[1])
    student_name: str = Field(..., examples=["Willy Gregory"])
    student_id_number: str = Field(..., examples=["215150200111001"])
    hints_used: int = Field(..., examples=[1])
    violation_count: int = Field(..., examples=[0])
    solved_problem_ids: list[int] = Field(default_factory=list, examples=[[101]])
    in_progress_problem_ids: list[int] = Field(default_factory=list, examples=[[102]])
    total_score: int = Field(0, description="Accumulated score across all problems", examples=[20])
    is_submitted: bool = Field(
        False, description="Whether final exam is finalized", examples=[False]
    )
    time_remaining_seconds: int = Field(
        0, description="Seconds left before expiry", examples=[3420]
    )

    model_config = ConfigDict(from_attributes=True)
