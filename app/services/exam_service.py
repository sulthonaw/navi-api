"""Business logic service for Exam Sessions, Multi-Problem Challenges, Hints, and Violations."""

import random
import string
from datetime import UTC, datetime, timedelta

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.exam_session import ExamSession, TestCase
from app.models.problem import Problem, StudentProblemSubmission
from app.models.student_session import StudentSession
from app.models.violation_log import ViolationLog
from app.schemas.code_execution import (
    CodeRunRequest,
    CodeRunResponse,
    CodeSubmitRequest,
    CodeSubmitResponse,
)
from app.schemas.exam_session import ExamSessionCreate
from app.schemas.problem import PublicProblemResponse, PublicTestCase
from app.schemas.socratic_hint import SocraticHintRequest, SocraticHintResponse
from app.schemas.student import StudentJoinRequest, StudentJoinResponse, StudentStatusResponse
from app.schemas.violation import ViolationReportRequest, ViolationReportResponse
from app.services.execution_service import execution_service
from app.services.socratic_engine import socratic_engine
from app.services.websocket_manager import websocket_manager


class ExamService:
    """Coordinates multi-problem exam business workflows and persistence."""

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
        """Create a new exam room with multi-problem challenges and timer."""
        room_code = self._generate_room_code()
        while True:
            existing = await db.scalar(
                select(ExamSession).where(ExamSession.room_code == room_code)
            )
            if not existing:
                break
            room_code = self._generate_room_code()

        now = datetime.now(UTC)
        expires_at = now + timedelta(minutes=payload.duration_minutes)

        exam_session = ExamSession(
            room_code=room_code,
            title=payload.title,
            duration_minutes=payload.duration_minutes,
            started_at=now,
            expires_at=expires_at,
            hint_quota=payload.hint_quota,
            allow_syntax_hints=payload.allow_syntax_hints,
            allow_logic_hints=payload.allow_logic_hints,
            is_active=True,
        )
        db.add(exam_session)
        await db.flush()

        # Add problems and their test cases
        for prob_data in payload.problems:
            problem = Problem(
                exam_session_id=exam_session.id,
                title=prob_data.title,
                difficulty=prob_data.difficulty,
                points=prob_data.points,
                category=prob_data.category,
                description=prob_data.description,
                constraints=prob_data.constraints,
                starter_code=prob_data.starter_code,
            )
            db.add(problem)
            await db.flush()

            for tc_data in prob_data.test_cases:
                test_case = TestCase(
                    problem_id=problem.id,
                    input_data=tc_data.input_data,
                    expected_output=tc_data.expected_output,
                    is_hidden=tc_data.is_hidden,
                )
                db.add(test_case)

        await db.commit()
        return await self.get_exam_session_by_code(db, room_code, include_students=False)

    async def get_exam_session_by_code(
        self,
        db: AsyncSession,
        room_code: str,
        include_students: bool = True,
    ) -> ExamSession:
        """Fetch exam room by its invitation code with related problems and test cases."""
        query = select(ExamSession).where(ExamSession.room_code == room_code)
        query = query.options(
            selectinload(ExamSession.problems).selectinload(Problem.test_cases),
        )
        if include_students:
            query = query.options(
                selectinload(ExamSession.students),
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
                total_score=0,
                last_status="in_progress",
                is_submitted=False,
            )
            db.add(student)
            await db.commit()
            await db.refresh(student)

            # Broadcast arrival to teacher dashboard
            await websocket_manager.broadcast_to_teachers(
                room_code=room.room_code,
                event_type="STUDENT_JOINED",
                data={
                    "student_id": student.id,
                    "student_name": student.student_name,
                    "student_id_number": student.student_id_number,
                    "hints_used": student.hints_used,
                    "violation_count": student.violation_count,
                    "total_score": student.total_score,
                    "last_status": student.last_status,
                    "started_at": student.started_at.isoformat(),
                },
            )

        # Build public problems array (excluding hidden test cases)
        public_problems: list[PublicProblemResponse] = []
        for prob in room.problems:
            public_cases = [
                PublicTestCase(
                    id=tc.id,
                    input_data=tc.input_data,
                    expected_output=tc.expected_output,
                )
                for tc in prob.test_cases
                if not tc.is_hidden
            ]
            public_problems.append(
                PublicProblemResponse(
                    id=prob.id,
                    title=prob.title,
                    difficulty=prob.difficulty,
                    points=prob.points,
                    category=prob.category,
                    description=prob.description,
                    constraints=prob.constraints or [],
                    starter_code=prob.starter_code,
                    public_test_cases=public_cases,
                )
            )

        return StudentJoinResponse(
            student_id=student.id,
            room_code=room.room_code,
            student_name=student.student_name,
            student_id_number=student.student_id_number,
            duration_minutes=room.duration_minutes,
            expires_at=room.expires_at,
            hint_quota=room.hint_quota,
            hints_used=student.hints_used,
            remaining_hints=max(0, room.hint_quota - student.hints_used),
            allow_syntax_hints=room.allow_syntax_hints,
            allow_logic_hints=room.allow_logic_hints,
            problems=public_problems,
        )

    async def run_student_code(
        self,
        db: AsyncSession,
        payload: CodeRunRequest,
    ) -> CodeRunResponse:
        """Run student code against public sample test cases for a specific problem."""
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

        # Fetch problem
        problem = await db.get(Problem, payload.problem_id)
        if not problem or problem.exam_session_id != room.id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Problem #{payload.problem_id} not found in this exam session.",
            )

        # Load public test cases for this problem
        result = await db.execute(
            select(TestCase).where(
                TestCase.problem_id == problem.id,
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
                "problem_id": problem.id,
                "student_name": student.student_name,
                "last_status": student.last_status,
                "has_syntax_error": run_response.has_syntax_error,
                "passed_tests": run_response.passed_tests,
                "total_tests": run_response.total_tests,
            },
        )

        return run_response

    async def submit_problem_code(
        self,
        db: AsyncSession,
        payload: CodeSubmitRequest,
    ) -> CodeSubmitResponse:
        """Grade student solution against full test suite for a problem and accumulate score."""
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

        problem = await db.get(Problem, payload.problem_id)
        if not problem or problem.exam_session_id != room.id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Problem #{payload.problem_id} not found in this exam session.",
            )

        # Fetch all test cases for this problem (public + hidden)
        result = await db.execute(select(TestCase).where(TestCase.problem_id == problem.id))
        all_cases = result.scalars().all()

        run_response = await execution_service.run_test_cases(
            source_code=payload.source_code,
            test_cases=all_cases,
            include_hidden=True,
        )

        total = len(all_cases)
        passed = run_response.passed_tests
        is_passed = run_response.all_passed

        if run_response.has_syntax_error:
            submission_status = "syntax_error"
        elif is_passed:
            submission_status = "accepted"
        else:
            submission_status = "wrong_answer"

        points_earned = problem.points if is_passed else 0

        # Upsert problem submission record
        existing_sub = await db.scalar(
            select(StudentProblemSubmission).where(
                StudentProblemSubmission.student_session_id == student.id,
                StudentProblemSubmission.problem_id == problem.id,
            )
        )

        if existing_sub:
            existing_sub.is_passed = is_passed
            existing_sub.points_earned = points_earned
            existing_sub.passed_tests = passed
            existing_sub.total_tests = total
            existing_sub.status = submission_status
            existing_sub.submitted_code = payload.source_code
            existing_sub.submitted_at = datetime.now(UTC)
        else:
            new_sub = StudentProblemSubmission(
                student_session_id=student.id,
                problem_id=problem.id,
                is_passed=is_passed,
                points_earned=points_earned,
                passed_tests=passed,
                total_tests=total,
                status=submission_status,
                submitted_code=payload.source_code,
                submitted_at=datetime.now(UTC),
            )
            db.add(new_sub)

        await db.flush()

        # Recompute total score accumulated across all problems
        total_score_res = await db.scalar(
            select(func.sum(StudentProblemSubmission.points_earned)).where(
                StudentProblemSubmission.student_session_id == student.id
            )
        )
        total_accumulated = int(total_score_res or 0)
        student.total_score = total_accumulated
        student.last_status = submission_status
        student.submitted_at = datetime.now(UTC)

        # Check if all problems in room are solved
        total_problems = await db.scalar(
            select(func.count(Problem.id)).where(Problem.exam_session_id == room.id)
        )
        solved_count = await db.scalar(
            select(func.count(StudentProblemSubmission.id)).where(
                StudentProblemSubmission.student_session_id == student.id,
                StudentProblemSubmission.is_passed == True,
            )
        )
        if total_problems and solved_count and solved_count >= total_problems:
            student.is_submitted = True

        await db.commit()

        # Broadcast submission event to teacher
        await websocket_manager.broadcast_to_teachers(
            room_code=room.room_code,
            event_type="PROBLEM_SUBMITTED",
            data={
                "student_id": student.id,
                "problem_id": problem.id,
                "student_name": student.student_name,
                "is_passed": is_passed,
                "points_earned": points_earned,
                "passed_tests": passed,
                "total_tests": total,
                "status": submission_status,
                "total_score_accumulated": total_accumulated,
                "submitted_at": student.submitted_at.isoformat(),
            },
        )

        score_pct = (passed / total * 100.0) if total > 0 else 0.0

        return CodeSubmitResponse(
            student_id=student.id,
            problem_id=problem.id,
            is_passed=is_passed,
            points_earned=points_earned,
            passed_tests=passed,
            total_tests=total,
            status=submission_status,
            total_score_accumulated=total_accumulated,
            score_percentage=round(score_pct, 2),
            submitted_at=student.submitted_at,
        )

    async def request_socratic_hint(
        self,
        db: AsyncSession,
        payload: SocraticHintRequest,
    ) -> SocraticHintResponse:
        """Provide a Socratic hint with optional problem-specific context."""
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

        remaining = room.hint_quota - student.hints_used
        if remaining <= 0:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Hint quota exhausted! Used {student.hints_used} of {room.hint_quota} hints.",
            )

        problem_title = None
        problem_description = None
        problem_constraints = None
        if payload.problem_id:
            problem = await db.get(Problem, payload.problem_id)
            if problem:
                problem_title = problem.title
                problem_description = problem.description
                problem_constraints = problem.constraints

        # Generate hint using Gemini or heuristic fallback
        hint_text, engine_used = await socratic_engine.generate_hint(
            source_code=payload.source_code,
            error_type=payload.error_type,
            error_message=payload.error_message,
            faulty_line_number=payload.faulty_line_number,
            language=payload.language,
            problem_title=problem_title,
            problem_description=problem_description,
            problem_constraints=problem_constraints,
        )

        student.hints_used += 1
        await db.commit()

        new_remaining = max(0, room.hint_quota - student.hints_used)

        await websocket_manager.broadcast_to_teachers(
            room_code=room.room_code,
            event_type="HINT_REQUESTED",
            data={
                "student_id": student.id,
                "problem_id": payload.problem_id,
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
        """Record an anti-cheat violation including kiosk hook status and sound alarm."""
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

        student.violation_count += 1

        log_entry = ViolationLog(
            student_session_id=student.id,
            event_type=payload.event_type,
            is_kiosk_active=payload.is_kiosk_active,
            details=payload.details,
            timestamp=datetime.now(UTC),
        )
        db.add(log_entry)
        await db.commit()

        await websocket_manager.broadcast_to_teachers(
            room_code=room.room_code,
            event_type="VIOLATION_DETECTED",
            data={
                "student_id": student.id,
                "student_name": student.student_name,
                "student_id_number": student.student_id_number,
                "event_type": payload.event_type,
                "is_kiosk_active": payload.is_kiosk_active,
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

    async def get_student_status(
        self,
        db: AsyncSession,
        student_id: int,
    ) -> StudentStatusResponse:
        """Fetch current progress, solved challenges, accumulated score, and time remaining."""
        student = await db.scalar(
            select(StudentSession)
            .where(StudentSession.id == student_id)
            .options(
                selectinload(StudentSession.submissions),
                selectinload(StudentSession.exam_session),
            )
        )
        if not student:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Student #{student_id} not found.",
            )

        room = student.exam_session
        solved_problem_ids = [sub.problem_id for sub in student.submissions if sub.is_passed]
        in_progress_problem_ids = [
            sub.problem_id
            for sub in student.submissions
            if not sub.is_passed and sub.problem_id not in solved_problem_ids
        ]

        now = datetime.now(UTC)
        time_remaining_seconds = 0
        if room and room.expires_at:
            expires_at = room.expires_at
            if expires_at.tzinfo is None:
                expires_at = expires_at.replace(tzinfo=UTC)
            delta = (expires_at - now).total_seconds()
            time_remaining_seconds = max(0, int(delta))

        return StudentStatusResponse(
            student_id=student.id,
            student_name=student.student_name,
            student_id_number=student.student_id_number,
            hints_used=student.hints_used,
            violation_count=student.violation_count,
            solved_problem_ids=solved_problem_ids,
            in_progress_problem_ids=in_progress_problem_ids,
            total_score=student.total_score,
            is_submitted=student.is_submitted,
            time_remaining_seconds=time_remaining_seconds,
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

        await websocket_manager.broadcast_to_room(
            room_code=room.room_code,
            event_type="EXAM_CLOSED",
            data={"room_code": room.room_code, "is_active": False},
        )
        return room


exam_service = ExamService()
