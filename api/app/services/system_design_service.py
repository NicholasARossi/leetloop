"""System Design service for oral question generation via Gemini."""

import asyncio
import json
import re
from typing import Optional

import google.generativeai as genai

from app.config import get_settings


class SystemDesignService:
    """
    Service for generating oral system design interview questions.

    Uses Gemini for:
    - Generating scenario + 3 focused sub-questions for oral sessions
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

    # ============ Oral Session Question Generation ============

    async def generate_oral_questions(
        self,
        topic: str,
        track_type: str,
    ) -> tuple[str, list[dict]]:
        """
        Generate scenario + 3 focused sub-questions for an oral session.

        Each sub-question targets a different aspect:
        1. Data & Storage
        2. Core System / ML Pipeline
        3. Evaluation & Operations

        Returns:
            (scenario, [sub_questions]) where each sub_question has:
            question_text, focus_area, key_concepts, suggested_duration_minutes
        """
        if not self.configured:
            return self._fallback_oral_questions(topic, track_type)

        prompt = self._build_oral_questions_prompt(topic, track_type)

        try:
            response = await asyncio.to_thread(self.model.generate_content, prompt)
            return self._parse_oral_questions_response(response.text, topic, track_type)
        except Exception as e:
            print(f"Gemini oral question generation failed: {e}")
            return self._fallback_oral_questions(topic, track_type)

    def _build_oral_questions_prompt(self, topic: str, track_type: str) -> str:
        """Build prompt for oral session question generation."""
        return f"""You are a senior system design interviewer at Google/Amazon. Create a system design interview scenario about "{topic}" broken into 3 focused sub-questions for ORAL practice.

Track type: {track_type.upper()}

STRUCTURE:
1. Write a realistic scenario (2-3 sentences) with specific constraints (users, QPS, data volume, latency requirements)
2. Create 3 focused sub-questions, each targeting a different aspect of the design:
   - Part 1: Data & Storage (how to model and store the data)
   - Part 2: Core System / ML Pipeline (the main processing or inference layer)
   - Part 3: Evaluation & Operations (A/B testing, monitoring, iteration)
3. Each sub-question should be answerable in 3-5 minutes of talking
4. Each sub-question should have 3-4 key concepts the candidate should cover

Format your response EXACTLY as JSON:
{{
  "scenario": "Your realistic scenario with constraints...",
  "sub_questions": [
    {{
      "question_text": "Walk me through how you'd model the data for this system...",
      "focus_area": "Data & Storage",
      "key_concepts": ["concept1", "concept2", "concept3"],
      "suggested_duration_minutes": 4
    }},
    {{
      "question_text": "Design the core processing pipeline...",
      "focus_area": "Core System / ML Pipeline",
      "key_concepts": ["concept1", "concept2", "concept3"],
      "suggested_duration_minutes": 5
    }},
    {{
      "question_text": "How would you evaluate and iterate on this system...",
      "focus_area": "Evaluation & Operations",
      "key_concepts": ["concept1", "concept2", "concept3"],
      "suggested_duration_minutes": 4
    }}
  ]
}}

Generate now:"""

    def _parse_oral_questions_response(
        self, text: str, topic: str, track_type: str
    ) -> tuple[str, list[dict]]:
        """Parse Gemini's oral questions response."""
        try:
            json_match = re.search(r'\{[\s\S]*\}', text)
            if not json_match:
                return self._fallback_oral_questions(topic, track_type)

            data = json.loads(json_match.group())
            scenario = data.get("scenario", "")
            sub_questions = []

            for i, q in enumerate(data.get("sub_questions", [])):
                concepts = q.get("key_concepts", [])[:4]
                sub_questions.append({
                    "question_text": q.get("question_text", ""),
                    "focus_area": q.get("focus_area", "general"),
                    "key_concepts": concepts,
                    "suggested_duration_minutes": q.get("suggested_duration_minutes", 4),
                    "part_number": i + 1,
                })

            # Ensure we have 3 questions
            while len(sub_questions) < 3:
                fallback = self._fallback_oral_sub_question(topic, len(sub_questions) + 1)
                sub_questions.append(fallback)

            return (scenario, sub_questions[:3])
        except (json.JSONDecodeError, KeyError) as e:
            print(f"Failed to parse oral questions response: {e}")
            return self._fallback_oral_questions(topic, track_type)

    def _fallback_oral_questions(self, topic: str, track_type: str) -> tuple[str, list[dict]]:
        """Return deterministic fallback oral questions."""
        scenario = f"Your company is building a scalable {topic} system serving 100M daily active users. The system must handle 10K requests per second with sub-200ms p99 latency and maintain 99.99% availability."
        sub_questions = [
            self._fallback_oral_sub_question(topic, i + 1) for i in range(3)
        ]
        return (scenario, sub_questions)

    def _fallback_oral_sub_question(self, topic: str, part_number: int) -> dict:
        """Return a fallback oral sub-question."""
        fallbacks = [
            {
                "question_text": f"Walk me through how you'd model the data for this {topic} system. What entities and relationships do you need? What storage systems would you choose and why?",
                "focus_area": "Data & Storage",
                "key_concepts": ["data modeling", "storage selection", "access patterns", "schema design"],
                "suggested_duration_minutes": 4,
                "part_number": 1,
            },
            {
                "question_text": f"Design the core processing pipeline for this {topic} system. How does data flow from ingestion to serving? What are the key components?",
                "focus_area": "Core System / ML Pipeline",
                "key_concepts": ["pipeline architecture", "batch vs real-time", "scaling", "fault tolerance"],
                "suggested_duration_minutes": 5,
                "part_number": 2,
            },
            {
                "question_text": f"How would you evaluate and iterate on this {topic} system? What metrics matter? How would you set up experimentation?",
                "focus_area": "Evaluation & Operations",
                "key_concepts": ["A/B testing", "monitoring", "key metrics", "iteration cycle"],
                "suggested_duration_minutes": 4,
                "part_number": 3,
            },
        ]
        idx = (part_number - 1) % len(fallbacks)
        return fallbacks[idx]


# Singleton instance
_system_design_service: Optional[SystemDesignService] = None


def get_system_design_service() -> SystemDesignService:
    """Get or create the SystemDesignService singleton."""
    global _system_design_service
    if _system_design_service is None:
        _system_design_service = SystemDesignService()
    return _system_design_service
