"""API Endpoints for Code Sandbox Execution and Final Exam Submission."""

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.schemas.code_execution import (
    CodeRunRequest,
    CodeRunResponse,
    CodeSubmitRequest,
    CodeSubmitResponse,
)
from app.services.exam_service import exam_service

router = APIRouter()


@router.post(
    "/code/run",
    response_model=CodeRunResponse,
    status_code=status.HTTP_200_OK,
    summary="Run code against sample test cases",
    description="Validates Python syntax via native AST, then executes code against sample test cases in an isolated subprocess sandbox.",
    tags=["Code Execution"],
)
async def run_code(
    payload: CodeRunRequest,
    db: AsyncSession = Depends(get_db),
) -> CodeRunResponse:
    """Execute code against public test cases and broadcast status."""
    return await exam_service.run_student_code(db, payload)


@router.post(
    "/code/submit",
    response_model=CodeSubmitResponse,
    status_code=status.HTTP_200_OK,
    summary="Submit final exam solution for grading",
    description="Evaluates student solution against all test cases (both public and hidden), computes score percentage, and marks exam as submitted.",
    tags=["Code Execution"],
)
async def submit_exam_code(
    payload: CodeSubmitRequest,
    db: AsyncSession = Depends(get_db),
) -> CodeSubmitResponse:
    """Grade submission against full test suite."""
    return await exam_service.submit_exam(db, payload)
