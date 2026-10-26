"""Pydantic schemas for Problems and Test Cases."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class PublicTestCase(BaseModel):
    """Public sample test case exposed to students."""

    id: int = Field(..., description="Test case ID", examples=[1])
    input_data: str = Field(..., description="Standard input data", examples=["7\n"])
    expected_output: str = Field(..., description="Expected output string", examples=["True\n"])

    model_config = ConfigDict(from_attributes=True)


class TestCaseCreate(BaseModel):
    """Schema for creating a test case."""

    input_data: str = Field(
        "", description="Standard input passed to the program", examples=["7\n"]
    )
    expected_output: str = Field(
        ..., min_length=1, description="Expected standard output", examples=["True\n"]
    )
    is_hidden: bool = Field(
        False, description="Whether this test case is hidden from student preview", examples=[False]
    )

    @field_validator("expected_output")
    @classmethod
    def validate_expected_output(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Test case expected_output cannot be empty or only whitespace.")
        return v


class TestCaseResponse(TestCaseCreate):
    """Schema for returning full test case details (for teachers)."""

    id: int
    problem_id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ProblemCreate(BaseModel):
    """Schema for creating a challenge problem within an exam session."""

    title: str = Field(
        ...,
        min_length=3,
        max_length=255,
        description="Problem title",
        examples=["Prime Number Verification"],
    )
    difficulty: Literal["Easy", "Medium", "Hard"] = Field(
        "Easy", description="Problem difficulty tier", examples=["Easy"]
    )
    points: int = Field(20, ge=1, le=100, description="Problem point weight", examples=[20])
    category: str = Field(
        "General", description="Problem topical category", examples=["Number Theory"]
    )
    description: str = Field(
        ...,
        min_length=5,
        description="Problem description in Markdown format",
        examples=["Write a function named is_prime(n) that checks if an integer is prime."],
    )
    constraints: list[str] = Field(
        default_factory=list,
        description="Problem constraints and complexity bounds",
        examples=[["1 <= n <= 10^6", "Function must return a boolean"]],
    )

    @field_validator("constraints", mode="before")
    @classmethod
    def normalize_constraints(cls, v):
        if isinstance(v, str):
            return [v] if v.strip() else []
        return v or []

    starter_code: str = Field(
        "def solution():\n    pass\n",
        description="Python starter code template",
        examples=["def is_prime(n):\n    pass\n"],
    )
    test_cases: list[TestCaseCreate] = Field(
        ...,
        min_length=1,
        description="List of automated test cases",
        examples=[
            [
                {"input_data": "7\n", "expected_output": "True\n", "is_hidden": False},
                {"input_data": "4\n", "expected_output": "False\n", "is_hidden": True},
            ]
        ],
    )


class PublicProblemResponse(BaseModel):
    """Public problem details returned to student kiosks (hidden test cases omitted)."""

    id: int = Field(..., description="Problem ID", examples=[101])
    title: str = Field(..., description="Problem title", examples=["Prime Number Verification"])
    difficulty: str = Field(..., description="Difficulty", examples=["Easy"])
    points: int = Field(..., description="Point value", examples=[20])
    category: str = Field(..., description="Category", examples=["Number Theory"])
    description: str = Field(
        ..., description="Markdown description", examples=["Write a function named is_prime(n)..."]
    )
    constraints: list[str] = Field(
        default_factory=list,
        description="Problem constraints",
        examples=[["1 <= n <= 10^6", "Function must return a boolean"]],
    )
    starter_code: str = Field(
        ..., description="Starter template", examples=["def is_prime(n):\n    pass\n"]
    )
    public_test_cases: list[PublicTestCase] = Field(
        default_factory=list,
        description="Public sample test cases for preview and sandbox testing",
    )

    model_config = ConfigDict(from_attributes=True)


class ProblemResponse(BaseModel):
    """Comprehensive problem details including hidden test cases (for teacher console)."""

    id: int
    exam_session_id: int
    title: str
    difficulty: str
    points: int
    category: str
    description: str
    constraints: list[str]
    starter_code: str
    test_cases: list[TestCaseResponse]
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
