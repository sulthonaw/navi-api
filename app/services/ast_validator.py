"""Python AST Syntax and Indentation Validator with multi-error detection."""

import ast
from dataclasses import dataclass, field


@dataclass
class ASTValidationResult:
    """Result of an AST parsing check."""

    is_valid: bool
    error_type: str | None = None
    line_number: int | None = None
    column_offset: int | None = None
    message: str | None = None
    faulty_line: str | None = None
    all_errors: list[dict] = field(default_factory=list)


class ASTValidator:
    """Validates Python code syntax using AST parser and fault-tolerant multi-line inspection."""

    @classmethod
    def validate(cls, source_code: str, allow_empty: bool = False) -> ASTValidationResult:
        """Parse source code, detecting primary and all additional syntax/indentation errors."""
        if not source_code or not source_code.strip():
            if allow_empty:
                return ASTValidationResult(is_valid=True)
            return ASTValidationResult(
                is_valid=False,
                error_type="EmptyCodeError",
                line_number=None,
                column_offset=None,
                message="Source code is empty. Please provide Python code to evaluate.",
                faulty_line=None,
                all_errors=[
                    {
                        "line_number": None,
                        "column_offset": None,
                        "error_type": "EmptyCodeError",
                        "message": "Source code is empty.",
                        "faulty_line": None,
                    }
                ],
            )

        # First, run fast native Python AST
        try:
            ast.parse(source_code)
            return ASTValidationResult(is_valid=True)
        except (SyntaxError, IndentationError, TabError) as primary_exc:
            primary_error_type = primary_exc.__class__.__name__
            primary_line_no = primary_exc.lineno
            primary_col_offset = primary_exc.offset
            primary_message = primary_exc.msg or str(primary_exc)

            lines = source_code.splitlines()
            primary_faulty_line = None
            if primary_exc.text:
                primary_faulty_line = primary_exc.text.strip("\r\n")
            elif primary_line_no is not None and 1 <= primary_line_no <= len(lines):
                primary_faulty_line = lines[primary_line_no - 1]

            all_errors = cls._collect_all_errors(
                source_code,
                primary_line_no,
                primary_col_offset,
                primary_error_type,
                primary_message,
                primary_faulty_line,
            )

            return ASTValidationResult(
                is_valid=False,
                error_type=primary_error_type,
                line_number=primary_line_no,
                column_offset=primary_col_offset,
                message=primary_message,
                faulty_line=primary_faulty_line,
                all_errors=all_errors,
            )

    @classmethod
    def _collect_all_errors(
        cls,
        source_code: str,
        first_line_no: int | None,
        first_col: int | None,
        first_type: str,
        first_msg: str,
        first_faulty_line: str | None,
    ) -> list[dict]:
        """Attempt to find all syntax errors using parso or fallback to iterative parsing."""
        errors: list[dict] = []
        lines = source_code.splitlines()

        # Primary error is always first
        first_entry = {
            "line_number": first_line_no,
            "column_offset": first_col,
            "error_type": first_type,
            "message": first_msg,
            "faulty_line": first_faulty_line,
        }
        errors.append(first_entry)
        seen_lines = {first_line_no} if first_line_no else set()

        # Try parso for fault-tolerant multi-line inspection
        try:
            import parso

            grammar = parso.load_grammar()
            module = grammar.parse(source_code)
            parso_errors = list(grammar.iter_errors(module))

            syntax_error_lines = set()
            for err in parso_errors:
                line_no = err.start_pos[0]
                msg = err.message
                # Filter cascade indentation errors right after a syntax error
                if (line_no - 1) in syntax_error_lines and "indent" in msg.lower():
                    continue

                clean_msg = msg
                if clean_msg.startswith("SyntaxError: "):
                    clean_msg = clean_msg[len("SyntaxError: ") :]
                elif clean_msg.startswith("IndentationError: "):
                    clean_msg = clean_msg[len("IndentationError: ") :]

                err_type = "IndentationError" if "indent" in msg.lower() else "SyntaxError"
                syntax_error_lines.add(line_no)

                if line_no not in seen_lines:
                    seen_lines.add(line_no)
                    faulty = lines[line_no - 1] if 1 <= line_no <= len(lines) else None
                    errors.append(
                        {
                            "line_number": line_no,
                            "column_offset": err.start_pos[1],
                            "error_type": err_type,
                            "message": clean_msg,
                            "faulty_line": faulty,
                        }
                    )

            if len(errors) > 1:
                return errors

        except Exception:
            pass

        # Iterative fallback if parso didn't find multiple errors
        temp_lines = list(lines)
        for _ in range(min(len(lines), 8)):
            try:
                ast.parse("\n".join(temp_lines))
                break
            except (SyntaxError, IndentationError, TabError) as next_exc:
                next_line = next_exc.lineno
                if next_line and next_line not in seen_lines:
                    seen_lines.add(next_line)
                    faulty = lines[next_line - 1] if 1 <= next_line <= len(lines) else None
                    errors.append(
                        {
                            "line_number": next_line,
                            "column_offset": next_exc.offset,
                            "error_type": next_exc.__class__.__name__,
                            "message": next_exc.msg or str(next_exc),
                            "faulty_line": faulty,
                        }
                    )
                if next_line and 1 <= next_line <= len(temp_lines):
                    temp_lines[next_line - 1] = "# error_masked"
                else:
                    break

        return errors
