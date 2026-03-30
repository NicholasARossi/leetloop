"""Onsite Prep grading service — category-specific Gemini multimodal rubrics."""

import asyncio
import json
import re
import tempfile
from typing import Optional

import google.generativeai as genai

from app.config import get_settings
from app.models.onsite_prep_schemas import (
    ConversationalFollowUpResult,
    DimensionEvidence,
    DimensionScore,
    IdealResponse,
    OnsitePrepFollowUp,
    OnsitePrepFollowUpResult,
    OnsitePrepGradeResult,
)

# Dimension weights per category (equal for now, can be tuned)
CATEGORY_WEIGHTS = {
    "lp": {
        "star_structure": 1.5,
        "specificity": 1.5,
        "i_vs_we": 2.0,
        "lp_signal": 2.0,
        "timing": 1.0,
        "impact": 2.0,
    },
    "breadth": {
        "definition": 1.5,
        "intuition": 1.5,
        "failure_modes": 1.5,
        "practical_connection": 2.0,
        "timing": 1.0,
        "completeness": 1.5,
    },
    "depth": {
        "architecture_clarity": 1.5,
        "technical_depth": 2.0,
        "design_decisions": 2.0,
        "honest_framing": 1.5,
        "timing": 1.0,
        "metrics_impact": 2.0,
    },
    "design": {
        "problem_framing": 1.5,
        "architecture": 2.0,
        "data_training": 1.5,
        "evaluation": 1.5,
        "production": 1.5,
        "timing_structure": 1.0,
    },
}


class OnsitePrepGradingService:
    """Grades onsite prep responses using Gemini multimodal with category-specific rubrics."""

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
        category: str,
        subcategory: str | None,
        context_hint: str | None,
        target_duration_seconds: int,
    ) -> OnsitePrepGradeResult:
        """Send audio to Gemini for transcription + category-specific rubric grading."""
        if not self.configured:
            raise RuntimeError("Gemini API key not configured")

        prompt = self._build_rubric_prompt(
            question_text, category, subcategory, context_hint, target_duration_seconds
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

            return self._parse_grade_response(response.text, category)

        finally:
            if uploaded_file:
                try:
                    await asyncio.to_thread(genai.delete_file, uploaded_file.name)
                except Exception:
                    pass

    async def generate_follow_up_probes(
        self,
        question_text: str,
        transcript: str,
        category: str,
        dimensions: list[DimensionScore],
        feedback: str,
    ) -> list[str]:
        """Generate targeted follow-up probes based on transcript weaknesses."""
        if not self.configured:
            raise RuntimeError("Gemini API key not configured")

        weak_dims = [d for d in dimensions if d.score < 4]
        weak_summary = ", ".join(f"{d.name} ({d.score}/5)" for d in weak_dims) if weak_dims else "none identified"

        prompt = f"""You are a senior Amazon interviewer conducting a follow-up after the candidate's initial answer.

ORIGINAL QUESTION: "{question_text}"
CATEGORY: {category.upper()}

CANDIDATE'S TRANSCRIPT:
"{transcript}"

WEAK DIMENSIONS: {weak_summary}
FEEDBACK: {feedback}

Generate 2-3 targeted follow-up probes that an interviewer would naturally ask to dig deeper into the gaps. Each probe should:
1. Reference something specific the candidate said (or didn't say)
2. Target a specific weakness or gap
3. Be phrased as a direct question the interviewer would ask
4. Include a brief note about what it targets

For LP stories: probe "I vs we", missing STAR elements, impact quantification, commitment after disagreement
For ML breadth: probe failure modes, practical examples, alternatives they didn't mention
For ML depth: probe honest framing, specific implementation details, what they'd do differently
For system design: probe data strategy, production deployment, cost tradeoffs, scale

Respond in this exact JSON format (no markdown code fences):
{{
  "probes": [
    "You said 'we ran an A/B test.' What was YOUR specific role in designing that test?",
    "What metrics did you track to know this was successful?",
    "If you could redo this, what would you change?"
  ]
}}"""

        response = await asyncio.to_thread(
            self.model.generate_content, [prompt]
        )

        json_match = re.search(r'\{[\s\S]*\}', response.text)
        if not json_match:
            return ["Tell me more about your specific contribution.", "What would you do differently?"]

        data = json.loads(json_match.group())
        return data.get("probes", [])

    async def transcribe_and_grade_follow_up(
        self,
        audio_bytes: bytes,
        mime_type: str,
        original_question: str,
        original_transcript: str,
        follow_up_question: str,
        category: str,
    ) -> OnsitePrepFollowUpResult:
        """Grade a follow-up response with simplified rubric."""
        if not self.configured:
            raise RuntimeError("Gemini API key not configured")

        category_context = {
            "lp": "Amazon behavioral interview",
            "breadth": "ML breadth knowledge check",
            "depth": "deep technical probe on candidate's own projects",
            "design": "system design deep-dive",
        }.get(category, "technical interview")

        prompt = f"""You are a senior Amazon interviewer evaluating a FOLLOW-UP response in a {category_context}.

The candidate was originally asked:
"{original_question}"

Their original response (transcript):
"{original_transcript[:1000]}"

Based on gaps in their answer, this follow-up was asked:
"{follow_up_question}"

First, transcribe the audio response verbatim (include filler words).

Then evaluate:
1. Did the candidate adequately address the gap that prompted this follow-up?
2. Score the response 1-5 (1=no useful content, 2=vague attempt, 3=partial answer, 4=solid answer, 5=exceptional depth)
3. Provide 1-2 sentences of direct feedback

Respond in this exact JSON format (no markdown code fences, just raw JSON):
{{
  "transcript": "full verbatim transcription",
  "score": 3,
  "feedback": "1-2 sentences of actionable feedback",
  "addressed_gap": true
}}

Grade now:"""

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

    async def generate_ideal_response(
        self,
        question_text: str,
        category: str,
        subcategory: str | None,
        context_hint: str | None,
        transcript: str,
        feedback: str,
    ) -> IdealResponse:
        """Generate a personalized L6 ideal response using text-only Gemini call."""
        if not self.configured:
            raise RuntimeError("Gemini API key not configured")

        category_instruction = {
            "lp": "Write the ideal STAR-format answer. Situation should set clear context, Task should specify the candidate's responsibility, Action should use 'I' statements with specific details, and Result should quantify impact with numbers.",
            "breadth": "Write the ideal ML breadth explanation. Start with a precise definition, build intuition with an analogy, cover failure modes and when NOT to use it, and connect to a practical application.",
            "depth": "Write the ideal deep technical walkthrough. Cover architecture clearly enough to whiteboard, explain design decisions with tradeoffs, be honest about limitations, and quantify metrics/impact.",
            "design": "Write the ideal system design walkthrough. Start with problem framing and clarifying questions, lay out architecture, cover data/training strategy, discuss evaluation metrics, and address production concerns.",
        }.get(category, "Write the ideal answer.")

        prompt = f"""You are a senior Amazon L6 Applied Scientist who just gave a perfect interview answer.

QUESTION: "{question_text}"
CATEGORY: {category.upper()}
{f'SUBCATEGORY: {subcategory}' if subcategory else ''}
{f'CANDIDATE CONTEXT (use their actual project/story): {context_hint}' if context_hint else ''}

The candidate gave this answer (use their context but improve it):
"{transcript[:2000]}"

Coach feedback on their answer: {feedback}

{category_instruction}

Write THREE things:
1. A 1-2 sentence summary of the key improvement
2. A 4-6 point outline of what the ideal answer covers
3. The full ideal spoken response (2-3 minutes of natural speech, written as the candidate would say it)

IMPORTANT: Use the candidate's ACTUAL project/story/context from the transcript. Don't invent a different scenario — show how THEIR story should be told better.

Respond in this exact JSON format (no markdown code fences):
{{
  "summary": "The key improvement is...",
  "outline": ["Point 1", "Point 2", "Point 3", "Point 4"],
  "full_response": "The full ideal spoken response..."
}}"""

        response = await asyncio.to_thread(
            self.model.generate_content, [prompt]
        )

        json_match = re.search(r'\{[\s\S]*\}', response.text)
        if not json_match:
            return IdealResponse(
                summary="Could not generate ideal response.",
                outline=[],
                full_response="",
            )

        data = json.loads(json_match.group())
        return IdealResponse(
            summary=data.get("summary", ""),
            outline=data.get("outline", []),
            full_response=data.get("full_response", ""),
        )

    async def transcribe_and_grade_follow_up_conversational(
        self,
        audio_bytes: bytes,
        mime_type: str,
        original_question: str,
        original_transcript: str,
        follow_up_question: str,
        category: str,
        previous_follow_ups: list[dict],
    ) -> dict:
        """Grade a follow-up response AND decide whether another probe is needed.

        Returns dict with: transcript, score, feedback, addressed_gap, next_probe (str|None)
        """
        if not self.configured:
            raise RuntimeError("Gemini API key not configured")

        category_context = {
            "lp": "Amazon behavioral interview",
            "breadth": "ML breadth knowledge check",
            "depth": "deep technical probe on candidate's own projects",
            "design": "system design deep-dive",
        }.get(category, "technical interview")

        # Build conversation context from previous follow-ups
        conversation_ctx = ""
        if previous_follow_ups:
            conversation_ctx = "\n\nPREVIOUS FOLLOW-UP EXCHANGE:\n"
            for pfu in previous_follow_ups[-4:]:  # Last 4 for context window
                conversation_ctx += f'Q: "{pfu.get("question_text", "")}"\n'
                if pfu.get("transcript"):
                    conversation_ctx += f'A: "{pfu["transcript"][:500]}"\n'
                    conversation_ctx += f'Score: {pfu.get("score", "?")}/5\n\n'

        total_follow_ups = len(previous_follow_ups) + 1  # Including current

        prompt = f"""You are a senior Amazon interviewer conducting a follow-up conversation in a {category_context}.

The candidate was originally asked:
"{original_question}"

Their original response (transcript):
"{original_transcript[:1000]}"
{conversation_ctx}
NOW this follow-up was asked:
"{follow_up_question}"

First, transcribe the audio response verbatim (include filler words).

Then evaluate:
1. Did the candidate adequately address the gap that prompted this follow-up?
2. Score the response 1-5 (1=no useful content, 2=vague attempt, 3=partial answer, 4=solid answer, 5=exceptional depth)
3. Provide 1-2 sentences of direct feedback
4. Write what the IDEAL answer to this follow-up would be — a concise, strong response (3-5 sentences) that directly addresses the gap. Use the candidate's own context/project but show the polished version.

Finally, decide if ANOTHER follow-up probe is needed:
- If the answer reveals a new gap or was incomplete, generate one more probing question
- If the answer was solid (4-5) or we've done {total_follow_ups} follow-ups already (max 8), set next_probe to null
- The next probe should build on what the candidate just said, not repeat earlier questions

Respond in this exact JSON format (no markdown code fences, just raw JSON):
{{
  "transcript": "full verbatim transcription",
  "score": 3,
  "feedback": "1-2 sentences of actionable feedback",
  "addressed_gap": true,
  "ideal_answer": "3-5 sentence ideal response to this specific follow-up, using the candidate's context",
  "next_probe": "A follow-up question based on their answer, or null if conversation should end"
}}

Grade now:"""

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

            json_match = re.search(r'\{[\s\S]*\}', response.text)
            if not json_match:
                raise ValueError(f"Could not parse JSON from Gemini response: {response.text[:200]}")

            data = json.loads(json_match.group())
            score = max(1, min(5, int(data.get("score", 1))))

            next_probe = data.get("next_probe")
            # Cap at 8 total follow-ups
            if total_follow_ups >= 8:
                next_probe = None

            return {
                "transcript": data.get("transcript", ""),
                "score": score,
                "feedback": data.get("feedback", ""),
                "addressed_gap": bool(data.get("addressed_gap", False)),
                "ideal_answer": data.get("ideal_answer", ""),
                "next_probe": next_probe,
            }

        finally:
            if uploaded_file:
                try:
                    await asyncio.to_thread(genai.delete_file, uploaded_file.name)
                except Exception:
                    pass

    def _build_rubric_prompt(
        self,
        question_text: str,
        category: str,
        subcategory: str | None,
        context_hint: str | None,
        target_duration_seconds: int,
    ) -> str:
        """Dispatch to the correct category-specific prompt builder."""
        builders = {
            "lp": self._build_lp_rubric_prompt,
            "breadth": self._build_breadth_rubric_prompt,
            "depth": self._build_depth_rubric_prompt,
            "design": self._build_design_rubric_prompt,
        }
        builder = builders.get(category, self._build_lp_rubric_prompt)
        return builder(question_text, subcategory, context_hint, target_duration_seconds)

    def _build_lp_rubric_prompt(self, question_text, subcategory, context_hint, target_seconds):
        target_min = target_seconds // 60
        return f"""You are a senior Amazon interviewer (Bar Raiser level) evaluating a BEHAVIORAL response for the "{subcategory or 'Leadership Principle'}" principle.

QUESTION ASKED:
"{question_text}"

{f'MAPPED STORY CONTEXT: {context_hint}' if context_hint else ''}
TARGET DURATION: {target_min} minutes

First, transcribe the audio response verbatim (include filler words like um, uh).

Then grade using this rubric. CITE SPECIFIC QUOTES from the transcript to justify each score.

## RUBRIC (each dimension scored 1-5)

### 1. STAR Structure
Is Situation, Task, Action, Result each clearly present and distinct?
- 1-2: Missing 2+ STAR elements or they blur together
- 3: All elements present but Situation/Task overlap or Result is vague
- 4: Clean STAR with clear transitions between each section
- 5: Textbook STAR — interviewer never has to guess which section they're in

### 2. Specificity
Does the candidate use concrete details — numbers, dates, team sizes, tool names?
- 1-2: Entirely vague. "We improved the system." No numbers, no context.
- 3: Some specifics but key numbers missing (no impact quantification)
- 4: Good specifics — team size, timeline, metric deltas
- 5: Rich detail — exact numbers, before/after, named tools and frameworks

### 3. "I" vs "We"
Is the candidate's personal contribution clear, or are they hiding behind the team?
- 1-2: Almost entirely "we" — impossible to tell what they personally did
- 3: Mix of "I" and "we" but their specific role is sometimes unclear
- 4: Clearly distinguishes personal actions from team context
- 5: Every action is "I did X" with team context only for framing

### 4. LP Signal
Does the answer clearly demonstrate the target Leadership Principle?
- 1-2: The story doesn't connect to the LP at all
- 3: Vaguely connected but interviewer has to stretch to see the LP
- 4: Clear LP signal — the story naturally demonstrates the principle
- 5: The story IS the LP — impossible to hear it without thinking of that principle

### 5. Timing
Is the answer well-paced and within the target duration?
- 1-2: Way over/under target, poor pacing, rushing or meandering
- 3: Slightly over target, or rushed through key sections
- 4: Close to target, good pacing overall
- 5: Perfect pacing, each STAR section gets proportional time

### 6. Impact
Is the Result quantified and meaningful?
- 1-2: No result, or result is "it worked" with no specifics
- 3: Has a result but no quantification ("we saw improvement")
- 4: Quantified result (metric delta, business impact, timeline)
- 5: Multiple quantified impacts — technical metric + business metric + team impact

---

## GRADING RULES
1. CITE EVIDENCE. Quote 1-2 specific phrases (10+ words) from the transcript per dimension.
2. DIFFERENTIATE SCORES. Scores should NOT all be within 1 point of each other.
3. ORAL-SPECIFIC. Expect some filler words — penalize patterns, not individual "um"s.
4. Be a TOUGH but FAIR grader. A 3 is average/acceptable, 4 is good, 5 is exceptional.

Respond in this exact JSON format (no markdown code fences, just raw JSON):
{{
  "transcript": "full verbatim transcription",
  "dimensions": [
    {{"name": "star_structure", "score": 4, "evidence": [{{"quote": "...", "analysis": "..."}}], "summary": "..."}},
    {{"name": "specificity", "score": 3, "evidence": [{{"quote": "...", "analysis": "..."}}], "summary": "..."}},
    {{"name": "i_vs_we", "score": 2, "evidence": [{{"quote": "...", "analysis": "..."}}], "summary": "..."}},
    {{"name": "lp_signal", "score": 4, "evidence": [{{"quote": "...", "analysis": "..."}}], "summary": "..."}},
    {{"name": "timing", "score": 3, "evidence": [{{"quote": "...", "analysis": "..."}}], "summary": "..."}},
    {{"name": "impact", "score": 3, "evidence": [{{"quote": "...", "analysis": "..."}}], "summary": "..."}}
  ],
  "feedback": "2-3 sentences of direct, actionable feedback",
  "strongest_moment": "quoted from transcript",
  "weakest_moment": "described",
  "follow_up_questions": ["2-3 probing follow-ups based on gaps"]
}}

Grade now:"""

    def _build_breadth_rubric_prompt(self, question_text, subcategory, context_hint, target_seconds):
        target_min = target_seconds // 60
        return f"""You are a senior Amazon Applied Science interviewer evaluating an ML BREADTH response.

QUESTION ASKED:
"{question_text}"

{f'TOPIC AREA: {subcategory}' if subcategory else ''}
{f'KEY CONCEPTS: {context_hint}' if context_hint else ''}
TARGET DURATION: {target_min} minutes

First, transcribe the audio response verbatim (include filler words).

Then grade using this rubric. CITE SPECIFIC QUOTES from the transcript.

## RUBRIC (each dimension scored 1-5)

### 1. Definition
Does the candidate define the concept correctly and precisely?
- 1-2: Wrong or missing definition
- 3: Roughly correct but imprecise or missing key nuance
- 4: Correct definition with key properties identified
- 5: Precise mathematical/technical definition with edge cases noted

### 2. Intuition
Can the candidate explain WHY it works, not just WHAT it is?
- 1-2: No intuition — just recites definition
- 3: Some intuition but stays abstract
- 4: Good analogy or concrete explanation of the mechanism
- 5: Builds genuine understanding — interviewer learns something

### 3. Failure Modes
Does the candidate know when the method breaks?
- 1-2: No mention of limitations
- 3: Mentions one limitation but superficially
- 4: Identifies key failure modes with concrete examples
- 5: Discusses failure modes AND how to detect/mitigate them

### 4. Practical Connection
Does the candidate connect theory to real-world application?
- 1-2: Entirely textbook, no practical grounding
- 3: Mentions an application but doesn't go deep
- 4: Concrete example from their work or a real system
- 5: Rich practical example with specific design choices and tradeoffs

### 5. Timing
Is the answer well-paced within the target?
- 1-2: Way over/under, or rushed key parts
- 3: Slightly off-target
- 4: Good pacing
- 5: Perfect pacing with clear structure

### 6. Completeness
Did the candidate cover the full scope of the question?
- 1-2: Major gaps — missed half the question
- 3: Covered most parts but skipped an important aspect
- 4: Complete coverage with minor gaps
- 5: Thorough — addressed every part with depth

---

## GRADING RULES
1. CITE EVIDENCE. Quote 1-2 specific phrases per dimension.
2. DIFFERENTIATE SCORES. Be honest about relative strengths.
3. This is a KNOWLEDGE check — depth of understanding matters more than delivery.

Respond in this exact JSON format (no markdown code fences, just raw JSON):
{{
  "transcript": "full verbatim transcription",
  "dimensions": [
    {{"name": "definition", "score": 4, "evidence": [{{"quote": "...", "analysis": "..."}}], "summary": "..."}},
    {{"name": "intuition", "score": 3, "evidence": [{{"quote": "...", "analysis": "..."}}], "summary": "..."}},
    {{"name": "failure_modes", "score": 3, "evidence": [{{"quote": "...", "analysis": "..."}}], "summary": "..."}},
    {{"name": "practical_connection", "score": 4, "evidence": [{{"quote": "...", "analysis": "..."}}], "summary": "..."}},
    {{"name": "timing", "score": 4, "evidence": [{{"quote": "...", "analysis": "..."}}], "summary": "..."}},
    {{"name": "completeness", "score": 3, "evidence": [{{"quote": "...", "analysis": "..."}}], "summary": "..."}}
  ],
  "feedback": "2-3 sentences of direct, actionable feedback",
  "strongest_moment": "quoted from transcript",
  "weakest_moment": "described",
  "follow_up_questions": ["2-3 probing follow-ups"]
}}

Grade now:"""

    def _build_depth_rubric_prompt(self, question_text, subcategory, context_hint, target_seconds):
        target_min = target_seconds // 60
        return f"""You are a senior Amazon Applied Science interviewer evaluating a DEEP TECHNICAL response about the candidate's OWN projects.

QUESTION ASKED:
"{question_text}"

{f'TOPIC: {subcategory}' if subcategory else ''}
{f'CONTEXT: {context_hint}' if context_hint else ''}
TARGET DURATION: {target_min} minutes

First, transcribe the audio response verbatim (include filler words).

Then grade using this rubric. CITE SPECIFIC QUOTES.

## RUBRIC (each dimension scored 1-5)

### 1. Architecture Clarity
Can the interviewer draw the system from the candidate's description?
- 1-2: Jumbled — components mentioned randomly without flow
- 3: General flow described but missing key connections
- 4: Clear end-to-end pipeline with components and data flow
- 5: Could be whiteboarded directly — every component named, connected, justified

### 2. Technical Depth
Does the candidate go beyond "I used X"?
- 1-2: Name-drops tools without justification
- 3: Basic rationale but no config, params, or failure handling
- 4: Discusses specific configurations, hyperparameters, or failure scenarios
- 5: Production-level detail — memory, compute, throughput, edge cases

### 3. Design Decisions
Does the candidate explain WHY, not just WHAT?
- 1-2: No alternatives considered
- 3: Mentions one alternative but doesn't deeply compare
- 4: Compares 2+ options on specific criteria
- 5: Frames as tradeoff matrix, discusses when their choice would be wrong

### 4. Honest Framing
Is the candidate calibrated about what they built?
- 1-2: Overstates (calls simple SFT "RL", etc.)
- 3: Mostly honest but stretches terminology
- 4: Accurately describes what they built, acknowledges limitations
- 5: Proactively disambiguates — "this is RL-inspired, not classical RL because..."

### 5. Timing
Well-paced within target?
- 1-2: Way over or rushed
- 3: Slightly off
- 4: Good pacing
- 5: Perfect pacing

### 6. Metrics & Impact
Does the candidate quantify results?
- 1-2: No metrics mentioned
- 3: One vague metric ("it improved")
- 4: Specific metrics (recall delta, latency, etc.)
- 5: Multiple metrics with before/after AND business translation

---

## GRADING RULES
1. CITE EVIDENCE per dimension.
2. DIFFERENTIATE SCORES.
3. This probes THEIR work — grade on ownership signal and technical command.
4. Honest Framing is CRITICAL for Amazon Applied Scientist interviews.

Respond in this exact JSON format (no markdown code fences, just raw JSON):
{{
  "transcript": "full verbatim transcription",
  "dimensions": [
    {{"name": "architecture_clarity", "score": 4, "evidence": [{{"quote": "...", "analysis": "..."}}], "summary": "..."}},
    {{"name": "technical_depth", "score": 3, "evidence": [{{"quote": "...", "analysis": "..."}}], "summary": "..."}},
    {{"name": "design_decisions", "score": 3, "evidence": [{{"quote": "...", "analysis": "..."}}], "summary": "..."}},
    {{"name": "honest_framing", "score": 3, "evidence": [{{"quote": "...", "analysis": "..."}}], "summary": "..."}},
    {{"name": "timing", "score": 4, "evidence": [{{"quote": "...", "analysis": "..."}}], "summary": "..."}},
    {{"name": "metrics_impact", "score": 4, "evidence": [{{"quote": "...", "analysis": "..."}}], "summary": "..."}}
  ],
  "feedback": "2-3 sentences of direct, actionable feedback",
  "strongest_moment": "quoted from transcript",
  "weakest_moment": "described",
  "follow_up_questions": ["2-3 probing follow-ups"]
}}

Grade now:"""

    def _build_design_rubric_prompt(self, question_text, subcategory, context_hint, target_seconds):
        target_min = target_seconds // 60
        return f"""You are a senior Amazon system design interviewer evaluating an ML SYSTEM DESIGN walkthrough.

QUESTION ASKED:
"{question_text}"

{f'FOCUS: {subcategory}' if subcategory else ''}
{f'CONTEXT: {context_hint}' if context_hint else ''}
TARGET DURATION: {target_min} minutes (this is a longer-form design, not a quick answer)

First, transcribe the audio response verbatim (include filler words).

Then grade using this rubric. CITE SPECIFIC QUOTES.

## RUBRIC (each dimension scored 1-5)

### 1. Problem Framing
Does the candidate clarify scope and constraints before diving in?
- 1-2: Jumps straight to solution with no scoping
- 3: Briefly mentions scope but doesn't clarify key constraints
- 4: Asks good clarifying questions, states assumptions
- 5: Methodical scoping — latency, scale, user types, success metrics defined upfront

### 2. Architecture
Is the overall system design sound?
- 1-2: No coherent architecture
- 3: Has a general approach but components are vague
- 4: Clear multi-component architecture with data flow
- 5: Production-grade design — could be built from this description

### 3. Data & Training
Does the candidate address the ML lifecycle?
- 1-2: No mention of data or training
- 3: Mentions training data but doesn't discuss sourcing, labeling, or quality
- 4: Discusses data strategy, feature engineering, model training approach
- 5: Full ML lifecycle — data collection, labeling strategy, training, validation, iteration

### 4. Evaluation
How does the candidate measure success?
- 1-2: No evaluation discussion
- 3: Mentions one metric
- 4: Offline and online metrics, discusses tradeoffs
- 5: Full eval strategy — offline metrics, A/B testing, guardrails, cost asymmetry

### 5. Production
Does the candidate consider deployment and operations?
- 1-2: No production discussion
- 3: Mentions deployment briefly
- 4: Discusses serving, monitoring, or scaling
- 5: Production-ready — staged rollout, monitoring, drift detection, fallbacks

### 6. Timing & Structure
Is the walkthrough well-structured and paced?
- 1-2: Chaotic, no structure
- 3: Loose structure, some backtracking
- 4: Clear sections, good flow
- 5: Signposted transitions, systematic progression, good time allocation

---

## GRADING RULES
1. CITE EVIDENCE per dimension.
2. DIFFERENTIATE SCORES.
3. This is a DESIGN interview — breadth of coverage AND depth in key areas both matter.
4. Connecting to personal experience is a strong positive.

Respond in this exact JSON format (no markdown code fences, just raw JSON):
{{
  "transcript": "full verbatim transcription",
  "dimensions": [
    {{"name": "problem_framing", "score": 4, "evidence": [{{"quote": "...", "analysis": "..."}}], "summary": "..."}},
    {{"name": "architecture", "score": 3, "evidence": [{{"quote": "...", "analysis": "..."}}], "summary": "..."}},
    {{"name": "data_training", "score": 3, "evidence": [{{"quote": "...", "analysis": "..."}}], "summary": "..."}},
    {{"name": "evaluation", "score": 3, "evidence": [{{"quote": "...", "analysis": "..."}}], "summary": "..."}},
    {{"name": "production", "score": 3, "evidence": [{{"quote": "...", "analysis": "..."}}], "summary": "..."}},
    {{"name": "timing_structure", "score": 4, "evidence": [{{"quote": "...", "analysis": "..."}}], "summary": "..."}}
  ],
  "feedback": "2-3 sentences of direct, actionable feedback",
  "strongest_moment": "quoted from transcript",
  "weakest_moment": "described",
  "follow_up_questions": ["2-3 probing follow-ups"]
}}

Grade now:"""

    def _parse_grade_response(self, text: str, category: str) -> OnsitePrepGradeResult:
        """Parse Gemini's JSON response and compute overall score in code."""
        json_match = re.search(r'\{[\s\S]*\}', text)
        if not json_match:
            raise ValueError(f"Could not parse JSON from Gemini response: {text[:200]}")

        data = json.loads(json_match.group())

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

        overall_score = self._compute_overall_score(dimensions, category)
        verdict = self._compute_verdict(overall_score)

        return OnsitePrepGradeResult(
            transcript=data.get("transcript", ""),
            dimensions=dimensions,
            overall_score=round(overall_score, 1),
            verdict=verdict,
            feedback=data.get("feedback", ""),
            strongest_moment=data.get("strongest_moment", ""),
            weakest_moment=data.get("weakest_moment", ""),
            follow_up_questions=data.get("follow_up_questions", []),
        )

    def _compute_overall_score(self, dimensions: list[DimensionScore], category: str) -> float:
        """Weighted average using category-specific weights."""
        weights = CATEGORY_WEIGHTS.get(category, {})
        weighted_sum = 0.0
        total_weight = 0.0
        for dim in dimensions:
            weight = weights.get(dim.name, 1.0)
            weighted_sum += dim.score * weight
            total_weight += weight

        if total_weight == 0:
            return 0.0
        return weighted_sum / total_weight

    @staticmethod
    def _compute_verdict(overall_score: float) -> str:
        """pass (>= 4), borderline (3-3.9), fail (< 3)."""
        if overall_score >= 4:
            return "pass"
        elif overall_score >= 3:
            return "borderline"
        else:
            return "fail"

    def _parse_follow_up_response(self, text: str) -> OnsitePrepFollowUpResult:
        """Parse Gemini's follow-up grading response."""
        json_match = re.search(r'\{[\s\S]*\}', text)
        if not json_match:
            raise ValueError(f"Could not parse JSON from Gemini response: {text[:200]}")

        data = json.loads(json_match.group())
        score = max(1, min(5, int(data.get("score", 1))))

        return OnsitePrepFollowUpResult(
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
_onsite_prep_grading_service: Optional[OnsitePrepGradingService] = None


def get_onsite_prep_grading_service() -> OnsitePrepGradingService:
    """Get or create the onsite prep grading service singleton."""
    global _onsite_prep_grading_service
    if _onsite_prep_grading_service is None:
        _onsite_prep_grading_service = OnsitePrepGradingService()
    return _onsite_prep_grading_service
