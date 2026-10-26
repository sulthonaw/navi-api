"""Main application entrypoint and FastAPI factory."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, RedirectResponse

from app.api.v1.router import api_router
from app.core.config import settings
from app.core.database import check_db_connection, init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager to initialize resources."""
    # Ensure database schema is ready
    await init_db()
    yield


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description=settings.DESCRIPTION,
    openapi_tags=settings.OPENAPI_TAGS,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount API v1 router
app.include_router(api_router, prefix=settings.API_V1_STR)


@app.get("/", include_in_schema=False)
async def root_redirect():
    """Redirect root to Swagger documentation."""
    return RedirectResponse(url="/docs")


@app.get(
    "/health",
    tags=["System & Health"],
    summary="Root healthcheck probe",
    description="Top-level health check endpoint for container orchestrators and load balancers.",
)
async def root_health():
    """Quick health probe."""
    is_db_ok = await check_db_connection()
    return {
        "status": "healthy" if is_db_ok else "degraded",
        "service": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "database_connected": is_db_ok,
    }


@app.get(
    "/export-openapi",
    tags=["System & Health"],
    summary="Export raw OpenAPI schema",
    description="Returns the full OpenAPI 3.1 JSON schema for frontend TypeScript client generation.",
)
async def export_openapi_schema():
    """Download raw OpenAPI schema."""
    return JSONResponse(content=app.openapi())
