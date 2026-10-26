"""Pydantic schemas for Exam Sessions and Test Cases."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class TestCaseBase(BaseModel):
    """Base schema for test cases."""

    input_data: str = Field(
        "", description="Standard input passed to the program", examples=["5\n"]
    )
    expected_output: str = Field(..., description="Expected standard output", examples=["True\n"])
    is_hidden: bool = Field(
        False, description="Whether this test case is hidden from student preview", examples=[False]
    )


class TestCaseCreate(TestCaseBase):
    """Schema for creating a test case."""

    pass


class TestCaseResponse(TestCaseBase):
    """Schema for returning test case details."""

    id: int
    exam_session_id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ExamSessionCreate(BaseModel):
    """Schema for teacher creating a new exam room."""

    title: str = Field(
        ...,
        min_length=3,
        max_length=255,
        description="Exam or problem title",
        examples=["Pengecekan Bilangan Prima (Prime Number Checker)"],
    )
    description: str = Field(
        ...,
        min_length=10,
        description="Detailed problem story and input/output specifications in Markdown",
        examples=[
            "Buat fungsi yang membaca sebuah integer `n` dari standard input, dan mencetak `True` jika bilangan tersebut prima atau `False` jika bukan."
        ],
    )
    starter_code: str = Field(
        "def is_prime(n):\n    # Write your solution here\n    pass\n\nif __name__ == '__main__':\n    n = int(input())\n    print(is_prime(n))\n",
        description="Python starter code template provided to the student",
        examples=[
            "def is_prime(n):\n    # Tulis solusi Anda di sini\n    pass\n\nif __name__ == '__main__':\n    n = int(input())\n    print(is_prime(n))\n"
        ],
    )
    hint_quota: int = Field(
        3, ge=1, le=10, description="Maximum number of Socratic hints permitted", examples=[3]
    )
    allow_syntax_hints: bool = Field(
        True, description="Enable Socratic hints for syntax errors", examples=[True]
    )
    allow_logic_hints: bool = Field(
        True, description="Enable Socratic hints for runtime/logic errors", examples=[True]
    )
    test_cases: list[TestCaseCreate] = Field(
        ...,
        min_length=1,
        description="List of test cases (at least one required)",
        examples=[
            [
                {"input_data": "5\n", "expected_output": "True\n", "is_hidden": False},
                {"input_data": "4\n", "expected_output": "False\n", "is_hidden": False},
                {"input_data": "1\n", "expected_output": "False\n", "is_hidden": True},
            ]
        ],
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "title": "Pengecekan Bilangan Prima (Prime Number Checker)",
                "description": "Buat fungsi yang membaca sebuah integer n dan mencetak True jika prima atau False jika bukan.",
                "starter_code": "def is_prime(n):\n    pass\n\nif __name__ == '__main__':\n    n = int(input())\n    print(is_prime(n))\n",
                "hint_quota": 3,
                "allow_syntax_hints": True,
                "allow_logic_hints": True,
                "test_cases": [
                    {"input_data": "5\n", "expected_output": "True\n", "is_hidden": False},
                    {"input_data": "4\n", "expected_output": "False\n", "is_hidden": False},
                    {"input_data": "1\n", "expected_output": "False\n", "is_hidden": True},
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
    description: str
    starter_code: str
    hint_quota: int
    allow_syntax_hints: bool
    allow_logic_hints: bool
    is_active: bool
    created_at: datetime
    test_cases: list[TestCaseResponse] = []

    model_config = ConfigDict(from_attributes=True)


class StudentSummary(BaseModel):
    """Summary of a student in the teacher's live dashboard."""

    id: int
    student_name: str
    student_id_number: str
    hints_used: int
    violation_count: int
    last_status: str
    is_submitted: bool
    started_at: datetime
    submitted_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class ExamSessionDetailResponse(ExamSessionResponse):
    """Full exam room details including active student roster."""

    students: list[StudentSummary] = []

    model_config = ConfigDict(from_attributes=True)
