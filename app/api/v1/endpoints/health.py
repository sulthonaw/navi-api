"""Health check endpoint for Docker container and uptime monitors."""

from fastapi import APIRouter

from app.core.config import settings
from app.core.database import check_db_connection
from app.schemas.health import HealthResponse

router = APIRouter()


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Check server health and database status",
    description="Returns overall health status, version, runtime environment, and database connectivity.",
    tags=["System & Health"],
)
async def check_health() -> HealthResponse:
    """Probe system health and database ping."""
    is_db_ok = await check_db_connection()
    return HealthResponse(
        status="healthy" if is_db_ok else "degraded",
        version=settings.VERSION,
        environment=settings.ENVIRONMENT,
        database_connected=is_db_ok,
    )
