"""Pydantic schemas for Socratic Hint generation powered by Google Gemini."""

from pydantic import BaseModel, ConfigDict, Field


class SocraticHintRequest(BaseModel):
    """Schema for student requesting a Socratic hint on code errors."""

    student_id: int = Field(..., description="Student session ID", examples=[1])
    problem_id: int | None = Field(None, description="Target problem ID", examples=[101])
    source_code: str = Field(
        ...,
        description="Current Python source code with the encountered issue",
        examples=[
            "def is_prime(n):\n    for i in range(2, n)\n        if n % i == 0:\n            return False\n    return True\n"
        ],
    )
    error_type: str = Field(
        ...,
        description="Category of error: SyntaxError, IndentationError, IndexError, ZeroDivisionError, WrongAnswer, etc.",
        examples=["SyntaxError"],
    )
    error_message: str = Field(
        ...,
        description="Raw error output or exception trace",
        examples=["expected ':' on line 2"],
    )
    faulty_line_number: int | None = Field(
        None,
        description="Target line number detected by AST or traceback",
        examples=[2],
    )
    language: str = Field(
        "en",
        description="Target language for guidance: 'en' (English, default) or 'id' (Indonesian)",
        examples=["en"],
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "student_id": 1,
                "problem_id": 101,
                "source_code": "def is_prime(n):\n    for i in range(2, n)\n        if n % i == 0:\n            return False\n    return True\n",
                "error_type": "SyntaxError",
                "error_message": "expected ':' on line 2",
                "faulty_line_number": 2,
                "language": "en",
            }
        }
    )


class SocraticHintResponse(BaseModel):
    """Socratic hint response delivered to the student kiosk."""

    hint_text: str = Field(
        ...,
        description="Guiding reflective question that nudges the student without revealing the solution",
        examples=[
            "Check line 2 in your 'for' loop structure. What punctuation is required at the end of the line before starting a new block?"
        ],
    )
    target_line_number: int | None = Field(None, examples=[2])
    hint_level: int = Field(
        1,
        description="Progression level of the hint (1: Guiding Question, 2: Conceptual Explanation, 3: Structural Example)",
        examples=[1],
    )
    hints_used: int = Field(..., examples=[1])
    remaining_hints: int = Field(..., examples=[2])
    total_quota: int = Field(..., examples=[3])
    engine_used: str = Field(..., examples=["gemini"])

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "hint_text": "Check line 2 in your 'for' loop structure. What punctuation is required at the end of the line before starting a new block?",
                "target_line_number": 2,
                "hint_level": 1,
                "hints_used": 1,
                "remaining_hints": 2,
                "total_quota": 3,
                "engine_used": "gemini",
            }
        }
    )
