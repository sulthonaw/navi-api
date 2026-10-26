"""Tests for Sandbox Execution Service."""

import pytest

from app.models.exam_session import TestCase
from app.services.execution_service import CodeExecutionService


@pytest.mark.asyncio
async def test_successful_execution():
    """Verify standard execution and output capture."""
    runner = CodeExecutionService(timeout_seconds=3.0)
    code = "name = input()\nprint(f'Hello {name}')\n"
    res = await runner.execute_snippet(code, stdin_data="Navi\n")
    assert res.returncode == 0
    assert res.stdout.strip() == "Hello Navi"
    assert res.timed_out is False
    assert res.execution_time_ms > 0


@pytest.mark.asyncio
async def test_runtime_error_captured():
    """Verify runtime exception (ZeroDivisionError) is captured in stderr."""
    runner = CodeExecutionService(timeout_seconds=3.0)
    code = "x = 10 / 0\n"
    res = await runner.execute_snippet(code)
    assert res.returncode != 0
    assert "ZeroDivisionError" in res.stderr


@pytest.mark.asyncio
async def test_infinite_loop_timeout():
    """Verify infinite loop is terminated safely without hanging the server."""
    runner = CodeExecutionService(timeout_seconds=1.0)
    code = "while True:\n    pass\n"
    res = await runner.execute_snippet(code, timeout=1.0)
    assert res.timed_out is True
    assert res.returncode == -1
    assert "timed out" in res.stderr


@pytest.mark.asyncio
async def test_empty_code_execution_fails():
    """Verify empty code immediately fails without passing test cases."""
    runner = CodeExecutionService(timeout_seconds=2.0)
    tc = TestCase(id=1, input_data="", expected_output="hello\n", is_hidden=False)
    res = await runner.run_test_cases("   ", [tc])
    assert res.success is False
    assert res.all_passed is False
    assert res.passed_tests == 0
    assert res.total_tests == 1
    assert "No code submitted" in res.stderr


@pytest.mark.asyncio
async def test_zero_test_cases_not_marked_passed():
    """Verify zero test cases scenario never returns all_passed=True."""
    runner = CodeExecutionService(timeout_seconds=2.0)
    res = await runner.run_test_cases("print('hello')", [])
    assert res.success is False
    assert res.all_passed is False
    assert res.passed_tests == 0
    assert res.total_tests == 0


@pytest.mark.asyncio
async def test_multi_syntax_error_details_in_run_test_cases():
    """Verify multi-line syntax errors populate all_syntax_errors in CodeRunResponse."""
    runner = CodeExecutionService(timeout_seconds=2.0)
    bad_code = "def foo()\n    x = 1\ndef bar()\n    y = 2\n"
    tc = TestCase(id=1, input_data="", expected_output="ok\n", is_hidden=False)
    res = await runner.run_test_cases(bad_code, [tc])
    assert res.has_syntax_error is True
    assert res.success is False
    assert len(res.all_syntax_errors) >= 2
    error_lines = [e.line_number for e in res.all_syntax_errors if e.line_number]
    assert 1 in error_lines
    assert 3 in error_lines
