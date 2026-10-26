"""Socratic Hint Engine powered by Google GenAI (Gemini) with strict guardrails and heuristic fallback."""

import logging
import re

from google import genai
from google.genai import types

from app.core.config import settings

logger = logging.getLogger(__name__)

SOCRATIC_SYSTEM_PROMPT = """
You are Navi, an empathetic and pedagogical Socratic coding tutor for students learning Python in a locked exam environment.
Your mission is to guide the student to discover their mistakes independently through critical thinking, without ever revealing the answer.

STRICT PEDAGOGICAL GUARDRAILS:
1. NEVER output direct code solutions, code fixes, replacement snippets, or complete mathematical formulas. Do NOT include markdown code blocks (```python) containing the corrected code.
2. ALWAYS cite the specific line number when provided (e.g., "Perhatikan baris ke-X..." or "Check line X...").
3. ASK GUIDING, REFLECTIVE QUESTIONS that encourage the student to inspect the concept themselves (e.g., "What punctuation mark is required at the end of a loop header?").
4. Keep the tone concise, warm, encouraging, and focused on one specific conceptual step at a time.
5. If language is 'id', respond in clear, natural, and friendly Indonesian. If language is 'en', respond in clear, encouraging English.
"""


class SocraticEngine:
    """Manages Socratic hint generation using Gemini and rule-based heuristics."""

    def __init__(self):
        self.api_key = settings.GEMINI_API_KEY
        self.model_name = settings.GEMINI_MODEL
        self._client: genai.Client | None = None

    def _get_client(self) -> genai.Client | None:
        """Lazy-initialize GenAI client if API key is present."""
        if not self._client and self.api_key:
            try:
                self._client = genai.Client(api_key=self.api_key)
            except Exception as exc:
                logger.warning("Failed to initialize Google GenAI Client: %s", exc)
                self._client = None
        return self._client

    async def generate_hint(
        self,
        source_code: str,
        error_type: str,
        error_message: str,
        faulty_line_number: int | None = None,
        language: str = "id",
        problem_title: str | None = None,
        problem_description: str | None = None,
        problem_constraints: list[str] | None = None,
    ) -> tuple[str, str]:
        """
        Generate a Socratic hint.
        Returns:
            tuple[hint_text: str, engine_used: str]
        """
        client = self._get_client()

        if client:
            try:
                problem_context = ""
                if problem_title:
                    problem_context += f"- Problem Title: {problem_title}\n"
                if problem_description:
                    problem_context += f"- Problem Story: {problem_description}\n"
                if problem_constraints:
                    problem_context += f"- Constraints: {', '.join(problem_constraints)}\n"

                prompt_content = (
                    f"Problem Context:\n{problem_context}\n"
                    f"Student Encountered Error:\n"
                    f"- Error Type: {error_type}\n"
                    f"- Error Message: {error_message}\n"
                    f"- Target Faulty Line: {faulty_line_number if faulty_line_number else 'Not specified'}\n"
                    f"- Preferred Language: {language}\n\n"
                    f"Student Source Code:\n"
                    f"```python\n{source_code}\n```\n\n"
                    f"Provide a brief, single-paragraph Socratic hint guiding the student to reflect on this error. "
                    f"Remember: Do not give the code solution!"
                )

                config = types.GenerateContentConfig(
                    system_instruction=SOCRATIC_SYSTEM_PROMPT,
                    temperature=0.4,
                    max_output_tokens=256,
                )

                response = await client.aio.models.generate_content(
                    model=self.model_name,
                    contents=prompt_content,
                    config=config,
                )

                raw_text = response.text or ""
                sanitized_hint = self._enforce_guardrails(raw_text, faulty_line_number, language)
                if sanitized_hint:
                    return sanitized_hint, "gemini"

            except Exception as exc:
                logger.warning(
                    "Gemini generation failed, falling back to heuristic engine: %s", exc
                )

        # Fallback to deterministic heuristic engine
        fallback_text = self._generate_heuristic_fallback(
            error_type=error_type,
            error_message=error_message,
            faulty_line_number=faulty_line_number,
            language=language,
        )
        return fallback_text, "heuristic_fallback"

    def _enforce_guardrails(self, text: str, faulty_line_number: int | None, language: str) -> str:
        """Strip markdown code blocks or solution code if Gemini accidentally generates code."""
        # Remove any full code blocks ```...```
        cleaned = re.sub(r"```[a-zA-Z0-9]*\n[\s\S]*?```", "", text).strip()
        if not cleaned:
            return self._generate_heuristic_fallback(
                "GeneralError", "", faulty_line_number, language
            )
        return cleaned

    def _generate_heuristic_fallback(
        self,
        error_type: str,
        error_message: str,
        faulty_line_number: int | None,
        language: str = "id",
    ) -> str:
        """Deterministic Socratic hints when offline or without Gemini API key."""
        line_ref_id = f"baris ke-{faulty_line_number}" if faulty_line_number else "baris terkait"
        line_ref_en = f"line {faulty_line_number}" if faulty_line_number else "the affected line"

        err = error_type.lower()
        msg = error_message.lower()

        if "syntax" in err or "expected ':'" in msg:
            if language == "en":
                return (
                    f"Take a close look at {line_ref_en}. "
                    "Did you remember to include the required punctuation (such as a colon ':') "
                    "at the end of the statement or loop header?"
                )
            return (
                f"Coba periksa {line_ref_id} pada struktur kode Anda. "
                "Apakah Anda sudah menyertakan tanda baca yang wajib (seperti tanda titik dua ':') "
                "di akhir baris perulangan atau percabangan sebelum blok baru dimulai?"
            )

        if "indent" in err:
            if language == "en":
                return (
                    f"Check the spacing and indentation on {line_ref_en}. "
                    "Is this line properly aligned with the block it belongs to?"
                )
            return (
                f"Periksa spasi atau indentasi pada {line_ref_id}. "
                "Apakah baris ini sudah sejajar dengan blok kode yang benar, atau ada spasi/tab yang berlebih?"
            )

        if "index" in err:
            if language == "en":
                return (
                    f"Examine {line_ref_en} where a list or string is being accessed. "
                    "What is the total length of the collection at that moment, and what index are you trying to retrieve?"
                )
            return (
                f"Coba periksa {line_ref_id} tempat Anda memanggil elemen list atau teks. "
                "Berapa panjang elemen tersebut saat baris ini dijalankan, dan berapa indeks yang sedang Anda coba akses?"
            )

        if "zero" in err:
            if language == "en":
                return (
                    f"Inspect the division operation on {line_ref_en}. "
                    "Could the denominator variable evaluate to zero under certain inputs?"
                )
            return (
                f"Perhatikan operasi pembagian pada {line_ref_id}. "
                "Apakah ada kemungkinan nilai pembagi bernilai nol saat input tertentu dimasukkan?"
            )

        if "name" in err:
            if language == "en":
                return (
                    f"Review the variable or function name on {line_ref_en}. "
                    "Has it been defined and assigned before this point in your code?"
                )
            return (
                f"Periksa nama variabel atau fungsi pada {line_ref_id}. "
                "Apakah variabel tersebut sudah didefinisikan dan memiliki nilai sebelum baris ini dipanggil?"
            )

        # Default Socratic question
        if language == "en":
            return (
                f"Carefully inspect the logic on {line_ref_en}. "
                "Step through your code step by step with a small test input to see where the behavior diverges from your expectation."
            )
        return (
            f"Perhatikan dengan seksama alur logika pada {line_ref_id}. "
            "Coba telusuri jalannya variabel satu per satu dengan contoh angka kecil untuk melihat di mana nilai mulai tidak sesuai harapan."
        )


socratic_engine = SocraticEngine()
