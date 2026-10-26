"""SQLAlchemy model for Student Exam Sessions."""

from datetime import UTC, datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.exam_session import ExamSession
    from app.models.violation_log import ViolationLog


class StudentSession(Base, TimestampMixin):
    """Student participant taking an exam in a room."""

    __tablename__ = "student_sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True, autoincrement=True)
    exam_session_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("exam_sessions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    student_name: Mapped[str] = mapped_column(String(150), nullable=False)
    student_id_number: Mapped[str] = mapped_column(String(100), nullable=False)
    hints_used: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    violation_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    last_status: Mapped[str] = mapped_column(String(50), default="in_progress", nullable=False)
    submitted_code: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_submitted: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )
    submitted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # Relationships
    exam_session: Mapped["ExamSession"] = relationship("ExamSession", back_populates="students")
    violations: Mapped[list["ViolationLog"]] = relationship(
        "ViolationLog",
        back_populates="student_session",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
