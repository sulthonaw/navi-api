"""Pydantic schemas for Exam Sessions and Problems."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.problem import ProblemCreate, ProblemResponse


class ExamSessionCreate(BaseModel):
    """Schema for teacher creating a new multi-problem exam room."""

    title: str = Field(
        ...,
        min_length=3,
        max_length=255,
        description="Exam or session title",
        examples=["Ujian Akhir Semester Pemrograman Dasar"],
    )
    duration_minutes: int = Field(
        90,
        ge=5,
        le=360,
        description="Exam duration in minutes",
        examples=[90],
    )
    hint_quota: int = Field(
        5,
        ge=1,
        le=10,
        description="Default Socratic hint quota per student",
        examples=[5],
    )
    allow_syntax_hints: bool = Field(
        True,
        description="Enable Socratic hints for syntax errors",
        examples=[True],
    )
    allow_logic_hints: bool = Field(
        True,
        description="Enable Socratic hints for runtime/logic errors",
        examples=[True],
    )
    problems: list[ProblemCreate] = Field(
        ...,
        min_length=1,
        description="List of challenge problems in this examination session",
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "title": "Ujian Akhir Semester Pemrograman Dasar",
                "duration_minutes": 90,
                "hint_quota": 5,
                "allow_syntax_hints": True,
                "allow_logic_hints": True,
                "problems": [
                    {
                        "title": "Prime Number Verification",
                        "difficulty": "Easy",
                        "points": 20,
                        "category": "Number Theory",
                        "description": "Write a function named is_prime(n)...",
                        "constraints": ["1 <= n <= 10^6"],
                        "starter_code": "def is_prime(n):\n    pass\n",
                        "test_cases": [
                            {"input_data": "7\n", "expected_output": "True\n", "is_hidden": False},
                            {"input_data": "4\n", "expected_output": "False\n", "is_hidden": True},
                        ],
                    }
                ],
            }
        }
    )


class ExamSessionResponse(BaseModel):
    """Schema for basic exam room details."""

    id: int
    room_code: str = Field(
        ..., description="Unique 8-character room invitation code", examples=["NAVI-8392"]
    )
    title: str
    duration_minutes: int
    started_at: datetime
    expires_at: datetime | None = None
    hint_quota: int
    allow_syntax_hints: bool
    allow_logic_hints: bool
    is_active: bool
    problems: list[ProblemResponse] = []
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class StudentSummary(BaseModel):
    """Summary of a student in the teacher's live dashboard."""

    id: int
    student_name: str
    student_id_number: str
    hints_used: int
    violation_count: int
    total_score: int = 0
    last_status: str
    is_submitted: bool
    started_at: datetime
    submitted_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class ExamSessionDetailResponse(ExamSessionResponse):
    """Full exam room details including active student roster."""

    students: list[StudentSummary] = []

    model_config = ConfigDict(from_attributes=True)
