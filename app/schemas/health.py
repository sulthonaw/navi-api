"""Health check schemas with Swagger documentation examples."""

from pydantic import BaseModel, ConfigDict, Field


class HealthResponse(BaseModel):
    """Schema for server health diagnostic output."""

    status: str = Field(..., description="Overall health status", examples=["healthy"])
    version: str = Field(..., description="Application version", examples=["1.0.0"])
    environment: str = Field(
        ..., description="Active runtime environment", examples=["development"]
    )
    database_connected: bool = Field(..., description="Database connection health", examples=[True])

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "status": "healthy",
                "version": "1.0.0",
                "environment": "development",
                "database_connected": True,
            }
        }
    )
