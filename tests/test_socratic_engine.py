"""Tests for Socratic Hint Engine guardrails, progressive levels, and fallback modes."""

import pytest

from app.services.socratic_engine import SocraticEngine


@pytest.mark.asyncio
async def test_heuristic_fallback_english_default():
    """Verify fallback engine defaults to English and cites the line number."""
    engine = SocraticEngine()
    hint_text, engine_used = await engine.generate_hint(
        source_code="for i in range(10)\n    pass\n",
        error_type="SyntaxError",
        error_message="expected ':'",
        faulty_line_number=1,
    )
    assert engine_used in ["gemini", "heuristic_fallback"]
    assert "line 1" in hint_text.lower()
    assert "colon" in hint_text.lower() or "punctuation" in hint_text.lower()
    # Ensure NO direct code block was produced
    assert "```" not in hint_text


@pytest.mark.asyncio
async def test_heuristic_fallback_indonesian_explicit():
    """Verify fallback engine generates Indonesian when language='id' is explicitly requested."""
    engine = SocraticEngine()
    hint_text, _ = await engine.generate_hint(
        source_code="for i in range(10)\n    pass\n",
        error_type="SyntaxError",
        error_message="expected ':'",
        faulty_line_number=1,
        language="id",
    )
    assert "baris ke-1" in hint_text.lower()
    assert "titik dua" in hint_text.lower()


@pytest.mark.asyncio
async def test_progressive_hint_levels_differ():
    """Verify level 1, 2, and 3 hints provide progressive non-repeating depth."""
    engine = SocraticEngine()
    h1, _ = await engine.generate_hint(
        source_code="def foo()\n    pass\n",
        error_type="SyntaxError",
        error_message="expected ':'",
        faulty_line_number=1,
        hint_level=1,
    )
    h2, _ = await engine.generate_hint(
        source_code="def foo()\n    pass\n",
        error_type="SyntaxError",
        error_message="expected ':'",
        faulty_line_number=1,
        hint_level=2,
    )
    h3, _ = await engine.generate_hint(
        source_code="def foo()\n    pass\n",
        error_type="SyntaxError",
        error_message="expected ':'",
        faulty_line_number=1,
        hint_level=3,
    )
    assert h1 != h2
    assert h2 != h3
    assert h1 != h3


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
