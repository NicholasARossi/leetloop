"""System Design service for question generation and grading via Gemini."""

import json
import re
from typing import Optional

import google.generativeai as genai

from app.config import get_settings
from app.models.system_design_schemas import (
    GeneratedQuestion,
    GeminiGradingContext,
    GeminiGradingResponse,
    GeminiQuestionContext,
    GeminiSimplifiedGradingResponse,
    GeminiSingleQuestionResponse,
    QuestionGrade,
    RubricScore,
)


# Book content context for enhanced question generation
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


class SystemDesignService:
    """
    Service for generating system design questions and grading responses.

    Uses Gemini for:
    - Generating 2-3 hard, scenario-based questions
    - Harsh senior-level grading with rubric scoring
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

    async def generate_questions(
        self,
        context: GeminiQuestionContext,
        book_content: Optional[BookContentContext] = None,
    ) -> list[GeneratedQuestion]:
        """
        Generate 2-3 hard, scenario-based system design questions.

        Args:
            context: Topic, track type, and user context
            book_content: Optional book content to enhance question generation

        Returns:
            List of generated questions with focus areas and key concepts
        """
        if not self.configured:
            return self._fallback_questions(context.topic)

        prompt = self._build_question_prompt(context, book_content)

        try:
            response = self.model.generate_content(prompt)
            return self._parse_questions_response(response.text)
        except Exception as e:
            print(f"Gemini question generation failed: {e}")
            return self._fallback_questions(context.topic)

    async def grade_session(
        self,
        context: GeminiGradingContext,
    ) -> GeminiGradingResponse:
        """
        Grade user responses with harsh, senior-level feedback.

        Rubric dimensions (each 1-3):
        - Depth: Edge cases, failure modes, implementation details
        - Tradeoffs: CAP, latency/consistency, cost/performance
        - Clarity: Structure, explainability to junior engineer
        - Scalability: Numbers, estimates, growth handling

        Args:
            context: Questions, responses, and rubric weights

        Returns:
            Complete grading with scores, feedback, and review topics
        """
        if not self.configured:
            return self._fallback_grading(context)

        prompt = self._build_grading_prompt(context)

        try:
            response = self.model.generate_content(prompt)
            return self._parse_grading_response(response.text)
        except Exception as e:
            print(f"Gemini grading failed: {e}")
            return self._fallback_grading(context)

    def _build_question_prompt(
        self,
        context: GeminiQuestionContext,
        book_content: Optional[BookContentContext] = None,
    ) -> str:
        """Build prompt for question generation."""
        examples = ", ".join(context.example_systems) if context.example_systems else "real-world systems"
        weak_areas_note = ""
        if context.user_weak_areas:
            weak_areas_note = f"\n\nThe user has shown weakness in: {', '.join(context.user_weak_areas)}. Include at least one question that probes these areas."

        # Add book content context if available
        book_context_note = ""
        if book_content and (book_content.key_concepts or book_content.summary):
            book_context_note = f"""

REFERENCE MATERIAL from "Reliable Machine Learning":
Chapter: {book_content.chapter_title}
Summary: {book_content.summary}
Key Concepts to Test: {', '.join(book_content.key_concepts[:10])}
"""
            if book_content.case_studies:
                case_study_names = [cs.get("name", "") for cs in book_content.case_studies[:3]]
                book_context_note += f"Case Studies: {', '.join(case_study_names)}\n"

            book_context_note += """
IMPORTANT: Generate questions that test understanding of the concepts from this chapter.
Questions should probe real-world application of ML reliability principles."""

        return f"""You are a senior system design interviewer at a top tech company. Generate 2-3 HARD, scenario-based system design questions about "{context.topic}".

Track type: {context.track_type.upper()}
Example systems to reference: {examples}
{weak_areas_note}
{book_context_note}

Requirements:
1. Questions must be SPECIFIC scenarios, not generic "design X" questions
2. Each question should probe a DIFFERENT aspect (data modeling, scaling, failure handling, etc.)
3. Questions should require deep technical knowledge to answer well
4. Include edge cases and constraints in the question itself

For each question, provide:
- The question text (specific scenario with constraints)
- Focus area (what aspect this tests)
- Key concepts the answer should cover (5-8 specific things)

Format your response EXACTLY as JSON:
{{
  "questions": [
    {{
      "id": 0,
      "text": "...",
      "focus_area": "...",
      "key_concepts": ["concept1", "concept2", ...]
    }},
    ...
  ]
}}

Example for "Recommendation System":
{{
  "questions": [
    {{
      "id": 0,
      "text": "Netflix wants to show personalized recommendations on their homepage that update in real-time as users browse. The system must handle 200M users, with 10% online at peak hours. Cold-start users should see reasonable recommendations within 3 page views. Design the recommendation serving layer, focusing on how you balance freshness vs. latency.",
      "focus_area": "real-time serving and latency optimization",
      "key_concepts": ["feature store", "model serving", "caching strategies", "cold-start problem", "A/B testing", "fallback recommendations", "latency budgets"]
    }},
    ...
  ]
}}

Generate questions now:"""

    def _build_grading_prompt(self, context: GeminiGradingContext) -> str:
        """Build prompt for harsh senior-level grading."""
        questions_text = ""
        for i, q in enumerate(context.questions):
            questions_text += f"""
---
QUESTION {i + 1}: {q.get('text', '')}
Focus area: {q.get('focus_area', '')}
Key concepts expected: {', '.join(q.get('key_concepts', []))}

USER RESPONSE:
{q.get('response', 'No response provided')}
---
"""

        rubric = context.rubric
        return f"""You are a harsh but fair senior system design interviewer at a top tech company. Grade these responses with the critical eye of someone who has to recommend hire/no-hire decisions.

Topic: {context.topic}
Track: {context.track_type.upper()}

RUBRIC (each dimension scored 1-3):
- Depth (weight: {rubric.depth}): Edge cases, failure modes, implementation details. Does the candidate go beyond surface-level architecture?
- Tradeoffs (weight: {rubric.tradeoffs}): Does the candidate explicitly discuss CAP theorem, latency vs consistency, cost vs performance? Or do they just present one solution without alternatives?
- Clarity (weight: {rubric.clarity}): Could a junior engineer understand this explanation? Is it structured logically?
- Scalability (weight: {rubric.scalability}): Does the candidate provide actual numbers? Estimate traffic? Plan for 10x growth?

GRADING GUIDELINES:
- 7/10 = "would likely pass" - Most responses should score 4-6
- Be SPECIFIC about gaps. Not "needs more detail" but "didn't address what happens when the cache fails"
- Identify PATTERNS across questions (e.g., "consistently ignores failure scenarios")
- return review_topics for concepts the user clearly doesn't understand

{questions_text}

Format your response EXACTLY as JSON:
{{
  "overall_score": 5.5,
  "overall_feedback": "Detailed 2-3 sentence summary of performance...",
  "question_grades": [
    {{
      "question_id": 0,
      "score": 5.0,
      "feedback": "Specific feedback for this question...",
      "rubric_scores": [
        {{"dimension": "depth", "score": 2, "feedback": "..."}},
        {{"dimension": "tradeoffs", "score": 1, "feedback": "..."}},
        {{"dimension": "clarity", "score": 2, "feedback": "..."}},
        {{"dimension": "scalability", "score": 1, "feedback": "..."}}
      ],
      "missed_concepts": ["concept1", "concept2"]
    }},
    ...
  ],
  "strengths": ["strength1", "strength2"],
  "gaps": ["gap1", "gap2"],
  "review_topics": ["topic1", "topic2"],
  "would_hire": false
}}

Grade now:"""

    def _parse_questions_response(self, text: str) -> list[GeneratedQuestion]:
        """Parse Gemini's question generation response."""
        try:
            # Extract JSON from response
            json_match = re.search(r'\{[\s\S]*\}', text)
            if not json_match:
                return self._fallback_questions("System Design")

            data = json.loads(json_match.group())
            questions = []
            for q in data.get("questions", []):
                questions.append(GeneratedQuestion(
                    id=q.get("id", len(questions)),
                    text=q.get("text", ""),
                    focus_area=q.get("focus_area", "general"),
                    key_concepts=q.get("key_concepts", []),
                ))
            return questions if questions else self._fallback_questions("System Design")
        except (json.JSONDecodeError, KeyError) as e:
            print(f"Failed to parse questions response: {e}")
            return self._fallback_questions("System Design")

    def _parse_grading_response(self, text: str) -> GeminiGradingResponse:
        """Parse Gemini's grading response."""
        try:
            # Extract JSON from response
            json_match = re.search(r'\{[\s\S]*\}', text)
            if not json_match:
                raise ValueError("No JSON found in response")

            data = json.loads(json_match.group())

            question_grades = []
            for qg in data.get("question_grades", []):
                rubric_scores = []
                for rs in qg.get("rubric_scores", []):
                    rubric_scores.append(RubricScore(
                        dimension=rs.get("dimension", ""),
                        score=min(3, max(1, rs.get("score", 1))),
                        feedback=rs.get("feedback", ""),
                    ))

                question_grades.append(QuestionGrade(
                    question_id=qg.get("question_id", 0),
                    score=min(10, max(1, qg.get("score", 5.0))),
                    feedback=qg.get("feedback", ""),
                    rubric_scores=rubric_scores,
                    missed_concepts=qg.get("missed_concepts", []),
                ))

            return GeminiGradingResponse(
                overall_score=min(10, max(1, data.get("overall_score", 5.0))),
                overall_feedback=data.get("overall_feedback", "Unable to provide detailed feedback."),
                question_grades=question_grades,
                strengths=data.get("strengths", []),
                gaps=data.get("gaps", []),
                review_topics=data.get("review_topics", []),
                would_hire=data.get("would_hire"),
            )
        except (json.JSONDecodeError, KeyError, ValueError) as e:
            print(f"Failed to parse grading response: {e}")
            return self._fallback_grading_response()

    def _fallback_questions(self, topic: str) -> list[GeneratedQuestion]:
        """Return fallback questions when Gemini is unavailable."""
        return [
            GeneratedQuestion(
                id=0,
                text=f"Design a scalable {topic} system that handles 100M daily active users. Focus on the data model, caching strategy, and how you would handle sudden traffic spikes.",
                focus_area="architecture and scaling",
                key_concepts=["horizontal scaling", "caching", "load balancing", "database sharding", "rate limiting"],
            ),
            GeneratedQuestion(
                id=1,
                text=f"Your {topic} system experiences a regional outage. Walk through your disaster recovery plan, including data consistency guarantees and failover procedures.",
                focus_area="reliability and failure handling",
                key_concepts=["redundancy", "failover", "data replication", "consistency models", "monitoring"],
            ),
            GeneratedQuestion(
                id=2,
                text=f"Design the data pipeline for the {topic} system. How would you handle schema evolution, backfills, and ensure exactly-once processing?",
                focus_area="data engineering",
                key_concepts=["ETL", "stream processing", "idempotency", "schema versioning", "data quality"],
            ),
        ]

    def _fallback_grading(self, context: GeminiGradingContext) -> GeminiGradingResponse:
        """Return fallback grading when Gemini is unavailable."""
        question_grades = []
        for i, q in enumerate(context.questions):
            response_text = q.get("response", "")
            word_count = len(response_text.split()) if response_text else 0

            # Basic heuristic scoring based on response length and key concepts
            base_score = 3.0  # Start low
            if word_count > 50:
                base_score += 1.0
            if word_count > 150:
                base_score += 1.0
            if word_count > 300:
                base_score += 1.0

            # Check for key concepts mentioned
            concepts_found = 0
            for concept in q.get("key_concepts", []):
                if concept.lower() in response_text.lower():
                    concepts_found += 1
            base_score += min(2.0, concepts_found * 0.5)

            question_grades.append(QuestionGrade(
                question_id=i,
                score=min(10, max(1, base_score)),
                feedback="AI grading unavailable. This is a basic heuristic score based on response length and keyword presence.",
                rubric_scores=[
                    RubricScore(dimension="depth", score=2, feedback="Manual review required"),
                    RubricScore(dimension="tradeoffs", score=2, feedback="Manual review required"),
                    RubricScore(dimension="clarity", score=2, feedback="Manual review required"),
                    RubricScore(dimension="scalability", score=2, feedback="Manual review required"),
                ],
                missed_concepts=[c for c in q.get("key_concepts", []) if c.lower() not in response_text.lower()],
            ))

        avg_score = sum(qg.score for qg in question_grades) / len(question_grades) if question_grades else 5.0

        return GeminiGradingResponse(
            overall_score=avg_score,
            overall_feedback="AI grading is currently unavailable. Your responses have been scored using a basic heuristic. For detailed feedback, please ensure the API key is configured.",
            question_grades=question_grades,
            strengths=["Response submitted"],
            gaps=["AI feedback unavailable"],
            review_topics=[context.topic],
            would_hire=None,
        )

    def _fallback_grading_response(self) -> GeminiGradingResponse:
        """Return minimal fallback when parsing fails."""
        return GeminiGradingResponse(
            overall_score=5.0,
            overall_feedback="Unable to parse grading response. Please try again.",
            question_grades=[],
            strengths=[],
            gaps=["Grading error"],
            review_topics=[],
            would_hire=None,
        )

    # ============ Dashboard Questions (Pre-generated for caching) ============

    async def generate_dashboard_questions(
        self,
        context: GeminiQuestionContext,
        count: int = 2,
    ) -> dict:
        """
        Generate a scenario with focused sub-questions for dashboard display.

        Each sub-question focuses on exactly 2 concepts, making answers more focused.
        A full scenario has 3 sub-questions total, spread across 2 days.

        Args:
            context: Topic, track type, and user context
            count: Number of sub-questions to generate for today (default 2)

        Returns:
            Dict with scenario and list of sub-questions
        """
        if not self.configured:
            return self._fallback_dashboard_questions(context.topic, count)

        prompt = self._build_dashboard_questions_prompt(context, count)

        try:
            response = self.model.generate_content(prompt)
            return self._parse_dashboard_questions_response(response.text, context.topic, count)
        except Exception as e:
            print(f"Gemini dashboard question generation failed: {e}")
            return self._fallback_dashboard_questions(context.topic, count)

    def _build_dashboard_questions_prompt(self, context: GeminiQuestionContext, count: int) -> str:
        """Build prompt for dashboard question generation with focused sub-questions."""
        examples = ", ".join(context.example_systems) if context.example_systems else "real-world systems"
        weak_areas_note = ""
        if context.user_weak_areas:
            weak_areas_note = f"\n\nThe user has shown weakness in: {', '.join(context.user_weak_areas)}. Probe these areas."

        return f"""You are a senior system design interviewer. Create ONE challenging scenario about "{context.topic}" with {count} focused sub-questions.

Track type: {context.track_type.upper()}
Example systems: {examples}
{weak_areas_note}

STRUCTURE:
1. Write a realistic scenario (2-3 sentences) with specific constraints (users, QPS, latency)
2. Create {count} focused sub-questions, each probing exactly 2 concepts
3. Each sub-question should be answerable in 50-100 words

IMPORTANT: Each sub-question should focus on ONLY 2 specific concepts. This keeps answers focused.

Format your response EXACTLY as JSON:
{{
  "scenario": "Your company is building a real-time collaborative document editor like Google Docs. You need to support 10M documents with 1000 concurrent editors per popular document. Changes must sync within 200ms...",
  "sub_questions": [
    {{
      "text": "How would you handle conflict resolution when two users edit the same paragraph simultaneously?",
      "focus_area": "conflict resolution",
      "key_concepts": ["operational transformation", "CRDTs"]
    }},
    {{
      "text": "Design the data model for storing document state and edit history efficiently.",
      "focus_area": "data modeling",
      "key_concepts": ["document versioning", "change deltas"]
    }}
  ]
}}

Generate now:"""

    def _parse_dashboard_questions_response(
        self,
        text: str,
        topic: str,
        count: int,
    ) -> dict:
        """Parse Gemini's dashboard questions response."""
        try:
            json_match = re.search(r'\{[\s\S]*\}', text)
            if not json_match:
                return self._fallback_dashboard_questions(topic, count)

            data = json.loads(json_match.group())
            scenario = data.get("scenario", "")
            sub_questions = []

            for i, q in enumerate(data.get("sub_questions", [])):
                # Ensure exactly 2 concepts per sub-question
                concepts = q.get("key_concepts", [])[:2]
                if len(concepts) < 2:
                    concepts = concepts + ["implementation details", "trade-offs"][:2-len(concepts)]

                sub_questions.append({
                    "text": q.get("text", ""),
                    "focus_area": q.get("focus_area", "general"),
                    "key_concepts": concepts,
                    "part_number": i + 1,
                })

            # Ensure we have the requested count
            while len(sub_questions) < count:
                sub_questions.append(self._fallback_sub_question(topic, len(sub_questions) + 1))

            return {
                "scenario": scenario,
                "sub_questions": sub_questions[:count],
                "total_parts": 3,  # Full question has 3 parts across 2 days
            }
        except (json.JSONDecodeError, KeyError) as e:
            print(f"Failed to parse dashboard questions response: {e}")
            return self._fallback_dashboard_questions(topic, count)

    def _fallback_dashboard_questions(self, topic: str, count: int) -> dict:
        """Return fallback scenario with sub-questions."""
        return {
            "scenario": f"Your company is building a scalable {topic} system. You need to handle 100M daily active users with sub-100ms latency. The system must be highly available (99.99% uptime) and handle 10x traffic spikes during peak hours.",
            "sub_questions": [self._fallback_sub_question(topic, i + 1) for i in range(count)],
            "total_parts": 3,
        }

    def _fallback_sub_question(self, topic: str, part_number: int) -> dict:
        """Return a fallback sub-question."""
        fallbacks = [
            {
                "text": "Design the data model and caching strategy for this system.",
                "focus_area": "data modeling",
                "key_concepts": ["schema design", "cache invalidation"],
            },
            {
                "text": "How would you handle failures and ensure data consistency?",
                "focus_area": "reliability",
                "key_concepts": ["failover", "consistency guarantees"],
            },
            {
                "text": "Describe your scaling strategy for 10x traffic growth.",
                "focus_area": "scaling",
                "key_concepts": ["horizontal scaling", "load balancing"],
            },
        ]
        idx = (part_number - 1) % len(fallbacks)
        return {**fallbacks[idx], "part_number": part_number}

    # ============ Simplified Single-Question Methods ============

    async def generate_single_question(
        self,
        context: GeminiQuestionContext,
    ) -> GeminiSingleQuestionResponse:
        """
        Generate ONE hard, scenario-based system design question.

        Args:
            context: Topic, track type, and user context

        Returns:
            Single generated question with focus area and key concepts
        """
        if not self.configured:
            return self._fallback_single_question(context.topic)

        prompt = self._build_single_question_prompt(context)

        try:
            response = self.model.generate_content(prompt)
            return self._parse_single_question_response(response.text)
        except Exception as e:
            print(f"Gemini single question generation failed: {e}")
            return self._fallback_single_question(context.topic)

    async def grade_attempt(
        self,
        topic: str,
        track_type: str,
        question_text: str,
        focus_area: str,
        key_concepts: list[str],
        response_text: str,
    ) -> GeminiSimplifiedGradingResponse:
        """
        Grade a single response with harsh, simplified feedback.

        Returns:
            - score: 1-10
            - verdict: 'pass' (>=7) | 'borderline' (5-7) | 'fail' (<5)
            - feedback: 2-3 harsh sentences
            - missed_concepts: concepts not covered
            - review_topics: topics to add to review queue
        """
        if not self.configured:
            return self._fallback_attempt_grading(response_text, key_concepts, topic)

        prompt = self._build_attempt_grading_prompt(
            topic, track_type, question_text, focus_area, key_concepts, response_text
        )

        try:
            response = self.model.generate_content(prompt)
            return self._parse_attempt_grading_response(response.text, topic)
        except Exception as e:
            print(f"Gemini attempt grading failed: {e}")
            return self._fallback_attempt_grading(response_text, key_concepts, topic)

    def _build_single_question_prompt(self, context: GeminiQuestionContext) -> str:
        """Build prompt for single question generation."""
        examples = ", ".join(context.example_systems) if context.example_systems else "real-world systems"
        weak_areas_note = ""
        if context.user_weak_areas:
            weak_areas_note = f"\n\nThe user has shown weakness in: {', '.join(context.user_weak_areas)}. Probe these areas."

        return f"""You are a senior system design interviewer at a top tech company. Generate ONE HARD, scenario-based system design question about "{context.topic}".

Track type: {context.track_type.upper()}
Example systems to reference: {examples}
{weak_areas_note}

Requirements:
1. Question must be a SPECIFIC scenario, not generic "design X"
2. Include concrete constraints (users, requests/sec, latency requirements)
3. Require deep technical knowledge to answer well
4. Probe edge cases, failure modes, and scaling challenges

Provide:
- The question text (specific scenario with constraints)
- Focus area (what aspect this tests)
- Key concepts the answer should cover (5-8 specific things)

Format your response EXACTLY as JSON:
{{
  "text": "Your specific scenario-based question here...",
  "focus_area": "e.g., data modeling, scaling, failure handling",
  "key_concepts": ["concept1", "concept2", ...]
}}

Generate the question now:"""

    def _build_attempt_grading_prompt(
        self,
        topic: str,
        track_type: str,
        question_text: str,
        focus_area: str,
        key_concepts: list[str],
        response_text: str,
    ) -> str:
        """Build prompt for simplified harsh grading."""
        return f"""You are a harsh but fair senior system design interviewer. Grade this response critically - you're deciding whether this person could actually build systems at scale.

TOPIC: {topic}
TRACK: {track_type.upper()}

QUESTION:
{question_text}

Focus area: {focus_area}
Key concepts expected: {', '.join(key_concepts)}

USER RESPONSE:
{response_text}

---

GRADING RULES:
- 7/10 = "would likely pass" - most responses should score 4-6
- Be HARSH. Most candidates fail senior system design interviews.
- Be SPECIFIC about what's missing. Not "needs more detail" but "didn't address cache invalidation strategy"
- If they missed fundamental concepts, call it out directly

Score guidelines:
- 8-10: Expert level - addresses edge cases, failure modes, tradeoffs with numbers
- 7: Solid - covers main concepts but misses some depth
- 5-6: Borderline - basic understanding but significant gaps
- 3-4: Weak - surface level, missing core concepts
- 1-2: Poor - shows lack of understanding

Format your response EXACTLY as JSON:
{{
  "score": 5.5,
  "verdict": "borderline",
  "feedback": "2-3 harsh but constructive sentences about what they got wrong and why it matters...",
  "missed_concepts": ["concept1", "concept2"],
  "review_topics": ["topic1", "topic2"]
}}

Note: verdict must be "pass" (score >= 7), "borderline" (5-7), or "fail" (< 5)

Grade now:"""

    def _parse_single_question_response(self, text: str) -> GeminiSingleQuestionResponse:
        """Parse Gemini's single question response."""
        try:
            json_match = re.search(r'\{[\s\S]*\}', text)
            if not json_match:
                return self._fallback_single_question("System Design")

            data = json.loads(json_match.group())
            return GeminiSingleQuestionResponse(
                text=data.get("text", ""),
                focus_area=data.get("focus_area", "general"),
                key_concepts=data.get("key_concepts", []),
            )
        except (json.JSONDecodeError, KeyError) as e:
            print(f"Failed to parse single question response: {e}")
            return self._fallback_single_question("System Design")

    def _parse_attempt_grading_response(self, text: str, topic: str) -> GeminiSimplifiedGradingResponse:
        """Parse Gemini's simplified grading response."""
        try:
            json_match = re.search(r'\{[\s\S]*\}', text)
            if not json_match:
                raise ValueError("No JSON found in response")

            data = json.loads(json_match.group())
            score = min(10, max(1, data.get("score", 5.0)))

            # Determine verdict based on score if not provided
            verdict = data.get("verdict", "")
            if not verdict or verdict not in ["pass", "fail", "borderline"]:
                if score >= 7:
                    verdict = "pass"
                elif score >= 5:
                    verdict = "borderline"
                else:
                    verdict = "fail"

            return GeminiSimplifiedGradingResponse(
                score=score,
                verdict=verdict,
                feedback=data.get("feedback", "Unable to provide detailed feedback."),
                missed_concepts=data.get("missed_concepts", []),
                review_topics=data.get("review_topics", [topic]),
            )
        except (json.JSONDecodeError, KeyError, ValueError) as e:
            print(f"Failed to parse attempt grading response: {e}")
            return self._fallback_attempt_grading("", [], topic)

    def _fallback_single_question(self, topic: str) -> GeminiSingleQuestionResponse:
        """Return fallback question when Gemini is unavailable."""
        return GeminiSingleQuestionResponse(
            text=f"Design a scalable {topic} system that handles 100M daily active users. Focus on the data model, caching strategy, and how you would handle sudden traffic spikes. Be specific about your database choices, sharding strategy, and failover mechanisms.",
            focus_area="architecture and scaling",
            key_concepts=["horizontal scaling", "caching", "load balancing", "database sharding", "rate limiting", "failover"],
        )

    def _fallback_attempt_grading(
        self,
        response_text: str,
        key_concepts: list[str],
        topic: str,
    ) -> GeminiSimplifiedGradingResponse:
        """Return fallback grading when Gemini is unavailable."""
        word_count = len(response_text.split()) if response_text else 0

        # Basic heuristic scoring
        base_score = 3.0
        if word_count > 50:
            base_score += 1.0
        if word_count > 150:
            base_score += 1.0
        if word_count > 300:
            base_score += 1.0

        # Check for key concepts
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

        missed = [c for c in key_concepts if c.lower() not in response_text.lower()]

        return GeminiSimplifiedGradingResponse(
            score=score,
            verdict=verdict,
            feedback="AI grading unavailable. Score based on response length and keyword presence. For detailed feedback, ensure the API key is configured.",
            missed_concepts=missed,
            review_topics=[topic] if score < 7 else [],
        )


# Singleton instance
_system_design_service: Optional[SystemDesignService] = None


def get_system_design_service() -> SystemDesignService:
    """Get or create the SystemDesignService singleton."""
    global _system_design_service
    if _system_design_service is None:
        _system_design_service = SystemDesignService()
    return _system_design_service
