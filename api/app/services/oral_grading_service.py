"""Oral grading service — Gemini multimodal audio transcription + rubric evaluation."""

import asyncio
import json
import re
import tempfile
from typing import Optional

import google.generativeai as genai

from app.config import get_settings
from app.models.system_design_schemas import (
    DimensionEvidence,
    DimensionScore,
    FollowUpGradeResult,
    OralGradeResult,
)

# Dimension weights for overall score computation
DIMENSION_WEIGHTS = {
    "technical_depth": 2.0,
    "structure_and_approach": 1.5,
    "tradeoff_reasoning": 2.0,
    "ml_data_fluency": 2.0,
    "communication_quality": 1.5,
}
TOTAL_WEIGHT = sum(DIMENSION_WEIGHTS.values())  # 9.0


class OralGradingService:
    """
    Grades oral system design responses using Gemini multimodal.

    Sends audio directly to Gemini for combined transcription + evaluation
    with a 5-dimension anchored rubric and mandatory citation of evidence.
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

    async def transcribe_and_grade(
        self,
        audio_bytes: bytes,
        mime_type: str,
        question_text: str,
        focus_area: str,
        key_concepts: list[str],
        track_type: str,
        suggested_duration: int,
    ) -> OralGradeResult:
        """
        Send audio to Gemini multimodal for transcription + grading in one call.

        Returns OralGradeResult with transcript, 5 dimension scores (with cited
        evidence), overall score (computed in code), verdict, feedback, and
        follow-up questions.
        """
        if not self.configured:
            raise RuntimeError("Gemini API key not configured")

        prompt = self._build_oral_grading_prompt(
            question_text, focus_area, key_concepts, track_type, suggested_duration
        )

        # Write audio to temp file for Gemini upload
        suffix = _mime_to_extension(mime_type)
        uploaded_file = None
        try:
            with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
                tmp.write(audio_bytes)
                tmp_path = tmp.name

            uploaded_file = await asyncio.to_thread(
                genai.upload_file, tmp_path, mime_type=mime_type
            )

            response = await asyncio.to_thread(
                self.model.generate_content, [prompt, uploaded_file]
            )

            return self._parse_grade_response(response.text)

        finally:
            # Clean up uploaded file from Gemini
            if uploaded_file:
                try:
                    await asyncio.to_thread(genai.delete_file, uploaded_file.name)
                except Exception:
                    pass  # Best-effort cleanup

    def _build_oral_grading_prompt(
        self,
        question_text: str,
        focus_area: str,
        key_concepts: list[str],
        track_type: str,
        suggested_duration: int,
    ) -> str:
        """Build the full rubric prompt with behavioral anchors and citation rules."""
        concepts_str = ", ".join(key_concepts)

        return f"""You are a senior system design interviewer at Google/Amazon evaluating an Applied Scientist candidate's ORAL response.

QUESTION ASKED:
"{question_text}"

FOCUS AREA: {focus_area}
KEY CONCEPTS: {concepts_str}
TRACK TYPE: {track_type.upper()}
SUGGESTED DURATION: {suggested_duration} minutes

First, transcribe the audio response verbatim (include filler words like um, uh).

Then grade using this rubric. IMPORTANT: You must CITE SPECIFIC QUOTES from the transcript to justify each score.

---

## RUBRIC (each dimension scored 1-10)

### 1. Technical Depth
How deep does the candidate go beyond "I'd use X"?

Score anchors:
- 2-3 (Surface): Names technologies without justification. "I'd use Kafka." No why, no config, no failure modes.
- 4-5 (Shallow): Mentions technologies with basic rationale but no edge cases or numbers. "I'd use Kafka because it handles high throughput" but no partition strategy, retention, or capacity estimate.
- 6-7 (Solid): Discusses specific configurations, capacity estimates, or failure scenarios for at least some components.
- 8-9 (Expert): Proactively addresses failure modes, capacity planning with math, implementation details showing real experience.

### 2. Structure & Approach
Does the candidate have a framework, or are they stream-of-consciousness?

- 2-3 (Chaotic): Jumps between topics randomly. Starts implementing before scoping.
- 4-5 (Loose): Has a general direction but backtracks frequently. "Oh wait, I should have mentioned..."
- 6-7 (Organized): Clear sections with signposted transitions. Covers question scope without major tangents.
- 8-9 (Exemplary): Opens with clarifying scope, states assumptions, builds high-level to detail systematically.

### 3. Trade-off Reasoning
Does the candidate weigh alternatives, or just present one solution?

- 2-3 (None): Presents one solution as the only option.
- 4-5 (Surface): Mentions alternatives exist but does not deeply compare.
- 6-7 (Thoughtful): Explicitly compares 2+ options on specific criteria (latency, cost, consistency).
- 8-9 (Rigorous): Frames decisions as trade-off matrices. Discusses when their choice would be wrong.

### 4. ML/Data Fluency
Does the candidate demonstrate working knowledge of ML systems and data pipelines?

- 2-3 (Textbook): Mentions ML concepts by name only. "We'd use collaborative filtering."
- 4-5 (Basic): Understands ML pipeline at high level but stays abstract. No feature engineering or evaluation discussion.
- 6-7 (Practitioner): Discusses specific feature types, model architectures with rationale, training/serving split. Aware of cold start, data drift, etc.
- 8-9 (Expert): Connects ML choices to business metrics. Discusses feature stores, experiment frameworks, model monitoring.

### 5. Communication Quality
Would an interviewer enjoy listening to this?

- 2-3 (Hard to follow): Excessive filler words. Long pauses. Contradicts self without correction.
- 4-5 (Passable): Gets the point across but with significant filler, repetition, or tangents. Ideas buried in verbal noise.
- 6-7 (Clear): Mostly fluent with occasional filler. Uses transitions. Self-corrects cleanly.
- 8-9 (Polished): Confident delivery. Minimal filler. Concise. Sounds experienced.

---

## GRADING RULES
1. CITE EVIDENCE. For every dimension, quote 1-2 specific phrases (at least 10 words each) from the transcript that justify the score.
2. DIFFERENTIATE SCORES. It is extremely unlikely all dimensions score within 1 point of each other. Really think about relative strengths vs weaknesses.
3. SCOPE TO THE QUESTION. This question is about {focus_area} only. Do NOT penalize for not covering topics outside the focus area.
4. DURATION. Suggested was {suggested_duration} minutes. Factor the actual duration into Structure score.
5. ORAL-SPECIFIC. This is a spoken response. Expect some natural filler — penalize patterns, not individual "um"s.

Respond in this exact JSON format (no markdown code fences, just raw JSON):
{{
  "transcript": "full verbatim transcription including filler words",
  "dimensions": [
    {{
      "name": "technical_depth",
      "score": 5,
      "evidence": [
        {{"quote": "exact quote from transcript at least 10 words", "analysis": "why this justifies this score"}}
      ],
      "summary": "one sentence justification"
    }},
    {{
      "name": "structure_and_approach",
      "score": 4,
      "evidence": [{{"quote": "...", "analysis": "..."}}],
      "summary": "..."
    }},
    {{
      "name": "tradeoff_reasoning",
      "score": 3,
      "evidence": [{{"quote": "...", "analysis": "..."}}],
      "summary": "..."
    }},
    {{
      "name": "ml_data_fluency",
      "score": 6,
      "evidence": [{{"quote": "...", "analysis": "..."}}],
      "summary": "..."
    }},
    {{
      "name": "communication_quality",
      "score": 4,
      "evidence": [{{"quote": "...", "analysis": "..."}}],
      "summary": "..."
    }}
  ],
  "feedback": "2-3 sentences of direct, actionable feedback",
  "missed_concepts": ["only concepts relevant to THIS question"],
  "strongest_moment": "the single best thing they said, quoted from transcript",
  "weakest_moment": "the single worst gap or mistake, described",
  "follow_up_questions": ["2-3 probing follow-ups based on gaps in THIS answer"]
}}

Grade now:"""

    def _parse_grade_response(self, text: str) -> OralGradeResult:
        """Parse Gemini's JSON response and compute overall score + verdict in code."""
        # Extract JSON from response (handle optional markdown fences)
        json_match = re.search(r'\{[\s\S]*\}', text)
        if not json_match:
            raise ValueError(f"Could not parse JSON from Gemini response: {text[:200]}")

        data = json.loads(json_match.group())

        # Parse dimensions
        dimensions = []
        for dim_data in data.get("dimensions", []):
            evidence = [
                DimensionEvidence(quote=e.get("quote", ""), analysis=e.get("analysis", ""))
                for e in dim_data.get("evidence", [])
            ]
            dimensions.append(DimensionScore(
                name=dim_data.get("name", ""),
                score=int(dim_data.get("score", 1)),
                evidence=evidence,
                summary=dim_data.get("summary", ""),
            ))

        # Compute overall score IN CODE (not trusting model)
        overall_score = self._compute_overall_score(dimensions)

        # Compute verdict IN CODE
        verdict = self._compute_verdict(overall_score)

        return OralGradeResult(
            transcript=data.get("transcript", ""),
            dimensions=dimensions,
            overall_score=round(overall_score, 1),
            verdict=verdict,
            feedback=data.get("feedback", ""),
            missed_concepts=data.get("missed_concepts", []),
            strongest_moment=data.get("strongest_moment", ""),
            weakest_moment=data.get("weakest_moment", ""),
            follow_up_questions=data.get("follow_up_questions", []),
        )

    def _compute_overall_score(self, dimensions: list[DimensionScore]) -> float:
        """Weighted average: tech*2 + structure*1.5 + tradeoffs*2 + ml*2 + comm*1.5 / 9."""
        weighted_sum = 0.0
        total_weight = 0.0
        for dim in dimensions:
            weight = DIMENSION_WEIGHTS.get(dim.name, 1.0)
            weighted_sum += dim.score * weight
            total_weight += weight

        if total_weight == 0:
            return 0.0
        return weighted_sum / total_weight

    @staticmethod
    def _compute_verdict(overall_score: float) -> str:
        """pass (>= 7), borderline (5-6.9), fail (< 5)."""
        if overall_score >= 7:
            return "pass"
        elif overall_score >= 5:
            return "borderline"
        else:
            return "fail"

    async def transcribe_and_grade_follow_up(
        self,
        audio_bytes: bytes,
        mime_type: str,
        original_question_text: str,
        original_transcript: str,
        follow_up_question: str,
    ) -> FollowUpGradeResult:
        """
        Grade a follow-up question response with a simplified rubric.

        Uses the same Gemini upload pattern but with a lighter prompt:
        just transcript, score (1-10), feedback, and whether the gap was addressed.
        """
        if not self.configured:
            raise RuntimeError("Gemini API key not configured")

        prompt = self._build_follow_up_prompt(
            original_question_text, original_transcript, follow_up_question
        )

        suffix = _mime_to_extension(mime_type)
        uploaded_file = None
        try:
            with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
                tmp.write(audio_bytes)
                tmp_path = tmp.name

            uploaded_file = await asyncio.to_thread(
                genai.upload_file, tmp_path, mime_type=mime_type
            )

            response = await asyncio.to_thread(
                self.model.generate_content, [prompt, uploaded_file]
            )

            return self._parse_follow_up_response(response.text)

        finally:
            if uploaded_file:
                try:
                    await asyncio.to_thread(genai.delete_file, uploaded_file.name)
                except Exception:
                    pass

    def _build_follow_up_prompt(
        self,
        original_question_text: str,
        original_transcript: str,
        follow_up_question: str,
    ) -> str:
        """Build a simplified prompt for grading a follow-up response."""
        return f"""You are a senior system design interviewer evaluating a FOLLOW-UP response.

The candidate was originally asked:
"{original_question_text}"

Their original response (transcript):
"{original_transcript}"

Based on gaps in their answer, this follow-up was asked:
"{follow_up_question}"

First, transcribe the audio response verbatim (include filler words).

Then evaluate:
1. Did the candidate adequately address the gap that prompted this follow-up?
2. Score the response 1-10 (1=no useful content, 5=partial answer, 7=solid answer, 10=exceptional depth)
3. Provide 1-2 sentences of direct feedback

Respond in this exact JSON format (no markdown code fences, just raw JSON):
{{
  "transcript": "full verbatim transcription",
  "score": 6,
  "feedback": "1-2 sentences of actionable feedback",
  "addressed_gap": true
}}

Grade now:"""

    def _parse_follow_up_response(self, text: str) -> FollowUpGradeResult:
        """Parse Gemini's JSON response for a follow-up grading."""
        json_match = re.search(r'\{[\s\S]*\}', text)
        if not json_match:
            raise ValueError(f"Could not parse JSON from Gemini response: {text[:200]}")

        data = json.loads(json_match.group())

        score = int(data.get("score", 1))
        score = max(1, min(10, score))

        return FollowUpGradeResult(
            transcript=data.get("transcript", ""),
            score=score,
            feedback=data.get("feedback", ""),
            addressed_gap=bool(data.get("addressed_gap", False)),
        )


def _mime_to_extension(mime_type: str) -> str:
    """Convert MIME type to file extension."""
    mapping = {
        "audio/webm": ".webm",
        "audio/mp4": ".m4a",
        "audio/x-m4a": ".m4a",
        "audio/mpeg": ".mp3",
        "audio/wav": ".wav",
        "audio/x-wav": ".wav",
    }
    return mapping.get(mime_type, ".audio")


# Singleton
_oral_grading_service: Optional[OralGradingService] = None


def get_oral_grading_service() -> OralGradingService:
    """Get or create the oral grading service singleton."""
    global _oral_grading_service
    if _oral_grading_service is None:
        _oral_grading_service = OralGradingService()
    return _oral_grading_service
