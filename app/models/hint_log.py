"""SQLAlchemy model for Socratic Hint Logs."""

from datetime import UTC, datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.student_session import StudentSession


class HintLog(Base):
    """Log of Socratic hints requested by students."""

    __tablename__ = "hint_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True, autoincrement=True)
    student_session_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("student_sessions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    problem_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    error_type: Mapped[str] = mapped_column(String(100), nullable=False)
    error_message: Mapped[str] = mapped_column(Text, nullable=False)
    faulty_line_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    hint_text: Mapped[str] = mapped_column(Text, nullable=False)
    hint_level: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    engine_used: Mapped[str] = mapped_column(
        String(50), default="heuristic_fallback", nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )

    # Relationships
    student_session: Mapped["StudentSession"] = relationship(
        "StudentSession", back_populates="hint_logs"
    )
