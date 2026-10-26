"""SQLAlchemy models for Examination Problems and Student Problem Submissions."""

from datetime import UTC, datetime
from typing import TYPE_CHECKING

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.exam_session import ExamSession, TestCase
    from app.models.student_session import StudentSession


class Problem(Base, TimestampMixin):
    """Problem challenge within an exam session."""

    __tablename__ = "problems"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True, autoincrement=True)
    exam_session_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("exam_sessions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    difficulty: Mapped[str] = mapped_column(String(50), default="Medium", nullable=False)
    points: Mapped[int] = mapped_column(Integer, default=20, nullable=False)
    category: Mapped[str] = mapped_column(String(100), default="General", nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    constraints: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    starter_code: Mapped[str] = mapped_column(Text, default="", nullable=False)

    # Relationships
    exam_session: Mapped["ExamSession"] = relationship("ExamSession", back_populates="problems")
    test_cases: Mapped[list["TestCase"]] = relationship(
        "TestCase",
        back_populates="problem",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    submissions: Mapped[list["StudentProblemSubmission"]] = relationship(
        "StudentProblemSubmission",
        back_populates="problem",
        cascade="all, delete-orphan",
        lazy="selectin",
    )


class StudentProblemSubmission(Base):
    """Tracks submission and grading status per student per problem."""

    __tablename__ = "student_problem_submissions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True, autoincrement=True)
    student_session_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("student_sessions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    problem_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("problems.id", ondelete="CASCADE"), nullable=False, index=True
    )
    is_passed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    points_earned: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    passed_tests: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_tests: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="in_progress", nullable=False)
    submitted_code: Mapped[str | None] = mapped_column(Text, nullable=True)
    submitted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )

    # Relationships
    student_session: Mapped["StudentSession"] = relationship(
        "StudentSession", back_populates="submissions"
    )
    problem: Mapped["Problem"] = relationship("Problem", back_populates="submissions")
