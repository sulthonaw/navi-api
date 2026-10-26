"""Tests for Health check and OpenAPI documentation endpoints."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_health_endpoint(client: AsyncClient):
    """Verify health endpoint responds with healthy status and metadata."""
    res = await client.get("/health")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] in ["healthy", "degraded"]
    assert "version" in data
    assert "database_connected" in data


@pytest.mark.asyncio
async def test_openapi_json(client: AsyncClient):
    """Verify OpenAPI 3.1 specification is generated with all expected endpoint tags."""
    res = await client.get("/openapi.json")
    assert res.status_code == 200
    spec = res.json()
    assert spec["openapi"].startswith("3.")
    assert "paths" in spec
    assert "/api/v1/rooms" in spec["paths"]
    assert "/api/v1/students/join" in spec["paths"]
    assert "/api/v1/code/run" in spec["paths"]
    assert "/api/v1/hints/request" in spec["paths"]
    assert "/api/v1/violations" in spec["paths"]


@pytest.mark.asyncio
async def test_export_openapi_endpoint(client: AsyncClient):
    """Verify the /export-openapi endpoint returns full OpenAPI schema."""
    res = await client.get("/export-openapi")
    assert res.status_code == 200
    schema = res.json()
    assert "info" in schema
    assert schema["info"]["title"] == "Navi Exam & Socratic Engine API"
