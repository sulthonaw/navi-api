"""Sandboxed Code Execution Service supporting local subprocess and Piston API."""

import asyncio
import os
import sys
import tempfile
import time
from dataclasses import dataclass

import httpx

from app.core.config import settings
from app.models.exam_session import TestCase
from app.schemas.code_execution import (
    CodeRunResponse,
    SyntaxErrorDetail,
    TestCaseRunResult,
)
from app.services.ast_validator import ASTValidator


@dataclass
class RawExecutionOutput:
    """Raw output from running a Python script."""

    stdout: str
    stderr: str
    returncode: int
    execution_time_ms: float
    timed_out: bool = False


class CodeExecutionService:
    """Executes Python code in an isolated environment against test cases."""

    def __init__(self, timeout_seconds: float | None = None, piston_url: str | None = None):
        self.timeout_seconds = timeout_seconds or settings.EXECUTION_TIMEOUT_SECONDS
        self.piston_url = piston_url or settings.PISTON_URL

    async def execute_snippet(
        self,
        source_code: str,
        stdin_data: str = "",
        timeout: float | None = None,
    ) -> RawExecutionOutput:
        """Execute Python source code using isolated subprocess or Piston."""
        if self.piston_url:
            return await self._execute_piston(source_code, stdin_data)
        return await self._execute_subprocess(source_code, stdin_data, timeout)

    async def _execute_subprocess(
        self,
        source_code: str,
        stdin_data: str = "",
        timeout: float | None = None,
    ) -> RawExecutionOutput:
        """Execute code locally via an asynchronous subprocess."""
        timeout_limit = timeout or self.timeout_seconds
        start_time = time.perf_counter()

        # Write to temporary file with utf-8 encoding
        with tempfile.NamedTemporaryFile(
            mode="w",
            suffix=".py",
            delete=False,
            encoding="utf-8",
        ) as tmp_file:
            tmp_path = tmp_file.name
            tmp_file.write(source_code)

        proc = None
        try:
            # Run using the current python executable with isolated environment
            proc = await asyncio.create_subprocess_exec(
                sys.executable,
                "-u",  # Unbuffered stdout/stderr
                tmp_path,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            stdin_bytes = stdin_data.encode("utf-8") if stdin_data else b""
            stdout_data, stderr_data = await asyncio.wait_for(
                proc.communicate(input=stdin_bytes),
                timeout=timeout_limit,
            )

            elapsed_ms = (time.perf_counter() - start_time) * 1000.0
            return RawExecutionOutput(
                stdout=stdout_data.decode("utf-8", errors="replace"),
                stderr=stderr_data.decode("utf-8", errors="replace"),
                returncode=proc.returncode if proc.returncode is not None else 0,
                execution_time_ms=round(elapsed_ms, 2),
                timed_out=False,
            )

        except TimeoutError:
            if proc:
                try:
                    proc.kill()
                    await proc.wait()
                except Exception:
                    pass
            elapsed_ms = (time.perf_counter() - start_time) * 1000.0
            return RawExecutionOutput(
                stdout="",
                stderr=f"Execution timed out after {timeout_limit} seconds (possible infinite loop).",
                returncode=-1,
                execution_time_ms=round(elapsed_ms, 2),
                timed_out=True,
            )

        finally:
            if os.path.exists(tmp_path):
                try:
                    os.remove(tmp_path)
                except Exception:
                    pass

    async def _execute_piston(self, source_code: str, stdin_data: str) -> RawExecutionOutput:
        """Execute code via external Piston API instance."""
        start_time = time.perf_counter()
        payload = {
            "language": "python",
            "version": "*",
            "files": [{"name": "solution.py", "content": source_code}],
            "stdin": stdin_data,
        }

        try:
            async with httpx.AsyncClient(timeout=self.timeout_seconds + 3.0) as client:
                res = await client.post(
                    f"{self.piston_url.rstrip('/')}/api/v2/execute", json=payload
                )
                elapsed_ms = (time.perf_counter() - start_time) * 1000.0
                if res.status_code == 200:
                    data = res.json().get("run", {})
                    return RawExecutionOutput(
                        stdout=data.get("stdout", ""),
                        stderr=data.get("stderr", ""),
                        returncode=data.get("code", 0),
                        execution_time_ms=round(elapsed_ms, 2),
                    )
                else:
                    return RawExecutionOutput(
                        stdout="",
                        stderr=f"Piston API returned HTTP {res.status_code}: {res.text}",
                        returncode=-1,
                        execution_time_ms=round(elapsed_ms, 2),
                    )
        except Exception as exc:
            elapsed_ms = (time.perf_counter() - start_time) * 1000.0
            return RawExecutionOutput(
                stdout="",
                stderr=f"Failed to communicate with Piston API: {str(exc)}",
                returncode=-1,
                execution_time_ms=round(elapsed_ms, 2),
            )

    async def run_test_cases(
        self,
        source_code: str,
        test_cases: list[TestCase],
        include_hidden: bool = False,
    ) -> CodeRunResponse:
        """Run AST validation, then execute test cases against the source code."""
        # Step 1: In-process AST syntax validation
        ast_result = ASTValidator.validate(source_code)
        if not ast_result.is_valid:
            syntax_detail = SyntaxErrorDetail(
                line_number=ast_result.line_number,
                column_offset=ast_result.column_offset,
                error_type=ast_result.error_type or "SyntaxError",
                message=ast_result.message or "Syntax Error",
                faulty_line=ast_result.faulty_line,
            )
            return CodeRunResponse(
                success=False,
                has_syntax_error=True,
                syntax_error_details=syntax_detail,
                total_tests=len(test_cases),
                passed_tests=0,
                all_passed=False,
                test_results=[],
                stdout="",
                stderr=f"{ast_result.error_type}: {ast_result.message} on line {ast_result.line_number}",
            )

        # Step 2: Execute test cases
        target_cases = (
            test_cases if include_hidden else [tc for tc in test_cases if not tc.is_hidden]
        )
        results: list[TestCaseRunResult] = []
        passed_count = 0
        overall_stdout = []
        overall_stderr = []

        for tc in target_cases:
            run_output = await self.execute_snippet(source_code, stdin_data=tc.input_data)
            normalized_actual = run_output.stdout.replace("\r\n", "\n").strip()
            normalized_expected = tc.expected_output.replace("\r\n", "\n").strip()

            is_pass = (run_output.returncode == 0) and (normalized_actual == normalized_expected)
            if is_pass:
                passed_count += 1

            if run_output.stdout:
                overall_stdout.append(run_output.stdout)
            if run_output.stderr:
                overall_stderr.append(run_output.stderr)

            # If hidden test case, mask expected/actual outputs for student security
            actual_display = normalized_actual if not tc.is_hidden else "[HIDDEN]"
            expected_display = normalized_expected if not tc.is_hidden else "[HIDDEN]"
            input_display = tc.input_data if not tc.is_hidden else "[HIDDEN]"

            results.append(
                TestCaseRunResult(
                    test_case_id=tc.id,
                    is_hidden=tc.is_hidden,
                    passed=is_pass,
                    input_data=input_display,
                    expected_output=expected_display,
                    actual_output=actual_display,
                    error_message=run_output.stderr if run_output.stderr else None,
                    execution_time_ms=run_output.execution_time_ms,
                )
            )

        total_tested = len(target_cases)
        all_passed = (passed_count == total_tested) and total_tested > 0

        return CodeRunResponse(
            success=all_passed,
            has_syntax_error=False,
            syntax_error_details=None,
            total_tests=total_tested,
            passed_tests=passed_count,
            all_passed=all_passed,
            test_results=results,
            stdout="".join(overall_stdout),
            stderr="".join(overall_stderr),
        )


execution_service = CodeExecutionService()
