"""Code analyzer for submission review."""

from app.models.schemas import CodeAnalysisResponse
from app.services.gemini_gateway import GeminiGateway


class CodeAnalyzer:
    """
    Analyzes submitted code for issues, patterns, and improvements.

    Uses Gemini AI for intelligent analysis when configured,
    falls back to basic static analysis otherwise.
    """

    def __init__(self):
        self.gateway = GeminiGateway()

    async def analyze(
        self,
        code: str,
        language: str,
        problem_slug: str,
        status: str,
    ) -> CodeAnalysisResponse:
        """
        Analyze submitted code and return structured feedback.

        Args:
            code: The submitted code
            language: Programming language (e.g., "python3", "javascript")
            problem_slug: The LeetCode problem slug
            status: Submission status (e.g., "Wrong Answer", "Time Limit Exceeded")

        Returns:
            CodeAnalysisResponse with analysis results
        """
        # Use AI analysis if configured
        if self.gateway.configured:
            analysis = await self.gateway.analyze_code(
                code=code,
                language=language,
                problem_slug=problem_slug,
                status=status,
            )
            return CodeAnalysisResponse(**analysis)

        # Fallback to basic analysis
        return self._basic_analysis(code, language, status)

    def _basic_analysis(
        self,
        code: str,
        language: str,
        status: str,
    ) -> CodeAnalysisResponse:
        """Perform basic static analysis without AI."""
        issues = []
        suggestions = []

        # Check for common issues based on status
        if status == "Time Limit Exceeded":
            issues.append("Code is taking too long to execute")
            suggestions.extend([
                "Look for nested loops that could be optimized",
                "Consider using a hash map for O(1) lookups",
                "Check if you can reduce the problem size with sorting or preprocessing",
            ])
            if self._has_nested_loops(code, language):
                issues.append("Nested loops detected - potential O(n²) or worse complexity")

        elif status == "Wrong Answer":
            issues.append("Code produces incorrect output for some test cases")
            suggestions.extend([
                "Check edge cases: empty input, single element, negative numbers",
                "Verify your algorithm handles boundary conditions",
                "Try working through a simple example step by step",
            ])

        elif status == "Runtime Error":
            issues.append("Code crashes during execution")
            suggestions.extend([
                "Check for index out of bounds errors",
                "Ensure you handle null/None values",
                "Look for division by zero",
            ])
            if self._has_potential_index_error(code, language):
                issues.append("Potential array index issue detected")

        elif status == "Memory Limit Exceeded":
            issues.append("Code uses too much memory")
            suggestions.extend([
                "Check if you're storing unnecessary data",
                "Consider using iterative instead of recursive approach",
                "Look for memory leaks or unbounded data structures",
            ])

        # Generic suggestions
        if not suggestions:
            suggestions = [
                "Review your approach and algorithm choice",
                "Consider the problem constraints",
                "Look at similar problems for patterns",
            ]

        return CodeAnalysisResponse(
            summary=f"Submission resulted in {status}",
            issues=issues,
            suggestions=suggestions,
            time_complexity=self._estimate_complexity(code, language),
            space_complexity=None,
        )

    def _has_nested_loops(self, code: str, language: str) -> bool:
        """Detect nested loops in code (basic heuristic)."""
        loop_keywords = {
            "python": ["for ", "while "],
            "python3": ["for ", "while "],
            "javascript": ["for ", "for(", "while ", "while("],
            "java": ["for ", "for(", "while ", "while("],
            "cpp": ["for ", "for(", "while ", "while("],
            "c": ["for ", "for(", "while ", "while("],
        }

        keywords = loop_keywords.get(language.lower(), loop_keywords["python"])
        loop_count = 0

        for keyword in keywords:
            loop_count += code.count(keyword)

        return loop_count >= 2

    def _has_potential_index_error(self, code: str, language: str) -> bool:
        """Detect potential index errors (basic heuristic)."""
        # Look for array access patterns without bounds checking
        access_patterns = ["[i]", "[j]", "[k]", "[n]", "[m]", "[-1]", "[len"]
        return any(pattern in code for pattern in access_patterns)

    def _estimate_complexity(self, code: str, language: str) -> str | None:
        """Estimate time complexity based on loop structure (very basic)."""
        loop_keywords = ["for ", "while "]
        loop_count = sum(code.count(kw) for kw in loop_keywords)

        if loop_count == 0:
            return "O(1) or O(n) - no explicit loops"
        elif loop_count == 1:
            return "O(n) - single loop detected"
        elif loop_count == 2:
            return "O(n²) - nested loops likely"
        else:
            return f"O(n^{loop_count}) - multiple nested loops"
