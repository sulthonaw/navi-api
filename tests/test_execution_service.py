"""Tests for Sandbox Execution Service."""

import pytest

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
