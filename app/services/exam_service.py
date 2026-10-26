"""Business logic service for Exam Sessions, Students, Hints, and Violations."""

import random
import string
from datetime import UTC, datetime

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.exam_session import ExamSession, TestCase
from app.models.student_session import StudentSession
from app.models.violation_log import ViolationLog
from app.schemas.code_execution import (
    CodeRunRequest,
    CodeRunResponse,
    CodeSubmitRequest,
    CodeSubmitResponse,
)
from app.schemas.exam_session import ExamSessionCreate
from app.schemas.socratic_hint import SocraticHintRequest, SocraticHintResponse
from app.schemas.student import StudentJoinRequest, StudentJoinResponse
from app.schemas.violation import ViolationReportRequest, ViolationReportResponse
from app.services.execution_service import execution_service
from app.services.socratic_engine import socratic_engine
from app.services.websocket_manager import websocket_manager


class ExamService:
    """Coordinates exam business workflows and persistence."""

    @staticmethod
    def _generate_room_code() -> str:
        """Generate a random 4-character suffix for room code e.g. NAVI-8392."""
        chars = string.digits + string.ascii_uppercase
        suffix = "".join(random.choices(chars, k=4))
        return f"NAVI-{suffix}"

    async def create_exam_session(
        self,
        db: AsyncSession,
        payload: ExamSessionCreate,
    ) -> ExamSession:
        """Create a new exam room with test cases and a unique room code."""
        # Ensure room code uniqueness
        room_code = self._generate_room_code()
        while True:
            existing = await db.scalar(
                select(ExamSession).where(ExamSession.room_code == room_code)
            )
            if not existing:
                break
            room_code = self._generate_room_code()

        exam_session = ExamSession(
            room_code=room_code,
            title=payload.title,
            description=payload.description,
            starter_code=payload.starter_code,
            hint_quota=payload.hint_quota,
            allow_syntax_hints=payload.allow_syntax_hints,
            allow_logic_hints=payload.allow_logic_hints,
            is_active=True,
        )
        db.add(exam_session)
        await db.flush()

        # Add test cases
        for tc_data in payload.test_cases:
            test_case = TestCase(
                exam_session_id=exam_session.id,
                input_data=tc_data.input_data,
                expected_output=tc_data.expected_output,
                is_hidden=tc_data.is_hidden,
            )
            db.add(test_case)

        await db.commit()
        await db.refresh(exam_session)
        return exam_session

    async def get_exam_session_by_code(
        self,
        db: AsyncSession,
        room_code: str,
        include_students: bool = True,
    ) -> ExamSession:
        """Fetch exam room by its invitation code."""
        query = select(ExamSession).where(ExamSession.room_code == room_code)
        if include_students:
            query = query.options(
                selectinload(ExamSession.students),
                selectinload(ExamSession.test_cases),
            )
        result = await db.execute(query)
        session = result.scalar_one_or_none()

        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Exam room with code '{room_code}' was not found.",
            )
        return session

    async def join_room(
        self,
        db: AsyncSession,
        payload: StudentJoinRequest,
    ) -> StudentJoinResponse:
        """Handle student entering an exam room from kiosk."""
        room = await self.get_exam_session_by_code(db, payload.room_code, include_students=True)

        if not room.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="This exam room is no longer active.",
            )

        # Check if student already enrolled in this session
        existing_student = await db.scalar(
            select(StudentSession).where(
                StudentSession.exam_session_id == room.id,
                StudentSession.student_id_number == payload.student_id_number,
            )
        )

        if existing_student:
            student = existing_student
        else:
            student = StudentSession(
                exam_session_id=room.id,
                student_name=payload.student_name,
                student_id_number=payload.student_id_number,
                hints_used=0,
                violation_count=0,
                last_status="in_progress",
                is_submitted=False,
            )
            db.add(student)
            await db.commit()
            await db.refresh(student)

            # Broadcast new student arrival to teacher dashboard
            await websocket_manager.broadcast_to_teachers(
                room_code=room.room_code,
                event_type="STUDENT_JOINED",
                data={
                    "student_id": student.id,
                    "student_name": student.student_name,
                    "student_id_number": student.student_id_number,
                    "hints_used": student.hints_used,
                    "violation_count": student.violation_count,
                    "last_status": student.last_status,
                    "started_at": student.started_at.isoformat(),
                },
            )

        public_cases = [tc for tc in room.test_cases if not tc.is_hidden]

        return StudentJoinResponse(
            student_id=student.id,
            room_code=room.room_code,
            title=room.title,
            description=room.description,
            starter_code=room.starter_code,
            hint_quota=room.hint_quota,
            hints_used=student.hints_used,
            remaining_hints=max(0, room.hint_quota - student.hints_used),
            allow_syntax_hints=room.allow_syntax_hints,
            allow_logic_hints=room.allow_logic_hints,
            public_test_cases=public_cases,
        )

    async def run_student_code(
        self,
        db: AsyncSession,
        payload: CodeRunRequest,
    ) -> CodeRunResponse:
        """Run student code against public test cases and broadcast live status."""
        student = await db.get(StudentSession, payload.student_id)
        if not student:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Student session #{payload.student_id} not found.",
            )

        room = await db.get(ExamSession, student.exam_session_id)
        if not room:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Associated exam room not found.",
            )

        # Load public test cases
        result = await db.execute(
            select(TestCase).where(
                TestCase.exam_session_id == room.id,
                TestCase.is_hidden == False,
            )
        )
        test_cases = result.scalars().all()

        run_response = await execution_service.run_test_cases(
            source_code=payload.source_code,
            test_cases=test_cases,
            include_hidden=False,
        )

        # Update student last status
        if run_response.has_syntax_error:
            student.last_status = "syntax_error"
        elif run_response.all_passed:
            student.last_status = "tests_passed"
        elif run_response.passed_tests > 0:
            student.last_status = "partially_passed"
        else:
            student.last_status = "code_error"

        await db.commit()

        # Broadcast live status update to teacher dashboard
        await websocket_manager.broadcast_to_teachers(
            room_code=room.room_code,
            event_type="CODE_STATUS_UPDATED",
            data={
                "student_id": student.id,
                "student_name": student.student_name,
                "last_status": student.last_status,
                "has_syntax_error": run_response.has_syntax_error,
                "passed_tests": run_response.passed_tests,
                "total_tests": run_response.total_tests,
            },
        )

        return run_response

    async def request_socratic_hint(
        self,
        db: AsyncSession,
        payload: SocraticHintRequest,
    ) -> SocraticHintResponse:
        """Provide a Socratic hint while enforcing teacher permissions and quota limits."""
        student = await db.get(StudentSession, payload.student_id)
        if not student:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Student session #{payload.student_id} not found.",
            )

        room = await db.get(ExamSession, student.exam_session_id)
        if not room:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Associated exam room not found.",
            )

        # Verify teacher permission policies
        is_syntax = "syntax" in payload.error_type.lower() or "indent" in payload.error_type.lower()
        if is_syntax and not room.allow_syntax_hints:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Syntax error hints are disabled for this exam session.",
            )
        if not is_syntax and not room.allow_logic_hints:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Logic/Runtime error hints are disabled for this exam session.",
            )

        # Check remaining quota
        remaining = room.hint_quota - student.hints_used
        if remaining <= 0:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Hint quota exhausted! Used {student.hints_used} of {room.hint_quota} hints.",
            )

        # Generate hint using Gemini or heuristic fallback
        hint_text, engine_used = await socratic_engine.generate_hint(
            source_code=payload.source_code,
            error_type=payload.error_type,
            error_message=payload.error_message,
            faulty_line_number=payload.faulty_line_number,
            language=payload.language,
        )

        # Decrement quota
        student.hints_used += 1
        await db.commit()

        new_remaining = max(0, room.hint_quota - student.hints_used)

        # Notify teacher dashboard of hint consumption
        await websocket_manager.broadcast_to_teachers(
            room_code=room.room_code,
            event_type="HINT_REQUESTED",
            data={
                "student_id": student.id,
                "student_name": student.student_name,
                "hints_used": student.hints_used,
                "remaining_hints": new_remaining,
                "error_type": payload.error_type,
                "faulty_line_number": payload.faulty_line_number,
            },
        )

        return SocraticHintResponse(
            hint_text=hint_text,
            target_line_number=payload.faulty_line_number,
            hints_used=student.hints_used,
            remaining_hints=new_remaining,
            total_quota=room.hint_quota,
            engine_used=engine_used,
        )

    async def log_violation(
        self,
        db: AsyncSession,
        payload: ViolationReportRequest,
    ) -> ViolationReportResponse:
        """Record an anti-cheat violation and immediately sound alarm on teacher dashboard."""
        student = await db.get(StudentSession, payload.student_id)
        if not student:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Student session #{payload.student_id} not found.",
            )

        room = await db.get(ExamSession, student.exam_session_id)
        if not room:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Associated exam room not found.",
            )

        # Increment violation counter
        student.violation_count += 1

        # Add violation log entry
        log_entry = ViolationLog(
            student_session_id=student.id,
            event_type=payload.event_type,
            details=payload.details,
            timestamp=datetime.now(UTC),
        )
        db.add(log_entry)
        await db.commit()

        # Real-time WebSocket alarm broadcast to teacher dashboard
        await websocket_manager.broadcast_to_teachers(
            room_code=room.room_code,
            event_type="VIOLATION_DETECTED",
            data={
                "student_id": student.id,
                "student_name": student.student_name,
                "student_id_number": student.student_id_number,
                "event_type": payload.event_type,
                "details": payload.details,
                "violation_count": student.violation_count,
                "timestamp": log_entry.timestamp.isoformat(),
            },
        )

        return ViolationReportResponse(
            violation_count=student.violation_count,
            event_type=payload.event_type,
            timestamp=log_entry.timestamp,
            message="Violation recorded and broadcasted to teacher dashboard.",
        )

    async def submit_exam(
        self,
        db: AsyncSession,
        payload: CodeSubmitRequest,
    ) -> CodeSubmitResponse:
        """Grade student solution against all test cases (public + hidden) and finalize submission."""
        student = await db.get(StudentSession, payload.student_id)
        if not student:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Student session #{payload.student_id} not found.",
            )

        room = await db.get(ExamSession, student.exam_session_id)
        if not room:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Associated exam room not found.",
            )

        # Fetch all test cases
        result = await db.execute(select(TestCase).where(TestCase.exam_session_id == room.id))
        all_cases = result.scalars().all()

        run_response = await execution_service.run_test_cases(
            source_code=payload.source_code,
            test_cases=all_cases,
            include_hidden=True,
        )

        total = len(all_cases)
        passed = run_response.passed_tests
        score = (passed / total * 100.0) if total > 0 else 0.0

        if run_response.has_syntax_error:
            submission_status = "syntax_error"
        elif run_response.all_passed:
            submission_status = "accepted"
        else:
            submission_status = "wrong_answer"

        student.is_submitted = True
        student.submitted_code = payload.source_code
        student.last_status = submission_status
        student.submitted_at = datetime.now(UTC)
        await db.commit()

        # Broadcast submission event to teacher
        await websocket_manager.broadcast_to_teachers(
            room_code=room.room_code,
            event_type="EXAM_SUBMITTED",
            data={
                "student_id": student.id,
                "student_name": student.student_name,
                "score_percentage": round(score, 2),
                "passed_tests": passed,
                "total_tests": total,
                "status": submission_status,
                "submitted_at": student.submitted_at.isoformat(),
            },
        )

        return CodeSubmitResponse(
            student_id=student.id,
            score_percentage=round(score, 2),
            passed_tests=passed,
            total_tests=total,
            status=submission_status,
            submitted_at=student.submitted_at,
        )

    async def close_exam_session(
        self,
        db: AsyncSession,
        room_code: str,
    ) -> ExamSession:
        """Close an exam session, preventing further submissions."""
        room = await self.get_exam_session_by_code(db, room_code, include_students=False)
        room.is_active = False
        await db.commit()

        # Notify room that exam has concluded
        await websocket_manager.broadcast_to_room(
            room_code=room.room_code,
            event_type="EXAM_CLOSED",
            data={"room_code": room.room_code, "is_active": False},
        )
        return room


exam_service = ExamService()
