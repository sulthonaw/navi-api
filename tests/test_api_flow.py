"""End-to-End API integration flow test."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_complete_exam_lifecycle(client: AsyncClient):
    """Test full workflow: Create room -> Join -> Syntax error -> Socratic hint -> Run pass -> Violation -> Submit."""
    # 1. Teacher creates exam session with multiple problems
    room_payload = {
        "title": "Python Midterm Exam",
        "description": "Comprehensive evaluation of basic Python programming.",
        "duration_minutes": 60,
        "hint_quota": 3,
        "allow_syntax_hints": True,
        "allow_logic_hints": True,
        "problems": [
            {
                "title": "Prime Number Checker",
                "description": "Read an integer n and print True if n is prime, False otherwise.",
                "category": "Math",
                "difficulty": "Medium",
                "points": 100,
                "constraints": ["1 <= n <= 10^6"],
                "starter_code": "def is_prime(n):\n    pass\n\nif __name__ == '__main__':\n    n = int(input())\n    print(is_prime(n))\n",
                "test_cases": [
                    {"input_data": "5\n", "expected_output": "True\n", "is_hidden": False},
                    {"input_data": "4\n", "expected_output": "False\n", "is_hidden": False},
                    {"input_data": "1\n", "expected_output": "False\n", "is_hidden": True},
                ],
            }
        ],
    }

    create_res = await client.post("/api/v1/rooms", json=room_payload)
    assert create_res.status_code == 201
    room_data = create_res.json()
    room_code = room_data["room_code"]
    assert room_code.startswith("NAVI-")
    assert room_data["duration_minutes"] == 60
    assert len(room_data["problems"]) == 1

    # 2. Student joins exam room
    join_payload = {
        "room_code": room_code,
        "student_name": "Budi Pratama",
        "student_id_number": "13521001",
    }
    join_res = await client.post("/api/v1/students/join", json=join_payload)
    assert join_res.status_code == 200
    student_data = join_res.json()
    student_id = student_data["student_id"]
    assert student_data["hint_quota"] == 3
    assert student_data["remaining_hints"] == 3
    assert student_data["duration_minutes"] == 60
    assert student_data["expires_at"] is not None
    assert len(student_data["problems"]) == 1

    problem = student_data["problems"][0]
    problem_id = problem["id"]
    assert problem["points"] == 100
    assert len(problem["public_test_cases"]) == 2  # Hidden case omitted

    # 3a. Student runs empty code (should fail and not pass test cases)
    run_empty_res = await client.post(
        "/api/v1/code/run",
        json={"student_id": student_id, "problem_id": problem_id, "source_code": "   "},
    )
    assert run_empty_res.status_code == 200
    run_empty_data = run_empty_res.json()
    assert run_empty_data["all_passed"] is False
    assert run_empty_data["success"] is False
    assert run_empty_data["passed_tests"] == 0
    assert "No code submitted" in run_empty_data["stderr"]

    # 3b. Student runs code with a syntax error (missing colon)
    bad_code = "def is_prime(n)\n    return True\n"
    run_bad_res = await client.post(
        "/api/v1/code/run",
        json={"student_id": student_id, "problem_id": problem_id, "source_code": bad_code},
    )
    assert run_bad_res.status_code == 200
    run_bad_data = run_bad_res.json()
    assert run_bad_data["has_syntax_error"] is True
    assert run_bad_data["syntax_error_details"]["line_number"] == 1
    assert len(run_bad_data["all_syntax_errors"]) >= 1

    # 4a. Student requests Socratic Hint for the syntax error (English default)
    hint_payload = {
        "student_id": student_id,
        "problem_id": problem_id,
        "source_code": bad_code,
        "error_type": "SyntaxError",
        "error_message": "expected ':' on line 1",
        "faulty_line_number": 1,
    }
    hint_res = await client.post("/api/v1/hints/request", json=hint_payload)
    assert hint_res.status_code == 200
    hint_data = hint_res.json()
    assert hint_data["hints_used"] == 1
    assert hint_data["remaining_hints"] == 2
    assert hint_data["hint_level"] == 1
    assert "line 1" in hint_data["hint_text"].lower()

    # 4b. Immediate duplicate click spam: should return existing hint without deducting quota
    hint_res_spam = await client.post("/api/v1/hints/request", json=hint_payload)
    assert hint_res_spam.status_code == 200
    hint_data_spam = hint_res_spam.json()
    assert hint_data_spam["hints_used"] == 1  # Still 1, quota protected!
    assert hint_data_spam["remaining_hints"] == 2

    # 5. Student fixes code and runs against sample test cases
    good_code = (
        "def is_prime(n):\n"
        "    if n <= 1:\n"
        "        return False\n"
        "    for i in range(2, int(n**0.5) + 1):\n"
        "        if n % i == 0:\n"
        "            return False\n"
        "    return True\n"
        "\n"
        "if __name__ == '__main__':\n"
        "    n = int(input())\n"
        "    print(is_prime(n))\n"
    )
    run_good_res = await client.post(
        "/api/v1/code/run",
        json={"student_id": student_id, "problem_id": problem_id, "source_code": good_code},
    )
    assert run_good_res.status_code == 200
    run_good_data = run_good_res.json()
    assert run_good_data["has_syntax_error"] is False
    assert run_good_data["all_passed"] is True
    assert run_good_data["passed_tests"] == 2

    # 6. Student attempts Alt+Tab (violation recorded with is_kiosk_active flag)
    violation_payload = {
        "student_id": student_id,
        "event_type": "alt_tab",
        "details": "Lost focus to external application",
        "is_kiosk_active": True,
    }
    violation_res = await client.post("/api/v1/violations", json=violation_payload)
    assert violation_res.status_code == 201
    violation_data = violation_res.json()
    assert violation_data["violation_count"] == 1

    # 7. Student submits final answer for the problem
    submit_res = await client.post(
        "/api/v1/code/submit",
        json={"student_id": student_id, "problem_id": problem_id, "source_code": good_code},
    )
    assert submit_res.status_code == 200
    submit_data = submit_res.json()
    assert submit_data["status"] == "accepted"
    assert submit_data["is_passed"] is True
    assert submit_data["points_earned"] == 100
    assert submit_data["total_score_accumulated"] == 100
    assert submit_data["score_percentage"] == 100.0
    assert submit_data["passed_tests"] == 3  # All 3 cases passed, including hidden

    # 8. Check student status sync endpoint
    status_res = await client.get(f"/api/v1/students/{student_id}")
    assert status_res.status_code == 200
    status_data = status_res.json()
    assert problem_id in status_data["solved_problem_ids"]
    assert status_data["total_score"] == 100
    assert status_data["time_remaining_seconds"] is not None
    assert status_data["time_remaining_seconds"] > 0

    # 9. Teacher views room details and verifies student metrics
    room_detail_res = await client.get(f"/api/v1/rooms/{room_code}")
    assert room_detail_res.status_code == 200
    detail_data = room_detail_res.json()
    assert len(detail_data["students"]) == 1
    student_summary = detail_data["students"][0]
    assert student_summary["hints_used"] == 1
    assert student_summary["violation_count"] == 1
    assert student_summary["is_submitted"] is True
    assert student_summary["total_score"] == 100

    # 10. Teacher closes exam session
    close_res = await client.patch(f"/api/v1/rooms/{room_code}/close")
    assert close_res.status_code == 200
    assert close_res.json()["is_active"] is False
