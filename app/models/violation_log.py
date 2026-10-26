"""SQLAlchemy model for Anti-Cheat Violation Logs."""

from datetime import UTC, datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.student_session import StudentSession


class ViolationLog(Base):
    """Log of anti-cheat violations reported by student kiosk clients."""

    __tablename__ = "violation_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True, autoincrement=True)
    student_session_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("student_sessions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    event_type: Mapped[str] = mapped_column(String(50), nullable=False)
    is_kiosk_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    details: Mapped[str | None] = mapped_column(Text, nullable=True)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )

    # Relationships
    student_session: Mapped["StudentSession"] = relationship(
        "StudentSession", back_populates="violations"
    )
