"""Database connection management and session factory using SQLAlchemy 2.0 Async."""

from collections.abc import AsyncGenerator
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import settings
from app.models.base import Base


def get_database_url() -> str:
    """Return database URL and ensure required directories exist if using SQLite."""
    url = settings.DATABASE_URL
    if url.startswith("sqlite"):
        # Ensure directory for sqlite file exists
        if "///" in url:
            db_path = url.split("///")[-1]
            if db_path != ":memory:":
                parent = Path(db_path).parent
                if parent and not parent.exists():
                    parent.mkdir(parents=True, exist_ok=True)
    return url


# Create Async Engine
db_url = get_database_url()
engine = create_async_engine(
    db_url,
    echo=False,
    future=True,
    pool_pre_ping=True,
)

# Async Session Factory
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency that yields an async database session."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db() -> None:
    """Initialize database tables."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def check_db_connection() -> bool:
    """Ping database to verify connectivity."""
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        return True
    except Exception:
        return False
