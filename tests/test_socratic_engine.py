"""Tests for Socratic Hint Engine guardrails and fallback modes."""

import pytest

from app.services.socratic_engine import SocraticEngine


@pytest.mark.asyncio
async def test_heuristic_fallback_syntax_error():
    """Verify fallback engine generates appropriate Socratic questions citing the line number."""
    engine = SocraticEngine()
    hint_text, engine_used = await engine.generate_hint(
        source_code="for i in range(10)\n    pass\n",
        error_type="SyntaxError",
        error_message="expected ':'",
        faulty_line_number=1,
        language="id",
    )
    assert engine_used in ["gemini", "heuristic_fallback"]
    assert "baris ke-1" in hint_text.lower()
    # Ensure NO direct code block was produced
    assert "```" not in hint_text


@pytest.mark.asyncio
async def test_guardrail_code_stripping():
    """Verify guardrail strips markdown code blocks if accidentally produced."""
    engine = SocraticEngine()
    bad_output = (
        "Here is the code:\n```python\nfor i in range(10):\n    pass\n```\nWhat do you think?"
    )
    sanitized = engine._enforce_guardrails(bad_output, faulty_line_number=1, language="en")
    assert "```python" not in sanitized
    assert "line 1" in sanitized.lower() or "what do you think?" in sanitized.lower()


@pytest.mark.asyncio
async def test_english_guidance_generation():
    """Verify English language guidance generation."""
    engine = SocraticEngine()
    hint_text, _ = await engine.generate_hint(
        source_code="lst = [1, 2]\nprint(lst[5])\n",
        error_type="IndexError",
        error_message="list index out of range",
        faulty_line_number=2,
        language="en",
    )
    assert "line 2" in hint_text.lower() or "index" in hint_text.lower()
