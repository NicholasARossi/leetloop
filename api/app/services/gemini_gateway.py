"""Centralized gateway for Google Gemini AI calls."""

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
            self.model = genai.GenerativeModel("gemini-1.5-flash")
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
            response = self.model.generate_content(messages)
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
            response = self.model.generate_content(messages, stream=True)
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
            }

        prompt = f"""Analyze this {language} code submission for the LeetCode problem "{problem_slug}".
The submission result was: {status}

Code:
```{language}
{code}
```

Provide a brief analysis including:
1. A one-sentence summary of what the code does
2. Any bugs or issues that could cause the {status} result
3. Suggestions for improvement
4. Time complexity (Big O)
5. Space complexity (Big O)

Format your response as:
SUMMARY: <one sentence>
ISSUES:
- <issue 1>
- <issue 2>
SUGGESTIONS:
- <suggestion 1>
- <suggestion 2>
TIME_COMPLEXITY: O(...)
SPACE_COMPLEXITY: O(...)
"""

        try:
            response = self.model.generate_content(prompt)
            return self._parse_analysis_response(response.text)
        except Exception as e:
            return {
                "summary": f"Analysis failed: {str(e)}",
                "issues": [],
                "suggestions": [],
                "time_complexity": None,
                "space_complexity": None,
            }

    async def generate_tips(self, context: dict) -> list[str]:
        """
        Generate personalized tips based on user's performance.

        Args:
            context: Dictionary containing recent_failures, weak_skills, etc.

        Returns:
            List of personalized tips
        """
        if not self.configured:
            return [
                "Keep practicing consistently",
                "Review problems you've failed after some time",
                "Focus on understanding patterns, not memorizing solutions",
            ]

        prompt = f"""Based on this LeetCode practice data, provide 3-5 specific, actionable tips:

Recent failures: {context.get('recent_failures', [])}
Weak skill areas: {context.get('weak_skills', [])}

Provide tips that are:
1. Specific to the patterns you see
2. Actionable (not generic advice)
3. Encouraging but honest

Format as a numbered list."""

        try:
            response = self.model.generate_content(prompt)
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
