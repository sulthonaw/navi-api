"""Tests for Python AST syntax parsing and line detection."""

from app.services.ast_validator import ASTValidator


def test_valid_python_code():
    """Valid Python code should pass AST check."""
    code = "def add(a, b):\n    return a + b\n\nprint(add(2, 3))\n"
    res = ASTValidator.validate(code)
    assert res.is_valid is True
    assert res.error_type is None
    assert res.line_number is None


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
