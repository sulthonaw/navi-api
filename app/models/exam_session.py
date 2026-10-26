from typing import TYPE_CHECKING

from sqlalchemy import Boolean, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.student_session import StudentSession


class ExamSession(Base, TimestampMixin):
    """Exam room created by a teacher."""

    __tablename__ = "exam_sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True, autoincrement=True)
    room_code: Mapped[str] = mapped_column(String(32), unique=True, index=True, nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    starter_code: Mapped[str] = mapped_column(Text, nullable=False, default="")
    hint_quota: Mapped[int] = mapped_column(Integer, default=3, nullable=False)
    allow_syntax_hints: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    allow_logic_hints: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Relationships
    test_cases: Mapped[list["TestCase"]] = relationship(
        "TestCase",
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
    """Automated test case for code verification."""

    __tablename__ = "test_cases"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True, autoincrement=True)
    exam_session_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("exam_sessions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    input_data: Mapped[str] = mapped_column(Text, default="", nullable=False)
    expected_output: Mapped[str] = mapped_column(Text, nullable=False)
    is_hidden: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Relationships
    exam_session: Mapped["ExamSession"] = relationship("ExamSession", back_populates="test_cases")
