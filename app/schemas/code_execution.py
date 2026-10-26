"""Pydantic schemas for Code Testing, Sandbox Execution, and Problem Submission."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class CodeRunRequest(BaseModel):
    """Schema for running student code against public test cases for a specific problem."""

    student_id: int = Field(..., description="Student session ID", examples=[1])
    problem_id: int = Field(..., description="Problem challenge ID", examples=[101])
    source_code: str = Field(
        ...,
        description="Python 3 source code written by student",
        examples=[
            "def is_prime(n):\n    if n <= 1:\n        return False\n    for i in range(2, int(n**0.5) + 1):\n        if n % i == 0:\n            return False\n    return True\n\nif __name__ == '__main__':\n    n = int(input())\n    print(is_prime(n))\n"
        ],
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "student_id": 1,
                "problem_id": 101,
                "source_code": "def is_prime(n):\n    return n > 1\n",
            }
        }
    )


class SyntaxErrorDetail(BaseModel):
    """Detailed metadata for Python syntax errors."""

    line_number: int | None = Field(None, examples=[4])
    column_offset: int | None = Field(None, examples=[15])
    error_type: str = Field(..., examples=["SyntaxError"])
    message: str = Field(..., examples=["expected ':'"])
    faulty_line: str | None = Field(None, examples=["    for i in range(2, n)"])


class TestCaseRunResult(BaseModel):
    """Execution result for an individual test case."""

    test_case_id: int | None = None
    is_hidden: bool = False
    passed: bool
    input_data: str | None = None
    expected_output: str | None = None
    actual_output: str | None = None
    error_message: str | None = None
    execution_time_ms: float = Field(..., examples=[12.5])


class CodeRunResponse(BaseModel):
    """Overall outcome of code execution against test cases."""

    success: bool = Field(
        ..., description="Whether all evaluated test cases passed", examples=[True]
    )
    has_syntax_error: bool = Field(False, examples=[False])
    syntax_error_details: SyntaxErrorDetail | None = None
    total_tests: int = Field(..., examples=[2])
    passed_tests: int = Field(..., examples=[2])
    all_passed: bool = Field(..., examples=[True])
    test_results: list[TestCaseRunResult] = []
    stdout: str = Field("", examples=["True\n"])
    stderr: str = Field("", examples=[""])

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "success": True,
                "has_syntax_error": False,
                "syntax_error_details": None,
                "total_tests": 2,
                "passed_tests": 2,
                "all_passed": True,
                "test_results": [
                    {
                        "test_case_id": 1,
                        "is_hidden": False,
                        "passed": True,
                        "input_data": "7\n",
                        "expected_output": "True\n",
                        "actual_output": "True\n",
                        "error_message": None,
                        "execution_time_ms": 15.2,
                    }
                ],
                "stdout": "True\n",
                "stderr": "",
            }
        }
    )


class CodeSubmitRequest(BaseModel):
    """Schema for submitting code solution for a specific problem."""

    student_id: int = Field(..., description="Student session ID", examples=[1])
    problem_id: int = Field(..., description="Problem challenge ID", examples=[101])
    source_code: str = Field(
        ...,
        description="Final Python 3 source code for the problem",
        examples=["def is_prime(n):\n    return n > 1\n"],
    )


class CodeSubmitResponse(BaseModel):
    """Grading verdict for problem submission with points and total accumulated score."""

    student_id: int = Field(..., examples=[1])
    problem_id: int = Field(..., examples=[101])
    is_passed: bool = Field(..., description="Whether all test cases passed", examples=[True])
    points_earned: int = Field(..., description="Points earned for this problem", examples=[20])
    passed_tests: int = Field(..., examples=[5])
    total_tests: int = Field(..., examples=[5])
    status: str = Field(
        ..., description="Submission status (e.g. accepted, wrong_answer)", examples=["accepted"]
    )
    total_score_accumulated: int = Field(
        ..., description="Total points accumulated across all problems", examples=[45]
    )
    score_percentage: float = Field(
        100.0, description="Percentage of test cases passed for this problem", examples=[100.0]
    )
    submitted_at: datetime = Field(..., description="Timestamp of submission")
