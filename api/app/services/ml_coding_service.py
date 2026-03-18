"""ML Coding Drills service — Gemini-powered exercise generation and code grading."""

import asyncio
import json
import re
from typing import Optional

import google.generativeai as genai

from app.config import get_settings
from app.models.ml_coding_schemas import MLCodingExerciseGrade

# Dimension weights for overall score computation
DIMENSION_WEIGHTS = {
    "correctness": 3.0,
    "code_quality": 2.0,
    "math_understanding": 3.0,
}
TOTAL_WEIGHT = sum(DIMENSION_WEIGHTS.values())  # 8.0


class MLCodingService:
    """
    Service for generating ML coding exercise variations and grading submitted code.

    Uses Gemini for:
    - Generating specific problem variations from the static problem bank
    - Grading Python code on correctness, code quality, and math understanding
    """

    def __init__(self):
        settings = get_settings()
        if settings.google_api_key:
            genai.configure(api_key=settings.google_api_key)
            self.model = genai.GenerativeModel(settings.gemini_model)
            self.configured = True
        else:
            self.model = None
            self.configured = False

    async def generate_exercise_variation(
        self,
        problem_title: str,
        problem_description: str,
        key_concepts: list[str],
        math_concepts: list[str],
        is_review: bool = False,
        weak_areas: list[str] = None,
    ) -> dict:
        """
        Generate a specific variation/prompt for an ML coding problem.

        Returns dict with: prompt_text, starter_code
        """
        if not self.configured:
            return self._fallback_variation(problem_title, problem_description)

        prompt = self._build_variation_prompt(
            problem_title, problem_description, key_concepts,
            math_concepts, is_review, weak_areas or [],
        )

        try:
            response = await asyncio.to_thread(self.model.generate_content, prompt)
            return self._parse_variation_response(response.text, problem_title, problem_description)
        except Exception as e:
            print(f"Gemini variation generation failed: {e}")
            return self._fallback_variation(problem_title, problem_description)

    async def generate_batch_variations(
        self,
        problems: list[dict],
        weak_areas: list[str] = None,
    ) -> list[dict]:
        """
        Generate variations for multiple problems in a single Gemini call.

        Falls back to one-at-a-time if batch call fails.
        """
        if not self.configured:
            return [
                self._fallback_variation(p["title"], p["description"])
                for p in problems
            ]

        prompt = self._build_batch_variation_prompt(problems, weak_areas or [])

        try:
            response = await asyncio.to_thread(self.model.generate_content, prompt)
            variations = self._parse_batch_variation_response(response.text, problems)
            if variations and len(variations) == len(problems):
                return variations
        except Exception as e:
            print(f"Gemini batch variation generation failed: {e}")

        # Fallback: generate one-at-a-time
        results = []
        for p in problems:
            variation = await self.generate_exercise_variation(
                p["title"], p["description"],
                p.get("key_concepts", []), p.get("math_concepts", []),
                p.get("is_review", False), weak_areas,
            )
            results.append(variation)
        return results

    async def grade_code(
        self,
        problem_title: str,
        prompt_text: str,
        key_concepts: list[str],
        math_concepts: list[str],
        submitted_code: str,
    ) -> MLCodingExerciseGrade:
        """
        Grade submitted Python code using Gemini.

        Evaluates on 3 dimensions:
        - Correctness (weight 3): Does the implementation work? Edge cases?
        - Code Quality (weight 2): Clean, idiomatic Python? Good naming?
        - Math Understanding (weight 3): Shows understanding of underlying algorithm/math?
        """
        if not self.configured:
            return self._fallback_grade(submitted_code, key_concepts)

        prompt = self._build_grading_prompt(
            problem_title, prompt_text, key_concepts, math_concepts, submitted_code,
        )

        try:
            response = await asyncio.to_thread(self.model.generate_content, prompt)
            return self._parse_grading_response(response.text, submitted_code, key_concepts)
        except Exception as e:
            print(f"Gemini code grading failed: {e}")
            return self._fallback_grade(submitted_code, key_concepts)

    # ============ Prompt Builders ============

    def _build_variation_prompt(
        self,
        title: str,
        description: str,
        key_concepts: list[str],
        math_concepts: list[str],
        is_review: bool,
        weak_areas: list[str],
    ) -> str:
        review_note = ""
        if is_review:
            review_note = "\nThis is a REVIEW exercise. Make the variation slightly different from the standard version to test deeper understanding."

        weak_note = ""
        if weak_areas:
            weak_note = f"\nThe student has shown weakness in: {', '.join(weak_areas)}. Emphasize these areas in the problem variation."

        return f"""You are an ML interview coach creating a specific coding problem variation.

PROBLEM: {title}
DESCRIPTION: {description}
KEY CONCEPTS: {', '.join(key_concepts)}
MATH CONCEPTS: {', '.join(math_concepts)}
{review_note}{weak_note}

Generate a specific variation of this problem with:
1. A clear problem statement with specific input/output format
2. Starter code with function signature and docstring
3. Concrete examples showing expected behavior

The problem should be implementable in pure Python + numpy only. No sklearn, scipy, or other ML libraries.

Respond with ONLY JSON (no markdown fences):
{{
  "prompt_text": "Full problem statement with examples and constraints",
  "starter_code": "import numpy as np\\n\\ndef function_name(args):\\n    \\\"\\\"\\\"Docstring.\\\"\\\"\\\"\\n    pass"
}}"""

    def _build_batch_variation_prompt(
        self,
        problems: list[dict],
        weak_areas: list[str],
    ) -> str:
        specs = []
        for i, p in enumerate(problems):
            review_tag = " [REVIEW]" if p.get("is_review", False) else ""
            specs.append(
                f'{i + 1}.{review_tag} "{p["title"]}": {p["description"][:200]} '
                f'(Concepts: {", ".join(p.get("key_concepts", [])[:4])})'
            )

        weak_note = ""
        if weak_areas:
            weak_note = f"\nStudent weak areas: {', '.join(weak_areas)}."

        return f"""You are an ML interview coach creating {len(problems)} coding problem variations.
{weak_note}
For each problem below, generate a specific variation with a clear problem statement, examples, and starter code.
Problems should be implementable in pure Python + numpy only.

{chr(10).join(specs)}

Respond with ONLY a JSON array (no markdown fences):
[
  {{"prompt_text": "Problem 1 statement with examples...", "starter_code": "import numpy as np\\n\\ndef ..."}},
  {{"prompt_text": "Problem 2 statement with examples...", "starter_code": "..."}}
]"""

    def _build_grading_prompt(
        self,
        title: str,
        prompt_text: str,
        key_concepts: list[str],
        math_concepts: list[str],
        submitted_code: str,
    ) -> str:
        return f"""You are a senior ML engineer grading a coding interview response.

PROBLEM: {title}
PROMPT: {prompt_text}
KEY CONCEPTS: {', '.join(key_concepts)}
MATH CONCEPTS: {', '.join(math_concepts)}

SUBMITTED CODE:
```python
{submitted_code}
```

Grade this code on three dimensions (each scored 1-10):

### 1. Correctness (weight 3)
- Does the implementation produce correct results?
- Are edge cases handled (empty inputs, single element, etc.)?
- Would this pass reasonable test cases?

Score anchors:
- 9-10: Fully correct, handles edge cases, would pass all tests
- 7-8: Mostly correct, minor edge case issues
- 5-6: Core logic works but significant gaps
- 3-4: Partially correct, fundamental issues
- 1-2: Does not work

### 2. Code Quality (weight 2)
- Clean, readable, idiomatic Python?
- Good variable naming?
- Appropriate use of numpy?
- No unnecessary complexity?

Score anchors:
- 9-10: Production-quality code, excellent style
- 7-8: Clean code with minor style issues
- 5-6: Functional but messy or hard to read
- 3-4: Poor style, confusing structure
- 1-2: Unreadable or fundamentally poor

### 3. Math Understanding (weight 3)
- Shows understanding of the underlying algorithm/math?
- Correct mathematical formulations?
- Would the candidate be able to explain the math if asked?

Score anchors:
- 9-10: Deep understanding, correct formulations, could explain derivations
- 7-8: Good understanding, minor mathematical gaps
- 5-6: Surface understanding, uses formulas without full comprehension
- 3-4: Weak understanding, mathematical errors
- 1-2: No evidence of mathematical understanding

Respond with ONLY JSON (no markdown fences):
{{
  "correctness_score": 7,
  "code_quality_score": 6,
  "math_understanding_score": 8,
  "feedback": "2-3 sentences of direct, actionable feedback",
  "missed_concepts": ["concepts the code misses or gets wrong"],
  "suggested_improvements": ["specific code improvements"]
}}"""

    # ============ Response Parsers ============

    def _parse_variation_response(self, text: str, title: str, description: str) -> dict:
        try:
            json_match = re.search(r'\{[\s\S]*\}', text)
            if not json_match:
                return self._fallback_variation(title, description)

            data = json.loads(json_match.group())
            return {
                "prompt_text": data.get("prompt_text", description),
                "starter_code": data.get("starter_code"),
            }
        except (json.JSONDecodeError, KeyError) as e:
            print(f"Failed to parse variation response: {e}")
            return self._fallback_variation(title, description)

    def _parse_batch_variation_response(self, text: str, problems: list[dict]) -> list[dict]:
        try:
            json_match = re.search(r'\[[\s\S]*\]', text)
            if not json_match:
                return []

            data = json.loads(json_match.group())
            if not isinstance(data, list):
                return []

            variations = []
            for item in data:
                if not isinstance(item, dict) or not item.get("prompt_text"):
                    return []  # Invalid item, fall back to one-at-a-time
                variations.append({
                    "prompt_text": item["prompt_text"],
                    "starter_code": item.get("starter_code"),
                })
            return variations
        except (json.JSONDecodeError, KeyError):
            return []

    def _parse_grading_response(
        self, text: str, submitted_code: str, key_concepts: list[str],
    ) -> MLCodingExerciseGrade:
        try:
            json_match = re.search(r'\{[\s\S]*\}', text)
            if not json_match:
                raise ValueError("No JSON found in grading response")

            data = json.loads(json_match.group())

            correctness = min(10, max(1, float(data.get("correctness_score", 5))))
            code_quality = min(10, max(1, float(data.get("code_quality_score", 5))))
            math_understanding = min(10, max(1, float(data.get("math_understanding_score", 5))))

            # Compute overall score in code (not trusting model)
            overall = (
                correctness * DIMENSION_WEIGHTS["correctness"]
                + code_quality * DIMENSION_WEIGHTS["code_quality"]
                + math_understanding * DIMENSION_WEIGHTS["math_understanding"]
            ) / TOTAL_WEIGHT

            overall = round(overall, 1)

            if overall >= 7:
                verdict = "pass"
            elif overall >= 5:
                verdict = "borderline"
            else:
                verdict = "fail"

            return MLCodingExerciseGrade(
                score=overall,
                verdict=verdict,
                feedback=data.get("feedback", "Grading complete."),
                correctness_score=round(correctness, 1),
                code_quality_score=round(code_quality, 1),
                math_understanding_score=round(math_understanding, 1),
                missed_concepts=data.get("missed_concepts", []),
                suggested_improvements=data.get("suggested_improvements", []),
            )
        except (json.JSONDecodeError, KeyError, ValueError) as e:
            print(f"Failed to parse grading response: {e}")
            return self._fallback_grade(submitted_code, key_concepts)

    # ============ Fallbacks ============

    def _fallback_variation(self, title: str, description: str) -> dict:
        return {
            "prompt_text": f"{title}\n\n{description}\n\nImplement this in Python using only numpy. Include proper docstrings and handle edge cases.",
            "starter_code": "import numpy as np\n\n# Implement your solution here\n",
        }

    def _fallback_grade(
        self, submitted_code: str, key_concepts: list[str],
    ) -> MLCodingExerciseGrade:
        line_count = len(submitted_code.strip().split('\n')) if submitted_code else 0
        base = 3.0
        if line_count > 5:
            base += 1.0
        if line_count > 15:
            base += 1.0
        if line_count > 30:
            base += 1.0
        if 'def ' in submitted_code:
            base += 0.5
        if 'return' in submitted_code:
            base += 0.5

        score = min(10, max(1, base))
        if score >= 7:
            verdict = "pass"
        elif score >= 5:
            verdict = "borderline"
        else:
            verdict = "fail"

        return MLCodingExerciseGrade(
            score=score,
            verdict=verdict,
            feedback="AI grading unavailable. Score based on code structure. Ensure the API key is configured for detailed feedback.",
            correctness_score=score,
            code_quality_score=score,
            math_understanding_score=score,
            missed_concepts=[c for c in key_concepts if c.lower() not in submitted_code.lower()],
            suggested_improvements=["Enable Gemini API for detailed code review"],
        )


# Singleton
_ml_coding_service: Optional[MLCodingService] = None


def get_ml_coding_service() -> MLCodingService:
    """Get or create the ML coding service singleton."""
    global _ml_coding_service
    if _ml_coding_service is None:
        _ml_coding_service = MLCodingService()
    return _ml_coding_service
