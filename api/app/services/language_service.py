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

# ============ Exercise Tier Configuration ============

EXERCISE_TIERS = {
    "quick": {
        "count": 3,
        "response_format": "single_line",
        "word_target": 3,
        "types": ["conjugation", "fill_blank", "vocabulary"],
    },
    "short": {
        "count": 2,
        "response_format": "short_text",
        "word_target": 20,
        "types": ["sentence_construction", "error_correction", "grammar"],
    },
    "extended": {
        "count": 2,
        "response_format": "long_text",
        "word_target": 60,
        "types": ["situational", "reading_comprehension", "dialogue"],
    },
    "free_form": {
        "count": 1,
        "response_format": "free_form",
        "word_target": 150,
        "types": ["journal_entry", "opinion_essay", "story_continuation", "letter_writing"],
    },
}

EXERCISE_TYPE_TO_TIER: dict[str, dict] = {}
for _tier_name, _tier_info in EXERCISE_TIERS.items():
    for _etype in _tier_info["types"]:
        EXERCISE_TYPE_TO_TIER[_etype] = {
            "tier": _tier_name,
            "response_format": _tier_info["response_format"],
            "word_target": _tier_info["word_target"],
        }


def get_response_format(exercise_type: str) -> str:
    """Get the response format for an exercise type."""
    info = EXERCISE_TYPE_TO_TIER.get(exercise_type)
    return info["response_format"] if info else "single_line"


def get_word_target(exercise_type: str) -> int:
    """Get the word target for an exercise type."""
    info = EXERCISE_TYPE_TO_TIER.get(exercise_type)
    return info["word_target"] if info else 3


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

    async def generate_batch_exercises(
        self,
        language: str,
        level: str,
        new_topics: list[dict],
        review_topics: list[dict],
        user_weak_areas: list[str],
        book_contexts: dict[str, BookContentContext],
    ) -> list[dict]:
        """
        Generate a batch of exercises in a single Gemini call.

        Falls back to generating exercises one-at-a-time if batch call fails.
        """
        if not self.configured:
            return self._fallback_batch_exercises(
                language, level, new_topics, review_topics
            )

        prompt = self._build_batch_exercise_prompt(
            language, level, new_topics, review_topics,
            user_weak_areas, book_contexts,
        )

        try:
            response = await asyncio.to_thread(self.model.generate_content, prompt)
            exercises = self._parse_batch_exercise_response(response.text)
            if exercises:
                return exercises
        except Exception as e:
            print(f"Gemini batch exercise generation failed: {e}")

        # Fallback: generate one-at-a-time using existing method
        return await self._fallback_generate_individually(
            language, level, new_topics, review_topics,
            user_weak_areas, book_contexts,
        )

    def _build_batch_exercise_prompt(
        self,
        language: str,
        level: str,
        new_topics: list[dict],
        review_topics: list[dict],
        user_weak_areas: list[str],
        book_contexts: dict[str, BookContentContext],
    ) -> str:
        """Build prompt for batch exercise generation."""
        language_name = language.capitalize()
        level_upper = level.upper()

        exercises_spec = []

        for i, rt in enumerate(review_topics):
            book_note = ""
            bc = book_contexts.get(rt["topic"])
            if bc and bc.summary:
                book_note = f" (Textbook context: {bc.summary[:200]})"
            etype = rt.get("exercise_type", "vocabulary")
            tier_info = EXERCISE_TYPE_TO_TIER.get(etype, {})
            tier_label = tier_info.get("tier", "quick").upper()
            word_target = tier_info.get("word_target", 3)
            exercises_spec.append(
                f'{i + 1}. [REVIEW] [{tier_label}] Topic: "{rt["topic"]}" - Type: {etype} - '
                f'Target: ~{word_target} words. Reason: {rt.get("reason", "due for review")}. '
                f'Key concepts: {", ".join(rt.get("key_concepts", []))}.{book_note}'
            )

        offset = len(review_topics)
        for i, nt in enumerate(new_topics):
            book_note = ""
            bc = book_contexts.get(nt["topic"])
            if bc and bc.summary:
                book_note = f" (Textbook context: {bc.summary[:200]})"
            etype = nt.get("exercise_type", "vocabulary")
            tier_info = EXERCISE_TYPE_TO_TIER.get(etype, {})
            tier_label = tier_info.get("tier", "quick").upper()
            word_target = tier_info.get("word_target", 3)
            exercises_spec.append(
                f'{offset + i + 1}. [NEW] [{tier_label}] Topic: "{nt["topic"]}" - Type: {etype} - '
                f'Target: ~{word_target} words. '
                f'Key concepts: {", ".join(nt.get("key_concepts", []))}.{book_note}'
            )

        exercises_list = "\n".join(exercises_spec)

        weak_areas_note = ""
        if user_weak_areas:
            weak_areas_note = f"\nThe student has shown weakness in: {', '.join(user_weak_areas)}. Incorporate these areas where relevant."

        return f"""You are a {language_name} language teacher creating a batch of daily exercises for a {level_upper} student.

CRITICAL RULE: FULL IMMERSION. All questions, example text, and expected answers must be in {language_name}. NO English. NO translation exercises.

Generate {len(exercises_spec)} exercises based on these specifications:

{exercises_list}
{weak_areas_note}

VARIETY RULES:
- Each exercise should test different skills (don't repeat the same pattern)
- For review exercises, use a DIFFERENT exercise type than what the student originally struggled with
- Mix question formats across all tiers

RESPONSE LENGTH BY TIER:
- QUICK exercises: expect a 1-3 word answer (single conjugated form, fill-in-the-blank, vocabulary word)
- SHORT exercises: expect 1-2 sentences (~15-25 words)
- EXTENDED exercises: expect 3-5 sentences (~40-80 words). Include context/scenario.
- FREE_FORM exercises: expect 8-10 sentences (~100-150 words). Give a rich, open-ended prompt.

Format your response as a JSON array. Each exercise object must have:
- "topic": the topic name (must match the topic from the spec above)
- "exercise_type": one of "vocabulary", "grammar", "fill_blank", "conjugation", "sentence_construction", "reading_comprehension", "error_correction", "situational", "dialogue", "journal_entry", "opinion_essay", "story_continuation", "letter_writing"
- "question_text": the exercise prompt entirely in {language_name}
- "expected_answer": the correct/model answer in {language_name} (or null for open-ended/free-form)
- "focus_area": what grammar/vocabulary aspect this tests
- "key_concepts": array of 2-4 concepts tested
- "is_review": true if this is a review exercise, false otherwise
- "response_format": one of "single_line", "short_text", "long_text", "free_form"
- "word_target": approximate number of words expected in the answer

Respond with ONLY the JSON array, no other text:
[
  {{"topic": "...", "exercise_type": "...", "question_text": "...", "expected_answer": "...", "focus_area": "...", "key_concepts": [...], "is_review": false, "response_format": "single_line", "word_target": 3}},
  ...
]"""

    def _parse_batch_exercise_response(self, text: str) -> list[dict]:
        """Parse Gemini's batch exercise generation response."""
        try:
            json_match = re.search(r'\[[\s\S]*\]', text)
            if not json_match:
                return []

            data = json.loads(json_match.group())
            if not isinstance(data, list):
                return []

            exercises = []
            for item in data:
                if not isinstance(item, dict):
                    continue
                if not item.get("question_text"):
                    continue
                etype = item.get("exercise_type", "vocabulary")
                exercises.append({
                    "topic": item.get("topic", ""),
                    "exercise_type": etype,
                    "question_text": item["question_text"],
                    "expected_answer": item.get("expected_answer"),
                    "focus_area": item.get("focus_area", "general"),
                    "key_concepts": item.get("key_concepts", []),
                    "is_review": item.get("is_review", False),
                    "response_format": item.get("response_format") or get_response_format(etype),
                    "word_target": item.get("word_target") or get_word_target(etype),
                })
            return exercises
        except (json.JSONDecodeError, KeyError) as e:
            print(f"Failed to parse batch exercise response: {e}")
            return []

    async def _fallback_generate_individually(
        self,
        language: str,
        level: str,
        new_topics: list[dict],
        review_topics: list[dict],
        user_weak_areas: list[str],
        book_contexts: dict[str, BookContentContext],
    ) -> list[dict]:
        """Fallback: generate exercises one at a time using existing method."""
        exercises = []

        all_items = [
            (rt["topic"], rt.get("exercise_type", "vocabulary"), rt.get("key_concepts", []), True, rt.get("reason"))
            for rt in review_topics
        ] + [
            (nt["topic"], nt.get("exercise_type", "vocabulary"), nt.get("key_concepts", []), False, None)
            for nt in new_topics
        ]

        for topic, exercise_type, key_concepts, is_review, reason in all_items:
            context = LanguageQuestionContext(
                language=language,
                level=level,
                topic=topic,
                exercise_type=exercise_type,
                key_concepts=key_concepts,
                user_weak_areas=user_weak_areas,
            )
            book_content = book_contexts.get(topic)
            result = await self.generate_exercise(context, book_content)
            exercises.append({
                "topic": topic,
                "exercise_type": exercise_type,
                "question_text": result.question_text,
                "expected_answer": result.expected_answer,
                "focus_area": result.focus_area,
                "key_concepts": result.key_concepts,
                "is_review": is_review,
                "response_format": get_response_format(exercise_type),
                "word_target": get_word_target(exercise_type),
            })

        return exercises

    def _fallback_batch_exercises(
        self,
        language: str,
        level: str,
        new_topics: list[dict],
        review_topics: list[dict],
    ) -> list[dict]:
        """Return fallback exercises when Gemini is unavailable."""
        exercises = []

        for rt in review_topics:
            etype = rt.get("exercise_type", "vocabulary")
            context = LanguageQuestionContext(
                language=language, level=level,
                topic=rt["topic"], exercise_type=etype,
                key_concepts=rt.get("key_concepts", []),
            )
            fallback = self._fallback_exercise(context)
            exercises.append({
                "topic": rt["topic"],
                "exercise_type": etype,
                "question_text": fallback.question_text,
                "expected_answer": fallback.expected_answer,
                "focus_area": fallback.focus_area,
                "key_concepts": fallback.key_concepts,
                "is_review": True,
                "response_format": get_response_format(etype),
                "word_target": get_word_target(etype),
            })

        for nt in new_topics:
            etype = nt.get("exercise_type", "vocabulary")
            context = LanguageQuestionContext(
                language=language, level=level,
                topic=nt["topic"], exercise_type=etype,
                key_concepts=nt.get("key_concepts", []),
            )
            fallback = self._fallback_exercise(context)
            exercises.append({
                "topic": nt["topic"],
                "exercise_type": etype,
                "question_text": fallback.question_text,
                "expected_answer": fallback.expected_answer,
                "focus_area": fallback.focus_area,
                "key_concepts": fallback.key_concepts,
                "is_review": False,
                "response_format": get_response_format(etype),
                "word_target": get_word_target(etype),
            })

        return exercises

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

            "error_correction": f"""Create an ERROR CORRECTION exercise. Present 1-2 sentences in {language_name} with grammatical or spelling errors. Ask the student to find and correct ALL errors. Everything in {language_name}. The expected answer is the fully corrected version.""",

            "situational": f"""Create a SITUATIONAL exercise. Describe a real-life scenario in {language_name} (at a restaurant, hotel, doctor, etc.) and ask the student to write what they would say. Expect 3-5 sentences. Everything in {language_name}. Expected answer is a model response.""",

            "dialogue": f"""Create a DIALOGUE exercise. Give a situation and ask the student to write a short conversation (3-5 exchanges) in {language_name}. Specify the roles. Everything in {language_name}. Expected answer is a model dialogue.""",

            "journal_entry": f"""Create a JOURNAL ENTRY exercise. Give the student a personal topic or theme to write about freely in {language_name}. Ask them to use specific grammar structures (e.g. past tenses, subjunctive, connectors). Expect 8-10 sentences. Everything in {language_name}. Expected answer is null (open-ended).""",

            "opinion_essay": f"""Create an OPINION ESSAY exercise. Present a debatable topic and ask the student to argue their position in {language_name}. They should use argument connectors (d'abord, ensuite, en revanche, etc.). Expect 8-10 sentences. Everything in {language_name}. Expected answer is null.""",

            "story_continuation": f"""Create a STORY CONTINUATION exercise. Write the beginning of a short story (2-3 sentences) in {language_name} and ask the student to continue it. Specify which tenses to use. Expect 8-10 sentences from the student. Everything in {language_name}. Expected answer is null.""",

            "letter_writing": f"""Create a LETTER WRITING exercise. Ask the student to write a formal or informal letter in {language_name} for a specific purpose (complaint, thank-you, request, etc.). Specify the tone and recipient. Expect 8-10 sentences. Everything in {language_name}. Expected answer is null.""",
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

        # Determine grading style by response format tier
        response_format = get_response_format(exercise_type)

        grading_style = ""
        if response_format == "single_line":
            grading_style = """
GRADING STYLE: QUICK exercise (single-line answer). Grade near-binary:
- 9-10: Completely correct (including accents and spelling)
- 6-8: Minor errors (missing accent, small spelling mistake, but meaning is correct)
- 1-5: Incorrect answer"""
        elif response_format == "short_text":
            grading_style = """
GRADING STYLE: SHORT exercise (1-2 sentences). Grade on:
- Accuracy (weight 3): Is the answer correct? Correct conjugation, usage?
- Grammar (weight 3): Agreement, tense, word order, accents?
- Vocabulary (weight 2): Appropriate word choice for level?"""
        elif response_format == "long_text":
            grading_style = """
GRADING STYLE: EXTENDED exercise (3-5 sentences). Grade on:
- Accuracy (weight 3): Is the answer correct? Correct conjugation, usage?
- Grammar (weight 3): Agreement, tense, word order, accents?
- Vocabulary (weight 2): Appropriate word choice for level?
- Coherence (weight 1): Does the response flow logically?
- Naturalness (weight 1): Does it sound like a native speaker would say it?"""
        else:  # free_form
            grading_style = """
GRADING STYLE: FREE-FORM exercise (8-10 sentences). Grade on:
- Accuracy (weight 2): Correct conjugation, grammar usage?
- Grammar (weight 2): Agreement, tense, word order, accents?
- Vocabulary (weight 2): Appropriate and varied word choice for level?
- Coherence (weight 1): Does the response flow logically between ideas?
- Naturalness (weight 1): Does it sound like a native speaker wrote it?
- Structure (weight 1): Clear organization with intro, body, conclusion?
- Voice (weight 1): Personal expression and engagement with the topic?

Provide DETAILED feedback on writing style: what worked well, what to improve, and specific suggestions for more natural phrasing."""

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
