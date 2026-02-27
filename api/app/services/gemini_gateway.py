"""Centralized gateway for Google Gemini AI calls."""

import asyncio
from typing import AsyncGenerator, Optional

import google.generativeai as genai

from app.config import get_settings
from app.models.schemas import ChatMessage


class GeminiGateway:
    """
    Gateway for all Gemini AI interactions.

    Handles:
    - Chat conversations
    - Code analysis
    - Tip generation
    - Streaming responses
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

    async def chat(
        self,
        message: str,
        history: list[ChatMessage] = None,
        system_context: str = "",
    ) -> str:
        """
        Generate a chat response.

        Args:
            message: User's message
            history: Previous conversation history
            system_context: Additional context about the user

        Returns:
            AI-generated response string
        """
        if not self.configured:
            return self._fallback_response(message)

        # Build conversation
        system_prompt = self._build_system_prompt(system_context)
        messages = self._build_messages(history, message, system_prompt)

        try:
            response = await asyncio.to_thread(self.model.generate_content, messages)
            return response.text
        except Exception as e:
            return f"I apologize, but I encountered an error: {str(e)}"

    async def chat_stream(
        self,
        message: str,
        history: list[ChatMessage] = None,
        system_context: str = "",
    ) -> AsyncGenerator[str, None]:
        """
        Stream a chat response chunk by chunk.

        Yields:
            Response text chunks
        """
        if not self.configured:
            yield self._fallback_response(message)
            return

        system_prompt = self._build_system_prompt(system_context)
        messages = self._build_messages(history, message, system_prompt)

        try:
            response = await asyncio.to_thread(lambda: self.model.generate_content(messages, stream=True))
            for chunk in response:
                if chunk.text:
                    yield chunk.text
        except Exception as e:
            yield f"Error: {str(e)}"

    async def analyze_code(
        self,
        code: str,
        language: str,
        problem_slug: str,
        status: str,
        code_output: str = None,
        expected_output: str = None,
        status_msg: str = None,
        total_correct: int = None,
        total_testcases: int = None,
        previous_attempts: list = None,
    ) -> dict:
        """
        Analyze submitted code for issues and improvements.

        Returns:
            Dictionary with analysis results
        """
        if not self.configured:
            return {
                "summary": "AI analysis unavailable - API key not configured",
                "issues": [],
                "suggestions": ["Configure Google API key for code analysis"],
                "time_complexity": None,
                "space_complexity": None,
                "root_cause": None,
                "the_fix": None,
                "pattern_type": None,
                "concept_gap": None,
            }

        # Build status-specific context
        error_context = self._build_error_context(
            status, code_output, expected_output, status_msg,
            total_correct, total_testcases,
        )

        # Build previous attempts section
        attempts_section = ""
        if previous_attempts:
            attempts_section = "\n## Previous Attempts on This Problem\n"
            for i, attempt in enumerate(previous_attempts, 1):
                attempts_section += f"Attempt {i}: {attempt.get('status', 'Unknown')}"
                if attempt.get('status_msg'):
                    attempts_section += f" — {attempt['status_msg']}"
                if attempt.get('total_correct') is not None and attempt.get('total_testcases') is not None:
                    attempts_section += f" ({attempt['total_correct']}/{attempt['total_testcases']} test cases)"
                attempts_section += f" [{attempt.get('language', language)}]\n"

        prompt = f"""Analyze this {language} code submission for the LeetCode problem "{problem_slug}".
The submission result was: {status}

{error_context}
{attempts_section}
Code:
```{language}
{code}
```

Respond with ONLY valid JSON (no markdown fences, no extra text):
{{
  "summary": "One sentence describing what the code attempts",
  "root_cause": "Specific cause of the {status} result",
  "the_fix": "Exact code change needed (describe the diff)",
  "pattern_type": "One of: off-by-one | wrong-data-structure | missing-edge-case | brute-force | incorrect-algorithm | wrong-traversal-order | integer-overflow | null-reference | other",
  "concept_gap": "Underlying concept the user should study",
  "issues": ["Issue 1", "Issue 2"],
  "suggestions": ["Suggestion 1", "Suggestion 2"],
  "time_complexity": "O(...)",
  "space_complexity": "O(...)"
}}"""

        try:
            response = await asyncio.to_thread(self.model.generate_content, prompt)
            return self._parse_json_analysis(response.text)
        except Exception as e:
            return {
                "summary": f"Analysis failed: {str(e)}",
                "issues": [],
                "suggestions": [],
                "time_complexity": None,
                "space_complexity": None,
                "root_cause": None,
                "the_fix": None,
                "pattern_type": None,
                "concept_gap": None,
            }

    def _build_error_context(
        self,
        status: str,
        code_output: str = None,
        expected_output: str = None,
        status_msg: str = None,
        total_correct: int = None,
        total_testcases: int = None,
    ) -> str:
        """Build status-specific error context for the analysis prompt."""
        parts = []

        if status == "Wrong Answer":
            parts.append("## Failure Details: Wrong Answer")
            if code_output and expected_output:
                parts.append(f"Your output:    {code_output}")
                parts.append(f"Expected output: {expected_output}")
            if total_correct is not None and total_testcases is not None:
                parts.append(f"Test cases passed: {total_correct}/{total_testcases}")
                if total_testcases > 0:
                    pct = total_correct / total_testcases * 100
                    if pct > 90:
                        parts.append("(Very close — likely an edge case issue)")
                    elif pct < 50:
                        parts.append("(Fundamental logic issue — most cases fail)")

        elif status in ("Time Limit Exceeded", "Memory Limit Exceeded"):
            resource = "time" if "Time" in status else "memory"
            parts.append(f"## Failure Details: {status}")
            if total_correct is not None and total_testcases is not None:
                parts.append(f"Test cases passed before {resource} limit: {total_correct}/{total_testcases}")
                if total_correct == total_testcases - 1:
                    parts.append("(Passed all but the last/largest test case — need better complexity)")
            if status_msg:
                parts.append(f"Error: {status_msg}")
            parts.append(f"The solution needs better {'time' if 'Time' in status else 'space'} complexity.")

        elif status == "Runtime Error":
            parts.append("## Failure Details: Runtime Error")
            if status_msg:
                parts.append(f"Error message: {status_msg}")
            if total_correct is not None and total_testcases is not None:
                parts.append(f"Test cases passed before crash: {total_correct}/{total_testcases}")

        elif status == "Compile Error":
            parts.append("## Failure Details: Compile Error")
            if status_msg:
                parts.append(f"Compiler error: {status_msg}")

        else:
            if status_msg:
                parts.append(f"## Details\n{status_msg}")

        return "\n".join(parts) if parts else ""

    async def generate_tips(self, context: dict) -> list[str]:
        """
        Generate personalized tips based on user's performance.

        Args:
            context: Dictionary containing:
                - recent_failures: list of recent failed submissions
                - weak_skills: list of weak skill areas
                - pattern_analysis: dict with recurring_mistakes, learning_velocity, blind_spots
                - submission_insights: list of recent insights (pattern_type, concept_gap)

        Returns:
            List of personalized tips
        """
        if not self.configured:
            return [
                "Keep practicing consistently",
                "Review problems you've failed after some time",
                "Focus on understanding patterns, not memorizing solutions",
            ]

        # Build rich context sections
        sections = []

        # Pattern analysis
        patterns = context.get("pattern_analysis", {})
        if patterns:
            velocity = patterns.get("learning_velocity", "unknown")
            velocity_details = patterns.get("velocity_details", "")
            sections.append(f"Learning velocity: {velocity} — {velocity_details}")

            recurring = patterns.get("recurring_mistakes", [])
            if recurring:
                mistake_lines = [f"  - {m.get('pattern', '')} ({m.get('frequency', '?')}x)" for m in recurring[:3]]
                sections.append("Recurring mistakes:\n" + "\n".join(mistake_lines))

            blind_spots = patterns.get("blind_spots", [])
            if blind_spots:
                sections.append(f"Blind spots: {', '.join(blind_spots[:4])}")

        # Submission insights (aggregated pattern types)
        insights = context.get("submission_insights", [])
        if insights:
            pattern_counts = {}
            concept_gaps = {}
            for ins in insights:
                pt = ins.get("pattern_type")
                cg = ins.get("concept_gap")
                if pt:
                    pattern_counts[pt] = pattern_counts.get(pt, 0) + 1
                if cg:
                    concept_gaps[cg] = concept_gaps.get(cg, 0) + 1
            if pattern_counts:
                top_patterns = sorted(pattern_counts.items(), key=lambda x: -x[1])[:3]
                sections.append("Common error patterns: " + ", ".join(f"{p} ({c}x)" for p, c in top_patterns))
            if concept_gaps:
                top_gaps = sorted(concept_gaps.items(), key=lambda x: -x[1])[:3]
                sections.append("Concept gaps to address: " + ", ".join(f"{g} ({c}x)" for g, c in top_gaps))

        # Recent failures
        failures = context.get("recent_failures", [])
        if failures:
            fail_lines = []
            for f in failures[:5]:
                line = f"  - {f.get('problem_slug', '?')}: {f.get('status', '?')}"
                if f.get("status_msg"):
                    line += f" — {f['status_msg'][:50]}"
                if f.get("total_correct") is not None and f.get("total_testcases") is not None:
                    line += f" ({f['total_correct']}/{f['total_testcases']} tests)"
                fail_lines.append(line)
            sections.append("Recent failures:\n" + "\n".join(fail_lines))

        # Weak skills
        weak = context.get("weak_skills", [])
        if weak:
            sections.append("Weak skills: " + ", ".join(
                f"{w.get('tag', '?')} ({w.get('score', 0):.0f}%)" if isinstance(w, dict) else str(w)
                for w in weak[:5]
            ))

        context_text = "\n\n".join(sections) if sections else "No detailed data available"

        prompt = f"""Based on this LeetCode practice data, provide 3-5 specific, actionable tips:

{context_text}

Requirements:
1. Be SPECIFIC — reference the exact patterns and mistakes you see (e.g., "You've failed 4 edge-case problems this week. Before your next problem, spend 5 minutes listing edge cases BEFORE coding.")
2. Be ACTIONABLE — each tip should be something the user can do immediately
3. Include progress acknowledgment if velocity is improving (e.g., "Your Two Pointer success rate improved — keep reinforcing with medium problems.")
4. If there are blind spots, address them directly
5. Be encouraging but honest

Format as a numbered list."""

        try:
            response = await asyncio.to_thread(self.model.generate_content, prompt)
            return self._parse_tips_response(response.text)
        except Exception as e:
            return [f"Unable to generate tips: {str(e)}"]

    def _build_system_prompt(self, context: str) -> str:
        """Build the system prompt for coaching."""
        base_prompt = """You are a helpful LeetCode coach assistant. You help users:
- Understand algorithmic concepts and patterns
- Debug their code submissions
- Learn from their mistakes
- Build strong problem-solving skills

Be encouraging but honest. Focus on teaching concepts, not just giving answers.
When reviewing code, explain WHY something is wrong, not just WHAT is wrong.
"""
        if context:
            return f"{base_prompt}\n\nContext about this user:\n{context}"
        return base_prompt

    def _build_messages(
        self,
        history: Optional[list[ChatMessage]],
        message: str,
        system_prompt: str,
    ) -> list[dict]:
        """Build the messages list for the API call."""
        messages = []

        # Add system prompt
        messages.append({"role": "user", "parts": [system_prompt]})
        messages.append({"role": "model", "parts": ["I understand. I'm ready to help with LeetCode coaching."]})

        # Add history
        if history:
            for msg in history:
                role = "user" if msg.role == "user" else "model"
                messages.append({"role": role, "parts": [msg.content]})

        # Add current message
        messages.append({"role": "user", "parts": [message]})

        return messages

    def _parse_json_analysis(self, text: str) -> dict:
        """Parse JSON analysis response from Gemini, falling back to text parsing."""
        import json

        defaults = {
            "summary": "",
            "issues": [],
            "suggestions": [],
            "time_complexity": None,
            "space_complexity": None,
            "root_cause": None,
            "the_fix": None,
            "pattern_type": None,
            "concept_gap": None,
        }

        # Strip markdown code fences if present
        cleaned = text.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.split("\n", 1)[-1]
            if "```" in cleaned:
                cleaned = cleaned.rsplit("```", 1)[0]
            cleaned = cleaned.strip()

        try:
            parsed = json.loads(cleaned)
            # Merge with defaults to ensure all keys exist
            for key in defaults:
                if key not in parsed:
                    parsed[key] = defaults[key]
            return parsed
        except (json.JSONDecodeError, ValueError):
            # Fall back to the old text parser
            result = self._parse_analysis_response(text)
            result.update({k: v for k, v in defaults.items() if k not in result})
            return result

    def _parse_analysis_response(self, text: str) -> dict:
        """Parse the structured analysis response."""
        result = {
            "summary": "",
            "issues": [],
            "suggestions": [],
            "time_complexity": None,
            "space_complexity": None,
        }

        lines = text.split("\n")
        current_section = None

        for line in lines:
            line = line.strip()
            if not line:
                continue

            if line.startswith("SUMMARY:"):
                result["summary"] = line.replace("SUMMARY:", "").strip()
            elif line.startswith("ISSUES:"):
                current_section = "issues"
            elif line.startswith("SUGGESTIONS:"):
                current_section = "suggestions"
            elif line.startswith("TIME_COMPLEXITY:"):
                result["time_complexity"] = line.replace("TIME_COMPLEXITY:", "").strip()
            elif line.startswith("SPACE_COMPLEXITY:"):
                result["space_complexity"] = line.replace("SPACE_COMPLEXITY:", "").strip()
            elif line.startswith("- ") and current_section:
                result[current_section].append(line[2:])

        return result

    def _parse_tips_response(self, text: str) -> list[str]:
        """Parse numbered tips from the response."""
        tips = []
        lines = text.split("\n")

        for line in lines:
            line = line.strip()
            # Match numbered items (1. or 1) format)
            if line and (line[0].isdigit() and (". " in line or ") " in line)):
                # Remove the number prefix
                tip = line.split(". ", 1)[-1] if ". " in line else line.split(") ", 1)[-1]
                tips.append(tip)

        return tips if tips else [text]  # Fallback to full text if parsing fails

    def _fallback_response(self, message: str) -> str:
        """Provide a helpful response when AI is not configured."""
        return """I'm your LeetCode coach, but AI features are currently disabled (API key not configured).

Here are some general tips:
1. Break down the problem into smaller steps
2. Consider edge cases (empty input, single element, etc.)
3. Think about time and space complexity before coding
4. If stuck, try working through a simple example by hand

To enable AI coaching, configure GOOGLE_API_KEY in the environment."""
