"""Submission pattern analyzer — detects recurring mistake patterns across submissions."""

import asyncio
import json
from datetime import datetime, timedelta
from typing import Optional
from uuid import UUID

from supabase import Client

from app.services.gemini_gateway import GeminiGateway


class PatternAnalyzer:
    """
    Analyzes a user's recent submissions to detect recurring mistake patterns,
    learning velocity, blind spots, and strategic recommendations.

    Results are cached in the user_pattern_analysis table (1 row per user, refreshed daily).
    """

    CACHE_TTL_HOURS = 12

    def __init__(self, supabase: Client, gemini: Optional[GeminiGateway] = None):
        self.supabase = supabase
        self.gemini = gemini or GeminiGateway()

    async def analyze_patterns(self, user_id: UUID, days: int = 14) -> dict:
        """
        Return pattern analysis for a user, using cache if fresh enough.

        Args:
            user_id: The user's ID
            days: Number of days of history to analyze

        Returns:
            UserPatterns-compatible dict
        """
        cached = await self._get_cached(user_id)
        if cached:
            return cached

        return await self._generate_analysis(user_id, days)

    async def _get_cached(self, user_id: UUID) -> Optional[dict]:
        """Return cached analysis if it exists and is fresh."""
        response = (
            self.supabase.table("user_pattern_analysis")
            .select("patterns, analyzed_at")
            .eq("user_id", str(user_id))
            .limit(1)
            .execute()
        )
        if not response.data:
            return None

        row = response.data[0]
        analyzed_at = row.get("analyzed_at", "")
        if isinstance(analyzed_at, str):
            try:
                analyzed_dt = datetime.fromisoformat(analyzed_at.replace("Z", "+00:00"))
            except (ValueError, TypeError):
                return None
        else:
            analyzed_dt = analyzed_at

        # Check freshness
        age = datetime.utcnow() - analyzed_dt.replace(tzinfo=None)
        if age < timedelta(hours=self.CACHE_TTL_HOURS):
            patterns = row.get("patterns", {})
            patterns["analyzed_at"] = analyzed_at
            return patterns

        return None

    async def _generate_analysis(self, user_id: UUID, days: int) -> dict:
        """Generate fresh pattern analysis via Gemini."""
        user_id_str = str(user_id)
        cutoff = (datetime.utcnow() - timedelta(days=days)).isoformat()

        # Fetch submissions and skills in parallel
        def _q_submissions():
            return (
                self.supabase.table("submissions")
                .select(
                    "problem_slug, status, tags, status_msg, code_output, expected_output, "
                    "total_correct, total_testcases, language, attempt_number, "
                    "time_elapsed_seconds, submitted_at"
                )
                .eq("user_id", user_id_str)
                .gte("submitted_at", cutoff)
                .order("submitted_at", desc=True)
                .limit(50)
                .execute()
            )

        def _q_skills():
            return (
                self.supabase.table("skill_scores")
                .select("tag, score, total_attempts")
                .eq("user_id", user_id_str)
                .order("score")
                .execute()
            )

        submissions_resp, skills_resp = await asyncio.gather(
            asyncio.to_thread(_q_submissions),
            asyncio.to_thread(_q_skills),
        )

        submissions = submissions_resp.data or []
        skills = skills_resp.data or []

        if not submissions:
            empty = {
                "recurring_mistakes": [],
                "error_distribution": {},
                "learning_velocity": "unknown",
                "velocity_details": "Not enough data to analyze",
                "blind_spots": [],
                "strategic_recommendations": ["Submit more problems to enable pattern analysis"],
                "analyzed_at": datetime.utcnow().isoformat(),
            }
            await self._save_cache(user_id, empty)
            return empty

        # Group failures
        failures = [s for s in submissions if s.get("status") != "Accepted"]
        failure_counts = {}
        for f in failures:
            status = f.get("status", "Unknown")
            failure_counts[status] = failure_counts.get(status, 0) + 1

        total_failures = len(failures)
        error_distribution = {
            status: round(count / total_failures * 100, 1)
            for status, count in failure_counts.items()
        } if total_failures > 0 else {}

        # Build Gemini prompt
        prompt = self._build_prompt(submissions, failures, skills, error_distribution, days)

        if not self.gemini.configured:
            result = self._fallback_analysis(submissions, failures, skills, error_distribution)
            await self._save_cache(user_id, result)
            return result

        try:
            response = await asyncio.to_thread(self.gemini.model.generate_content, prompt)
            text = response.text.strip()

            # Extract JSON
            if text.startswith("```"):
                text = text.split("\n", 1)[-1]
                if "```" in text:
                    text = text.rsplit("```", 1)[0]
                text = text.strip()

            parsed = json.loads(text)
            parsed["error_distribution"] = error_distribution
            parsed["analyzed_at"] = datetime.utcnow().isoformat()

            await self._save_cache(user_id, parsed)
            return parsed

        except Exception as e:
            print(f"Pattern analysis Gemini call failed: {e}")
            result = self._fallback_analysis(submissions, failures, skills, error_distribution)
            await self._save_cache(user_id, result)
            return result

    def _build_prompt(
        self,
        submissions: list,
        failures: list,
        skills: list,
        error_distribution: dict,
        days: int,
    ) -> str:
        """Build the Gemini prompt for pattern analysis."""
        # Format failed submissions
        failure_lines = []
        for f in failures[:30]:
            line = f"- {f['problem_slug']} | {f.get('status', '?')}"
            if f.get("tags"):
                line += f" | tags: {', '.join(f['tags'][:3])}"
            if f.get("status_msg"):
                line += f" | error: {f['status_msg'][:80]}"
            if f.get("total_correct") is not None and f.get("total_testcases") is not None:
                line += f" | tests: {f['total_correct']}/{f['total_testcases']}"
            if f.get("code_output") and f.get("expected_output"):
                line += f" | got: {f['code_output'][:40]} expected: {f['expected_output'][:40]}"
            if f.get("attempt_number"):
                line += f" | attempt #{f['attempt_number']}"
            failure_lines.append(line)

        # Format skills
        skill_lines = []
        for s in skills:
            score = s.get("score", 0)
            skill_lines.append(f"- {s['tag']}: {score:.0f}% ({s.get('total_attempts', 0)} attempts)")

        # Split submissions into weeks for velocity
        total = len(submissions)
        accepted = sum(1 for s in submissions if s.get("status") == "Accepted")

        return f"""Analyze this LeetCode user's recent submission history and identify patterns.

## Submissions Summary (last {days} days)
Total submissions: {total}
Accepted: {accepted}
Failed: {len(failures)}

## Error Distribution
{json.dumps(error_distribution, indent=2)}

## Failed Submissions (most recent first)
{chr(10).join(failure_lines) if failure_lines else "No failures"}

## Skill Scores (lowest first)
{chr(10).join(skill_lines) if skill_lines else "No skill data yet"}

Analyze and respond with ONLY valid JSON (no markdown fences):
{{
  "recurring_mistakes": [
    {{"pattern": "description of the recurring pattern", "frequency": 3, "example_problems": ["slug1", "slug2"]}}
  ],
  "learning_velocity": "improving | plateauing | regressing",
  "velocity_details": "Explanation with evidence",
  "blind_spots": ["Concept user thinks they know but consistently fails"],
  "strategic_recommendations": ["Top 3 focus areas with reasoning"]
}}"""

    def _fallback_analysis(
        self,
        submissions: list,
        failures: list,
        skills: list,
        error_distribution: dict,
    ) -> dict:
        """Generate basic analysis without Gemini."""
        # Find recurring problem slugs in failures
        slug_counts = {}
        for f in failures:
            slug = f.get("problem_slug", "")
            slug_counts[slug] = slug_counts.get(slug, 0) + 1

        recurring = [
            {"pattern": f"Failed {slug} multiple times", "frequency": count, "example_problems": [slug]}
            for slug, count in sorted(slug_counts.items(), key=lambda x: -x[1])
            if count >= 2
        ][:5]

        # Blind spots: weak skills with many attempts
        blind_spots = [
            s["tag"]
            for s in skills
            if s.get("score", 0) < 40 and s.get("total_attempts", 0) >= 3
        ][:3]

        total = len(submissions)
        accepted = sum(1 for s in submissions if s.get("status") == "Accepted")
        rate = accepted / total if total > 0 else 0

        if rate >= 0.7:
            velocity = "improving"
            details = f"{accepted}/{total} accepted ({rate*100:.0f}%)"
        elif rate >= 0.4:
            velocity = "plateauing"
            details = f"{accepted}/{total} accepted ({rate*100:.0f}%) — mixed results"
        else:
            velocity = "regressing"
            details = f"Only {accepted}/{total} accepted ({rate*100:.0f}%)"

        recommendations = []
        if error_distribution.get("Wrong Answer", 0) > 40:
            recommendations.append("Focus on edge cases — list all inputs before coding")
        if error_distribution.get("Time Limit Exceeded", 0) > 20:
            recommendations.append("Study time complexity — practice recognizing O(n²) patterns")
        if blind_spots:
            recommendations.append(f"Drill weak fundamentals: {', '.join(blind_spots)}")
        if not recommendations:
            recommendations.append("Continue current practice rhythm")

        return {
            "recurring_mistakes": recurring,
            "error_distribution": error_distribution,
            "learning_velocity": velocity,
            "velocity_details": details,
            "blind_spots": blind_spots,
            "strategic_recommendations": recommendations,
            "analyzed_at": datetime.utcnow().isoformat(),
        }

    async def _save_cache(self, user_id: UUID, patterns: dict) -> None:
        """Upsert pattern analysis to the cache table."""
        user_id_str = str(user_id)
        # Remove analyzed_at from the JSON blob (stored as a column)
        patterns_copy = {k: v for k, v in patterns.items() if k != "analyzed_at"}

        data = {
            "user_id": user_id_str,
            "patterns": patterns_copy,
            "analyzed_at": datetime.utcnow().isoformat(),
        }

        try:
            self.supabase.table("user_pattern_analysis").upsert(
                data, on_conflict="user_id"
            ).execute()
        except Exception as e:
            print(f"Failed to cache pattern analysis: {e}")


# Singleton
_instance: Optional[PatternAnalyzer] = None


def get_pattern_analyzer(supabase: Client, gemini: Optional[GeminiGateway] = None) -> PatternAnalyzer:
    """Get or create the PatternAnalyzer singleton."""
    global _instance
    if _instance is None:
        _instance = PatternAnalyzer(supabase, gemini)
    return _instance
