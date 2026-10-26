"""Pydantic schemas for Student room access and status."""

from pydantic import BaseModel, ConfigDict, Field


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
        examples=["Budi Pratama"],
    )
    student_id_number: str = Field(
        ..., min_length=2, max_length=100, description="Student ID / NIM", examples=["13521001"]
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "room_code": "NAVI-8392",
                "student_name": "Budi Pratama",
                "student_id_number": "13521001",
            }
        }
    )


class PublicTestCase(BaseModel):
    """Public sample test case visible to students."""

    id: int
    input_data: str
    expected_output: str

    model_config = ConfigDict(from_attributes=True)


class StudentJoinResponse(BaseModel):
    """Payload delivered to student kiosk upon successful room entry."""

    student_id: int = Field(..., description="Unique student session ID", examples=[1])
    room_code: str = Field(..., examples=["NAVI-8392"])
    title: str = Field(..., examples=["Pengecekan Bilangan Prima"])
    description: str = Field(..., examples=["Buat fungsi yang membaca bilangan prima..."])
    starter_code: str = Field(..., examples=["def is_prime(n):\n    pass\n"])
    hint_quota: int = Field(..., examples=[3])
    hints_used: int = Field(..., examples=[0])
    remaining_hints: int = Field(..., examples=[3])
    allow_syntax_hints: bool = Field(..., examples=[True])
    allow_logic_hints: bool = Field(..., examples=[True])
    public_test_cases: list[PublicTestCase] = []

    model_config = ConfigDict(from_attributes=True)


class StudentStatusResponse(BaseModel):
    """Current live status of a student participant."""

    student_id: int
    student_name: str
    student_id_number: str
    hints_used: int
    violation_count: int
    last_status: str
    is_submitted: bool
    submitted_code: str | None = None

    model_config = ConfigDict(from_attributes=True)
