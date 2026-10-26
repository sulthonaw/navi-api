"""Application configuration using Pydantic Settings."""

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """System settings and environment variables."""

    PROJECT_NAME: str = "Navi Exam & Socratic Engine API"
    VERSION: str = "1.0.0"
    DESCRIPTION: str = (
        "High-integrity Python examination backend featuring a kiosk-locking environment, "
        "Socratic AI tutoring powered by Google Gemini, native AST syntax validation, "
        "and real-time anti-cheat teacher monitoring."
    )
    API_V1_STR: str = "/api/v1"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    PORT: int = 8000

    # Database
    DATABASE_URL: str = "sqlite+aiosqlite:///./data/navi.db"

    # AI Configuration
    GEMINI_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-2.5-flash"

    # Sandbox & Execution
    EXECUTION_TIMEOUT_SECONDS: float = 5.0
    PISTON_URL: str = ""

    # CORS
    CORS_ORIGINS: list[str] = ["*"]

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: str | list[str]) -> list[str]:
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",")]
        elif isinstance(v, list):
            return v
        return ["*"]

    # OpenAPI Tag Metadata for Swagger UI
    OPENAPI_TAGS: list[dict] = [
        {
            "name": "System & Health",
            "description": "Server health status, database ping, and environment diagnostics.",
        },
        {
            "name": "Exam Sessions",
            "description": "Teacher-managed exam sessions, room code generation, and live room queries.",
        },
        {
            "name": "Student Sessions",
            "description": "Student kiosk login, room verification, and exam initialization.",
        },
        {
            "name": "Code Execution",
            "description": "Python code testing against public test cases and final exam submission.",
        },
        {
            "name": "Socratic AI Engine",
            "description": "Gemini-powered Socratic tutoring with strict code-concealment guardrails.",
        },
        {
            "name": "Violations & Anti-Cheat",
            "description": "Logging of window blur, Alt+Tab, and focus loss events from student kiosks.",
        },
        {
            "name": "WebSockets",
            "description": "Bidirectional real-time event streaming for teachers and students.",
        },
    ]

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=True,
    )


settings = Settings()
