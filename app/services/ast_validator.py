"""Python AST Syntax and Indentation Validator."""

import ast
from dataclasses import dataclass


@dataclass
class ASTValidationResult:
    """Result of an AST parsing check."""

    is_valid: bool
    error_type: str | None = None
    line_number: int | None = None
    column_offset: int | None = None
    message: str | None = None
    faulty_line: str | None = None


class ASTValidator:
    """Validates Python code syntax using the built-in AST parser."""

    @staticmethod
    def validate(source_code: str) -> ASTValidationResult:
        """Parse source code with Python AST and catch syntax/indentation errors."""
        if not source_code or not source_code.strip():
            return ASTValidationResult(is_valid=True)

        try:
            ast.parse(source_code)
            return ASTValidationResult(is_valid=True)
        except (SyntaxError, IndentationError, TabError) as exc:
            error_type = exc.__class__.__name__
            line_no = exc.lineno
            col_offset = exc.offset
            message = exc.msg or str(exc)

            # Extract faulty line from exc.text or source lines
            faulty_line = None
            if exc.text:
                faulty_line = exc.text.strip("\r\n")
            elif line_no is not None:
                lines = source_code.splitlines()
                if 1 <= line_no <= len(lines):
                    faulty_line = lines[line_no - 1]

            return ASTValidationResult(
                is_valid=False,
                error_type=error_type,
                line_number=line_no,
                column_offset=col_offset,
                message=message,
                faulty_line=faulty_line,
            )
