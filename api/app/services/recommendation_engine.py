"""Recommendation engine for personalized problem suggestions."""

from datetime import datetime
from typing import Optional
from uuid import UUID

from supabase import Client

from app.models.schemas import Difficulty, RecommendedProblem


class RecommendationEngine:
    """
    Generates personalized problem recommendations based on:
    1. Spaced repetition review queue (highest priority)
    2. Weak skill areas
    3. Natural difficulty progression
    """

    def __init__(self, supabase: Client):
        self.supabase = supabase

    async def get_recommendations(
        self,
        user_id: UUID,
        limit: int = 5,
    ) -> list[RecommendedProblem]:
        """Get prioritized problem recommendations."""
        recommendations = []

        # 1. Get due reviews (highest priority)
        reviews = await self._get_due_reviews(user_id, limit=limit)
        for review in reviews:
            recommendations.append(
                RecommendedProblem(
                    problem_slug=review["problem_slug"],
                    problem_title=review.get("problem_title"),
                    difficulty=None,  # Could fetch from problem DB
                    tags=[],
                    reason=f"Review needed: {review.get('reason', 'Previously failed')}",
                    priority=100.0 - review.get("interval_days", 1),  # Shorter interval = higher priority
                    source="review_queue",
                )
            )

        # 2. Get weak skill recommendations
        if len(recommendations) < limit:
            weak_problems = await self._get_weak_skill_problems(
                user_id,
                limit=limit - len(recommendations),
            )
            recommendations.extend(weak_problems)

        # 3. Fill with progression problems if needed
        if len(recommendations) < limit:
            progression = await self._get_progression_problems(
                user_id,
                limit=limit - len(recommendations),
            )
            recommendations.extend(progression)

        # Sort by priority and return top N
        recommendations.sort(key=lambda x: x.priority, reverse=True)
        return recommendations[:limit]

    async def get_weak_areas(self, user_id: UUID) -> list[str]:
        """Get list of user's weakest skill areas."""
        response = (
            self.supabase.table("skill_scores")
            .select("tag, score")
            .eq("user_id", str(user_id))
            .order("score")
            .limit(5)
            .execute()
        )

        if response.data:
            return [s["tag"] for s in response.data if s["score"] < 60]
        return []

    async def _get_due_reviews(
        self,
        user_id: UUID,
        limit: int = 5,
    ) -> list[dict]:
        """Get problems due for spaced repetition review."""
        try:
            response = self.supabase.rpc(
                "get_due_reviews",
                {"p_user_id": str(user_id), "p_limit": limit}
            ).execute()
            return response.data if response.data else []
        except Exception:
            # Fallback to direct query if RPC fails
            response = (
                self.supabase.table("review_queue")
                .select("*")
                .eq("user_id", str(user_id))
                .lte("next_review", datetime.utcnow().isoformat())
                .order("priority", desc=True)
                .order("next_review")
                .limit(limit)
                .execute()
            )
            return response.data if response.data else []

    async def _get_weak_skill_problems(
        self,
        user_id: UUID,
        limit: int = 3,
    ) -> list[RecommendedProblem]:
        """Get problems targeting user's weakest skills."""
        # Get weakest skills
        weak_skills = (
            self.supabase.table("skill_scores")
            .select("tag, score")
            .eq("user_id", str(user_id))
            .order("score")
            .limit(3)
            .execute()
        )

        if not weak_skills.data:
            return []

        recommendations = []
        for skill in weak_skills.data:
            if skill["score"] >= 70:  # Not weak enough
                continue

            # Find problems the user hasn't solved with this tag
            # For now, we'll suggest reviewing previously failed problems with this tag
            failed = (
                self.supabase.table("submissions")
                .select("problem_slug, problem_title, difficulty, tags")
                .eq("user_id", str(user_id))
                .neq("status", "Accepted")
                .contains("tags", [skill["tag"]])
                .order("submitted_at", desc=True)
                .limit(1)
                .execute()
            )

            if failed.data:
                problem = failed.data[0]
                # Check if not already in recommendations
                if not any(r.problem_slug == problem["problem_slug"] for r in recommendations):
                    recommendations.append(
                        RecommendedProblem(
                            problem_slug=problem["problem_slug"],
                            problem_title=problem.get("problem_title"),
                            difficulty=problem.get("difficulty"),
                            tags=problem.get("tags", []),
                            reason=f"Strengthen weak area: {skill['tag']} (score: {skill['score']:.0f})",
                            priority=70.0 - skill["score"],  # Lower score = higher priority
                            source="weak_skill",
                        )
                    )

            if len(recommendations) >= limit:
                break

        return recommendations

    async def _get_progression_problems(
        self,
        user_id: UUID,
        limit: int = 2,
    ) -> list[RecommendedProblem]:
        """Get problems for natural difficulty progression."""
        # Get user's current level based on success rate by difficulty
        stats_by_difficulty = {}

        for diff in ["Easy", "Medium", "Hard"]:
            accepted = (
                self.supabase.table("submissions")
                .select("id", count="exact")
                .eq("user_id", str(user_id))
                .eq("difficulty", diff)
                .eq("status", "Accepted")
                .execute()
            )
            total = (
                self.supabase.table("submissions")
                .select("id", count="exact")
                .eq("user_id", str(user_id))
                .eq("difficulty", diff)
                .execute()
            )
            stats_by_difficulty[diff] = {
                "accepted": accepted.count or 0,
                "total": total.count or 0,
            }

        # Determine recommended difficulty
        recommended_diff = self._determine_progression_difficulty(stats_by_difficulty)

        recommendations = []

        # Suggest problems at this difficulty that user hasn't solved
        # For now, we'll look for problems they've attempted but not solved
        attempted = (
            self.supabase.table("submissions")
            .select("problem_slug, problem_title, difficulty, tags")
            .eq("user_id", str(user_id))
            .eq("difficulty", recommended_diff)
            .neq("status", "Accepted")
            .order("submitted_at", desc=True)
            .limit(limit)
            .execute()
        )

        seen_slugs = set()
        for problem in (attempted.data or []):
            if problem["problem_slug"] in seen_slugs:
                continue
            seen_slugs.add(problem["problem_slug"])

            recommendations.append(
                RecommendedProblem(
                    problem_slug=problem["problem_slug"],
                    problem_title=problem.get("problem_title"),
                    difficulty=problem.get("difficulty"),
                    tags=problem.get("tags", []),
                    reason=f"Continue {recommended_diff} difficulty progression",
                    priority=30.0,
                    source="progression",
                )
            )

        return recommendations

    def _determine_progression_difficulty(
        self,
        stats: dict[str, dict],
    ) -> str:
        """Determine what difficulty level user should work on next."""
        easy = stats.get("Easy", {"accepted": 0, "total": 0})
        medium = stats.get("Medium", {"accepted": 0, "total": 0})
        hard = stats.get("Hard", {"accepted": 0, "total": 0})

        # Calculate success rates
        easy_rate = easy["accepted"] / easy["total"] if easy["total"] > 0 else 0
        medium_rate = medium["accepted"] / medium["total"] if medium["total"] > 0 else 0

        # Progression logic:
        # - If Easy success rate < 70% or < 10 Easy problems, stay on Easy
        # - If Medium success rate < 50% or < 5 Medium problems, stay on Medium
        # - Otherwise, suggest Hard

        if easy_rate < 0.7 or easy["total"] < 10:
            return "Easy"
        elif medium_rate < 0.5 or medium["total"] < 5:
            return "Medium"
        else:
            return "Hard"
