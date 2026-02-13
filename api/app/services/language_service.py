"""Language Learning service for exercise generation and grading via Gemini."""

import asyncio
import json
import re
from typing import Optional

import google.generativeai as genai

from app.config import get_settings
from app.models.language_schemas import (
    LanguageGradingResponse,
    LanguageQuestionContext,
    LanguageQuestionResponse,
)


class BookContentContext:
    """Context from ingested book content for a topic."""

    def __init__(
        self,
        chapter_title: str = "",
        summary: str = "",
        key_concepts: list[str] = None,
        case_studies: list[dict] = None,
    ):
        self.chapter_title = chapter_title
        self.summary = summary
        self.key_concepts = key_concepts or []
        self.case_studies = case_studies or []


class LanguageService:
    """
    Service for generating language exercises and grading responses.

    Uses Gemini for:
    - Generating exercises in the target language (full immersion)
    - Grading responses with language-specific rubric
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

    async def generate_exercise(
        self,
        context: LanguageQuestionContext,
        book_content: Optional[BookContentContext] = None,
    ) -> LanguageQuestionResponse:
        """
        Generate a single language exercise in the target language.

        All exercises are in full immersion - no L1/L2 translation.
        Questions, prompts, and expected answers are all in the target language.
        """
        if not self.configured:
            return self._fallback_exercise(context)

        prompt = self._build_exercise_prompt(context, book_content)

        try:
            response = await asyncio.to_thread(self.model.generate_content, prompt)
            return self._parse_exercise_response(response.text, context)
        except Exception as e:
            print(f"Gemini exercise generation failed: {e}")
            return self._fallback_exercise(context)

    async def grade_exercise(
        self,
        language: str,
        level: str,
        exercise_type: str,
        question_text: str,
        expected_answer: Optional[str],
        focus_area: str,
        key_concepts: list[str],
        response_text: str,
    ) -> LanguageGradingResponse:
        """
        Grade a language exercise response.

        Rubric dimensions (weighted):
        - Accuracy (3): Correct answer, conjugation, usage
        - Grammar (3): Agreement, tense, word order, accents
        - Vocabulary (2): Appropriate word choice for level
        - Naturalness (2): Sounds like a native speaker
        """
        if not self.configured:
            return self._fallback_grading(response_text, key_concepts, language)

        prompt = self._build_grading_prompt(
            language, level, exercise_type, question_text,
            expected_answer, focus_area, key_concepts, response_text,
        )

        try:
            response = await asyncio.to_thread(self.model.generate_content, prompt)
            return self._parse_grading_response(response.text, language)
        except Exception as e:
            print(f"Gemini grading failed: {e}")
            return self._fallback_grading(response_text, key_concepts, language)

    def _build_exercise_prompt(
        self,
        context: LanguageQuestionContext,
        book_content: Optional[BookContentContext] = None,
    ) -> str:
        """Build prompt for exercise generation."""
        language_name = context.language.capitalize()
        level_upper = context.level.upper()

        weak_areas_note = ""
        if context.user_weak_areas:
            weak_areas_note = f"\n\nThe student has shown weakness in: {', '.join(context.user_weak_areas)}. Focus on these areas."

        book_context_note = ""
        if book_content and (book_content.key_concepts or book_content.summary):
            book_context_note = f"""

TEXTBOOK REFERENCE:
Chapter: {book_content.chapter_title}
Summary: {book_content.summary}
Key Vocabulary/Grammar: {', '.join(book_content.key_concepts[:10])}

Generate the exercise based on vocabulary and grammar patterns from this chapter."""

        exercise_instructions = self._get_exercise_type_instructions(context.exercise_type, language_name)

        return f"""You are a {language_name} language teacher creating exercises for a {level_upper} student.

CRITICAL RULE: FULL IMMERSION. The question, any example text, and the expected answer must ALL be in {language_name}. NO English. NO translation exercises. The student is practicing thinking entirely in {language_name}.

Topic: {context.topic}
Exercise Type: {context.exercise_type}
Level: {level_upper} (CEFR)
Key concepts to test: {', '.join(context.key_concepts) if context.key_concepts else 'general ' + language_name + ' skills'}
{weak_areas_note}
{book_context_note}

{exercise_instructions}

Format your response EXACTLY as JSON:
{{
  "question_text": "The exercise prompt entirely in {language_name}...",
  "expected_answer": "The correct/model answer in {language_name} (or null for open-ended exercises)",
  "focus_area": "What grammar/vocabulary aspect this tests",
  "key_concepts": ["concept1", "concept2", "concept3"]
}}

Generate the exercise now:"""

    def _get_exercise_type_instructions(self, exercise_type: str, language_name: str) -> str:
        """Get type-specific instructions for exercise generation."""
        instructions = {
            "vocabulary": f"""Create a VOCABULARY exercise. Ask the student to define a word, use it in a sentence, or choose the correct word for a context. Everything in {language_name}. Keep it to one clear, focused question.""",

            "grammar": f"""Create a GRAMMAR exercise. Present a sentence with a grammatical challenge (agreement, tense, mood, preposition). Ask the student to complete or correct it. Everything in {language_name}.""",

            "fill_blank": f"""Create a FILL-IN-THE-BLANK exercise. Write a sentence in {language_name} with one or two blanks (marked with ___). The student fills in the correct form. Provide the expected answer.""",

            "conjugation": f"""Create a CONJUGATION exercise. Give a verb and ask the student to conjugate it for specific tense(s) and person(s). Present the prompt in {language_name}. The expected answer should be the correct conjugated form(s).""",

            "sentence_construction": f"""Create a SENTENCE CONSTRUCTION exercise. Give the student a grammar pattern or vocabulary words and ask them to write an original sentence using them. Prompt entirely in {language_name}. Expected answer is a model sentence.""",

            "reading_comprehension": f"""Create a READING COMPREHENSION exercise. Write a short passage (3-5 sentences) in {language_name} appropriate for the level, then ask ONE focused question about it. Both passage and question in {language_name}.""",

            "dictation": f"""Create a DICTATION exercise. Write a sentence in {language_name} that the student would write from hearing. Focus on tricky spelling, accents, or sound-alike words. The expected answer is the exact sentence.""",
        }
        return instructions.get(exercise_type, instructions["vocabulary"])

    def _build_grading_prompt(
        self,
        language: str,
        level: str,
        exercise_type: str,
        question_text: str,
        expected_answer: Optional[str],
        focus_area: str,
        key_concepts: list[str],
        response_text: str,
    ) -> str:
        """Build prompt for grading a language exercise."""
        language_name = language.capitalize()
        level_upper = level.upper()

        expected_note = ""
        if expected_answer:
            expected_note = f"\nEXPECTED ANSWER:\n{expected_answer}"

        # Simple exercises get near-binary grading
        is_simple = exercise_type in ("fill_blank", "conjugation", "dictation", "vocabulary")

        grading_style = ""
        if is_simple:
            grading_style = """
GRADING STYLE: This is a simple exercise. Grade near-binary:
- 9-10: Completely correct (including accents and spelling)
- 6-8: Minor errors (missing accent, small spelling mistake, but meaning is correct)
- 1-5: Incorrect answer"""
        else:
            grading_style = """
GRADING STYLE: This is an open-ended exercise. Use full rubric:
- Accuracy (weight 3): Is the answer correct? Correct conjugation, usage?
- Grammar (weight 3): Agreement, tense, word order, accents?
- Vocabulary (weight 2): Appropriate word choice for level?
- Naturalness (weight 2): Does it sound like a native speaker would say it?"""

        return f"""You are a strict but fair {language_name} teacher grading a {level_upper} student's exercise.

EXERCISE TYPE: {exercise_type}
FOCUS AREA: {focus_area}
KEY CONCEPTS: {', '.join(key_concepts)}

QUESTION:
{question_text}
{expected_note}

STUDENT'S RESPONSE:
{response_text}

---
{grading_style}

Score guidelines:
- 9-10: Native-level accuracy, natural phrasing
- 7-8: Good - minor issues that don't impede understanding
- 5-6: Borderline - understandable but notable errors
- 3-4: Weak - significant errors, partially incorrect
- 1-2: Poor - fundamental misunderstanding

IMPORTANT: Write your feedback in {language_name} to maintain immersion. Only use English for the JSON field names.

If the student made errors, provide the CORRECT version in the "corrections" field.

Format your response EXACTLY as JSON:
{{
  "score": 7.0,
  "verdict": "pass",
  "feedback": "Feedback in {language_name} about what was good and what needs work...",
  "corrections": "The corrected version of the student's answer in {language_name} (or null if no corrections needed)",
  "missed_concepts": ["concept1", "concept2"]
}}

Note: verdict must be "pass" (score >= 7), "borderline" (5-7), or "fail" (< 5)

Grade now:"""

    def _parse_exercise_response(
        self, text: str, context: LanguageQuestionContext
    ) -> LanguageQuestionResponse:
        """Parse Gemini's exercise generation response."""
        try:
            json_match = re.search(r'\{[\s\S]*\}', text)
            if not json_match:
                return self._fallback_exercise(context)

            data = json.loads(json_match.group())
            return LanguageQuestionResponse(
                question_text=data.get("question_text", ""),
                expected_answer=data.get("expected_answer"),
                focus_area=data.get("focus_area", "general"),
                key_concepts=data.get("key_concepts", []),
            )
        except (json.JSONDecodeError, KeyError) as e:
            print(f"Failed to parse exercise response: {e}")
            return self._fallback_exercise(context)

    def _parse_grading_response(
        self, text: str, language: str
    ) -> LanguageGradingResponse:
        """Parse Gemini's grading response."""
        try:
            json_match = re.search(r'\{[\s\S]*\}', text)
            if not json_match:
                raise ValueError("No JSON found in response")

            data = json.loads(json_match.group())
            score = min(10, max(1, data.get("score", 5.0)))

            verdict = data.get("verdict", "")
            if not verdict or verdict not in ["pass", "fail", "borderline"]:
                if score >= 7:
                    verdict = "pass"
                elif score >= 5:
                    verdict = "borderline"
                else:
                    verdict = "fail"

            return LanguageGradingResponse(
                score=score,
                verdict=verdict,
                feedback=data.get("feedback", "Unable to provide detailed feedback."),
                corrections=data.get("corrections"),
                missed_concepts=data.get("missed_concepts", []),
            )
        except (json.JSONDecodeError, KeyError, ValueError) as e:
            print(f"Failed to parse grading response: {e}")
            return self._fallback_grading("", [], language)

    def _fallback_exercise(
        self, context: LanguageQuestionContext
    ) -> LanguageQuestionResponse:
        """Return fallback exercise when Gemini is unavailable."""
        fallbacks = {
            "french": {
                "vocabulary": LanguageQuestionResponse(
                    question_text="Utilisez le mot 'cependant' dans une phrase compl\u00e8te.",
                    expected_answer="Il fait beau, cependant il fait froid.",
                    focus_area="connecteurs logiques",
                    key_concepts=["cependant", "opposition", "phrase complexe"],
                ),
                "grammar": LanguageQuestionResponse(
                    question_text="Compl\u00e9tez la phrase avec la forme correcte du verbe 'aller' au pass\u00e9 compos\u00e9 : 'Hier, nous ___ au march\u00e9.'",
                    expected_answer="sommes all\u00e9s",
                    focus_area="pass\u00e9 compos\u00e9 avec \u00eatre",
                    key_concepts=["pass\u00e9 compos\u00e9", "auxiliaire \u00eatre", "accord"],
                ),
                "fill_blank": LanguageQuestionResponse(
                    question_text="Je ___ (vouloir) un caf\u00e9, s'il vous pla\u00eet.",
                    expected_answer="voudrais",
                    focus_area="conditionnel de politesse",
                    key_concepts=["conditionnel", "politesse", "vouloir"],
                ),
            },
        }

        language_fallbacks = fallbacks.get(context.language, fallbacks.get("french", {}))
        exercise = language_fallbacks.get(context.exercise_type)

        if exercise:
            return exercise

        # Generic fallback
        return LanguageQuestionResponse(
            question_text=f"Exercise generation unavailable. Practice writing a sentence about: {context.topic}",
            expected_answer=None,
            focus_area="general practice",
            key_concepts=context.key_concepts[:3] if context.key_concepts else ["general"],
        )

    def _fallback_grading(
        self,
        response_text: str,
        key_concepts: list[str],
        language: str,
    ) -> LanguageGradingResponse:
        """Return fallback grading when Gemini is unavailable."""
        word_count = len(response_text.split()) if response_text else 0

        base_score = 3.0
        if word_count > 5:
            base_score += 1.0
        if word_count > 15:
            base_score += 1.0
        if word_count > 30:
            base_score += 1.0

        concepts_found = 0
        for concept in key_concepts:
            if concept.lower() in response_text.lower():
                concepts_found += 1
        base_score += min(2.0, concepts_found * 0.5)

        score = min(10, max(1, base_score))

        if score >= 7:
            verdict = "pass"
        elif score >= 5:
            verdict = "borderline"
        else:
            verdict = "fail"

        return LanguageGradingResponse(
            score=score,
            verdict=verdict,
            feedback="AI grading unavailable. Score based on response length. For detailed feedback, ensure the API key is configured.",
            corrections=None,
            missed_concepts=[c for c in key_concepts if c.lower() not in response_text.lower()],
        )


# Singleton instance
_language_service: Optional[LanguageService] = None


def get_language_service() -> LanguageService:
    """Get or create the LanguageService singleton."""
    global _language_service
    if _language_service is None:
        _language_service = LanguageService()
    return _language_service
