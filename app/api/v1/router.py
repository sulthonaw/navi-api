"""Aggregated API Router for v1 endpoints."""

from fastapi import APIRouter

from app.api.v1.endpoints import (
    code,
    exam_sessions,
    health,
    hints,
    students,
    violations,
    ws,
)

api_router = APIRouter()

api_router.include_router(health.router)
api_router.include_router(exam_sessions.router)
api_router.include_router(students.router)
api_router.include_router(code.router)
api_router.include_router(hints.router)
api_router.include_router(violations.router)
api_router.include_router(ws.router)
