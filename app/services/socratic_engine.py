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
2. ALWAYS cite the specific line number when provided (e.g., "Check line X..." or "Perhatikan baris ke-X...").
3. ASK GUIDING, REFLECTIVE QUESTIONS that encourage the student to inspect the concept themselves (e.g., "What punctuation mark is required at the end of a loop header?").
4. Keep the tone concise, warm, encouraging, and focused on one specific conceptual step at a time.
5. Always respond in clear, encouraging English by default. Only respond in Indonesian if preferred language is explicitly set to 'id'.
6. Do NOT repeat previous hints verbatim. Provide progressive depth to help the student advance.
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
        language: str = "en",
        hint_level: int = 1,
        previous_hints: list[str] | None = None,
        problem_title: str | None = None,
        problem_description: str | None = None,
        problem_constraints: list[str] | None = None,
    ) -> tuple[str, str]:
        """
        Generate a Socratic hint with progressive depth.
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

                hint_guideline = {
                    1: "Level 1: Guiding Reflective Question. Prompt the student to inspect the specific syntax or logic error.",
                    2: "Level 2: Conceptual Explanation. Explain the core concept (e.g., scoping, zero-based indexing, compound statement delimiters) without providing code.",
                    3: "Level 3: Structural Pattern. Describe the abstract anatomical pattern of the statement without revealing the specific answer.",
                }.get(hint_level, "Level 1: Guiding Question.")

                prev_hints_context = ""
                if previous_hints:
                    prev_hints_context = (
                        "- Previously given hints to this student (DO NOT REPEAT THESE):\n"
                    )
                    for ph in previous_hints[-3:]:
                        prev_hints_context += f"  * {ph}\n"
                    prev_hints_context += (
                        "Provide a brand new, deeper perspective that builds upon their learning.\n"
                    )

                prompt_content = (
                    f"Problem Context:\n{problem_context}\n"
                    f"Student Encountered Error:\n"
                    f"- Error Type: {error_type}\n"
                    f"- Error Message: {error_message}\n"
                    f"- Target Faulty Line: {faulty_line_number if faulty_line_number else 'Not specified'}\n"
                    f"- Progression Level: {hint_guideline}\n"
                    f"- Preferred Language: {language}\n"
                    f"{prev_hints_context}\n"
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
                sanitized_hint = self._enforce_guardrails(
                    raw_text, faulty_line_number, language, hint_level
                )
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
            hint_level=hint_level,
        )
        return fallback_text, "heuristic_fallback"

    def _enforce_guardrails(
        self,
        text: str,
        faulty_line_number: int | None,
        language: str,
        hint_level: int = 1,
    ) -> str:
        """Strip markdown code blocks or solution code if Gemini accidentally generates code."""
        # Remove any full code blocks ```...```
        cleaned = re.sub(r"```[a-zA-Z0-9]*\n[\s\S]*?```", "", text).strip()
        if not cleaned:
            return self._generate_heuristic_fallback(
                "GeneralError", "", faulty_line_number, language, hint_level
            )
        return cleaned

    def _generate_heuristic_fallback(
        self,
        error_type: str,
        error_message: str,
        faulty_line_number: int | None,
        language: str = "en",
        hint_level: int = 1,
    ) -> str:
        """Deterministic Socratic hints with progressive depth when offline or without Gemini API key."""
        line_ref_id = f"baris ke-{faulty_line_number}" if faulty_line_number else "baris terkait"
        line_ref_en = f"line {faulty_line_number}" if faulty_line_number else "the affected line"

        err = error_type.lower()
        msg = error_message.lower()

        # Syntax / Colon error
        if "syntax" in err or "expected ':'" in msg:
            if language == "id":
                if hint_level == 1:
                    return (
                        f"Coba periksa {line_ref_id} pada struktur kode Anda. "
                        "Apakah Anda sudah menyertakan tanda baca yang wajib (seperti tanda titik dua ':') "
                        "di akhir baris perulangan atau percabangan sebelum blok baru dimulai?"
                    )
                elif hint_level == 2:
                    return (
                        f"Pada bahasa Python, pernyataan majemuk seperti 'def', 'for', 'if', dan 'while' "
                        f"pada {line_ref_id} wajib diakhiri dengan tanda titik dua ':' sebelum blok kode berikutnya."
                    )
                return (
                    f"Perhatikan karakter paling akhir pada {line_ref_id}. "
                    "Format umum setiap kepala pernyataan adalah `pernyataan :`. Pastikan tanda titik dua ada di ujung baris."
                )
            # English (Default)
            if hint_level == 1:
                return (
                    f"Take a close look at {line_ref_en}. "
                    "Did you remember to include the required punctuation (such as a colon ':') "
                    "at the end of the statement or loop header?"
                )
            elif hint_level == 2:
                return (
                    f"In Python, compound statement headers like 'def', 'for', 'while', and 'if' "
                    f"on {line_ref_en} must end with a colon ':' to begin a new indented code block."
                )
            return (
                f"Inspect the very end of {line_ref_en}. "
                "The required structure is `header_statement:`. Ensure the colon is present right before the newline."
            )

        # Indentation error
        if "indent" in err:
            if language == "id":
                if hint_level == 1:
                    return (
                        f"Periksa spasi atau indentasi pada {line_ref_id}. "
                        "Apakah baris ini sudah sejajar dengan blok kode yang benar, atau ada spasi/tab yang berlebih?"
                    )
                elif hint_level == 2:
                    return (
                        f"Python menggunakan indentasi (umumnya 4 spasi) untuk menentukan cakupan blok kode. "
                        f"Baris {line_ref_id} tidak sejajar dengan tingkatan blok induknya."
                    )
                return (
                    f"Lihat baris tepat sebelum {line_ref_id}. Jika baris sebelumnya adalah awal blok (berakhiran ':'), "
                    f"maka {line_ref_id} harus menjorok 4 spasi ke dalam."
                )
            # English (Default)
            if hint_level == 1:
                return (
                    f"Check the spacing and indentation on {line_ref_en}. "
                    "Is this line properly aligned with the block it belongs to?"
                )
            elif hint_level == 2:
                return (
                    f"Python uses consistent indentation (standard 4 spaces) rather than braces to define block scope. "
                    f"Line {line_ref_en} does not match the indentation depth of its surrounding block."
                )
            return (
                f"Inspect the statement immediately preceding {line_ref_en}. If it ended with a colon ':', "
                f"then {line_ref_en} should be indented 4 spaces further than that header line."
            )

        # Index error
        if "index" in err:
            if language == "id":
                if hint_level == 1:
                    return (
                        f"Coba periksa {line_ref_id} tempat Anda memanggil elemen list atau teks. "
                        "Berapa panjang elemen tersebut saat baris ini dijalankan, dan berapa indeks yang sedang Anda coba akses?"
                    )
                elif hint_level == 2:
                    return (
                        "Ingat bahwa indeks Python berbasis nol: jika panjang koleksi adalah N, indeks yang valid "
                        f"adalah dari 0 hingga N-1. Mengakses indeks N pada {line_ref_id} akan memicu IndexError."
                    )
                return (
                    f"Sebelum mengakses indeks pada {line_ref_id}, pastikan nilai indeks yang digunakan "
                    "selalu lebih kecil dari panjang kumpulan data (`len(...)`)."
                )
            # English (Default)
            if hint_level == 1:
                return (
                    f"Examine {line_ref_en} where a list or string is being accessed. "
                    "What is the total length of the collection at that moment, and what index are you trying to retrieve?"
                )
            elif hint_level == 2:
                return (
                    "Remember that Python uses zero-based indexing. For a sequence of length N, "
                    f"valid indices range from 0 to N-1. Accessing index N on {line_ref_en} causes an IndexError."
                )
            return (
                f"Check the boundary conditions before indexing on {line_ref_en}. "
                "Ensure your index variable is strictly less than the length obtained from `len(...)`."
            )

        # Zero division error
        if "zero" in err:
            if language == "id":
                if hint_level == 1:
                    return (
                        f"Perhatikan operasi pembagian pada {line_ref_id}. "
                        "Apakah ada kemungkinan nilai pembagi bernilai nol saat input tertentu dimasukkan?"
                    )
                elif hint_level == 2:
                    return (
                        f"Operasi matematika pembagian dengan nol tidak terdefinisi dan menyebabkan program berhenti. "
                        f"Telusuri bagaimana penyebut di {line_ref_id} dihitung."
                    )
                return (
                    f"Tambahkan pengecekan kondisi sebelum operasi pembagian pada {line_ref_id} "
                    "untuk memastikan penyebut tidak bernilai nol."
                )
            # English (Default)
            if hint_level == 1:
                return (
                    f"Inspect the division operation on {line_ref_en}. "
                    "Could the denominator variable evaluate to zero under certain inputs?"
                )
            elif hint_level == 2:
                return (
                    f"Division by zero is mathematically undefined and crashes the Python runtime. "
                    f"Trace how the divisor variable on {line_ref_en} is computed."
                )
            return (
                f"Consider adding a defensive check before {line_ref_en} "
                "to handle or avoid cases where the denominator becomes zero."
            )

        # Name error
        if "name" in err:
            if language == "id":
                if hint_level == 1:
                    return (
                        f"Periksa nama variabel atau fungsi pada {line_ref_id}. "
                        "Apakah variabel tersebut sudah didefinisikan dan memiliki nilai sebelum baris ini dipanggil?"
                    )
                elif hint_level == 2:
                    return (
                        f"Python mengeksekusi kode dari atas ke bawah. Variabel pada {line_ref_id} harus "
                        "didefinisikan dan diberi nilai terlebih dahulu sebelum dibaca."
                    )
                return f"Periksa penulisan huruf besar/kecil (case sensitivity) atau ejaan nama variabel pada {line_ref_id}."
            # English (Default)
            if hint_level == 1:
                return (
                    f"Review the variable or function name on {line_ref_en}. "
                    "Has it been defined and assigned before this point in your code?"
                )
            elif hint_level == 2:
                return (
                    f"Python executes sequentially. The identifier on {line_ref_en} must be declared "
                    "and assigned in the current scope prior to being evaluated."
                )
            return (
                f"Double-check for typos, case-sensitivity differences, or out-of-scope declarations "
                f"concerning the identifier on {line_ref_en}."
            )

        # Default Socratic question / General Error
        if language == "id":
            if hint_level == 1:
                return (
                    f"Perhatikan dengan seksama alur logika pada {line_ref_id}. "
                    "Coba telusuri jalannya variabel satu per satu dengan contoh angka kecil untuk melihat di mana nilai mulai tidak sesuai harapan."
                )
            elif hint_level == 2:
                return (
                    f"Bandingkan hasil kalkulasi pada {line_ref_id} dengan deskripsi soal. "
                    "Periksa apakah ada kasus batas (edge cases) seperti input 0, angka negatif, atau list kosong yang belum ditangani."
                )
            return (
                f"Uji coba alur percabangan dan perulangan di sekitar {line_ref_id} secara manual "
                "untuk memastikan setiap kondisi menghasilkan output yang benar."
            )

        # English (Default)
        if hint_level == 1:
            return (
                f"Carefully inspect the logic on {line_ref_en}. "
                "Step through your code step by step with a small test input to see where the behavior diverges from your expectation."
            )
        elif hint_level == 2:
            return (
                f"Compare the computation on {line_ref_en} against the problem constraints. "
                "Check whether edge cases such as empty collections, zero, or boundary inputs are properly addressed."
            )
        return (
            f"Trace your conditional expressions and loop bounds around {line_ref_en} manually. "
            "Verify whether comparison operators (like '<' vs '<=') accurately reflect the problem requirements."
        )


socratic_engine = SocraticEngine()
