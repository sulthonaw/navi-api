"""SQLAlchemy models for Exam Sessions and Test Cases."""

from datetime import UTC, datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.problem import Problem
    from app.models.student_session import StudentSession


class ExamSession(Base, TimestampMixin):
    """Exam room created by a teacher."""

    __tablename__ = "exam_sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True, autoincrement=True)
    room_code: Mapped[str] = mapped_column(String(32), unique=True, index=True, nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    duration_minutes: Mapped[int] = mapped_column(Integer, default=90, nullable=False)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )
    expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    hint_quota: Mapped[int] = mapped_column(Integer, default=5, nullable=False)
    allow_syntax_hints: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    allow_logic_hints: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Relationships
    problems: Mapped[list["Problem"]] = relationship(
        "Problem",
        back_populates="exam_session",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    students: Mapped[list["StudentSession"]] = relationship(
        "StudentSession",
        back_populates="exam_session",
        cascade="all, delete-orphan",
        lazy="selectin",
    )


class TestCase(Base, TimestampMixin):
    """Automated test case for problem code verification."""

    __tablename__ = "test_cases"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True, autoincrement=True)
    problem_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("problems.id", ondelete="CASCADE"), nullable=False, index=True
    )
    input_data: Mapped[str] = mapped_column(Text, default="", nullable=False)
    expected_output: Mapped[str] = mapped_column(Text, nullable=False)
    is_hidden: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Relationships
    problem: Mapped["Problem"] = relationship("Problem", back_populates="test_cases")
