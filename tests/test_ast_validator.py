"""Tests for Python AST syntax parsing and line detection."""

from app.services.ast_validator import ASTValidator


def test_valid_python_code():
    """Valid Python code should pass AST check."""
    code = "def add(a, b):\n    return a + b\n\nprint(add(2, 3))\n"
    res = ASTValidator.validate(code)
    assert res.is_valid is True
    assert res.error_type is None
    assert res.line_number is None


def test_empty_code_invalid_by_default():
    """Empty or whitespace code should be invalid by default."""
    res = ASTValidator.validate("   ")
    assert res.is_valid is False
    assert res.error_type == "EmptyCodeError"


def test_empty_code_allowed_when_flag_set():
    """Empty code should be valid when allow_empty=True."""
    res = ASTValidator.validate("", allow_empty=True)
    assert res.is_valid is True


def test_syntax_error_missing_colon():
    """Code with missing colon should report SyntaxError on the exact line."""
    code = "def is_prime(n)\n    return True\n"
    res = ASTValidator.validate(code)
    assert res.is_valid is False
    assert res.error_type == "SyntaxError"
    assert res.line_number == 1
    assert "def is_prime(n)" in (res.faulty_line or "")


def test_syntax_error_unclosed_parenthesis():
    """Code with unclosed parenthesis should be caught."""
    code = "x = (1 + 2\nprint(x)\n"
    res = ASTValidator.validate(code)
    assert res.is_valid is False
    assert res.error_type == "SyntaxError"
    assert res.line_number is not None


def test_indentation_error():
    """Unexpected indentation should report IndentationError."""
    code = "def hello():\nprint('bad indent')\n"
    res = ASTValidator.validate(code)
    assert res.is_valid is False
    assert res.error_type in ["IndentationError", "SyntaxError"]
    assert res.line_number == 2


def test_multi_line_syntax_errors_detected():
    """Multiple syntax errors on different lines should all be detected."""
    code = (
        "def check_num(n):\n"
        "    if n > 10\n"
        "        return True\n"
        "    for i in range(n)\n"
        "        pass\n"
    )
    res = ASTValidator.validate(code)
    assert res.is_valid is False
    assert len(res.all_errors) >= 2
    detected_lines = [e["line_number"] for e in res.all_errors if e.get("line_number")]
    assert 2 in detected_lines
    assert 4 in detected_lines
