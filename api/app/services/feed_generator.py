"""Feed Generator Service - generates daily problem feeds mixing practice and metric problems."""

import asyncio
import json
from datetime import date, datetime
from typing import Optional
from uuid import UUID

from supabase import Client

from app.services.gemini_gateway import GeminiGateway
from app.services.recommendation_engine import RecommendationEngine


class FeedGenerator:
    """Generates daily problem feeds with practice and metric problems."""

    PRACTICE_COUNT = 20
    METRIC_COUNT = 10
    MAX_REGENERATIONS = 3

    def __init__(self, supabase: Client, gemini: Optional[GeminiGateway] = None):
        self.supabase = supabase
        self.gemini = gemini or GeminiGateway()
        self.recommendation_engine = RecommendationEngine(supabase)

    async def get_or_generate_feed(self, user_id: UUID, feed_date: date = None) -> dict:
        if feed_date is None:
            feed_date = date.today()

        existing = self._get_existing_feed(user_id, feed_date)
        if existing:
            return existing

        return await self.generate_feed(user_id, feed_date)

    def _get_focus_notes(self, user_id: UUID) -> Optional[str]:
        """Fetch user's focus notes from user_settings."""
        try:
            resp = (
                self.supabase.table("user_settings")
                .select("focus_notes")
                .eq("user_id", str(user_id))
                .limit(1)
                .execute()
            )
            if resp.data and resp.data[0].get("focus_notes"):
                return resp.data[0]["focus_notes"]
        except Exception:
            pass
        return None

    async def generate_feed(self, user_id: UUID, feed_date: date = None) -> dict:
        if feed_date is None:
            feed_date = date.today()

        user_id_str = str(user_id)
        focus_notes = self._get_focus_notes(user_id)

        # Get practice and metric problems in parallel
        practice_problems, metric_problems = await asyncio.gather(
            self._get_practice_problems(user_id, self.PRACTICE_COUNT, focus_notes=focus_notes),
            self._get_metric_problems(user_id, self.METRIC_COUNT, focus_notes=focus_notes),
        )

        # Build feed items
        items = []
        sort_order = 0

        # Interleave: every 3rd item is a metric problem
        practice_iter = iter(practice_problems)
        metric_iter = iter(metric_problems)
        practice_done = False
        metric_done = False

        while not practice_done or not metric_done:
            # Add 2 practice problems
            for _ in range(2):
                try:
                    p = next(practice_iter)
                    items.append(self._build_practice_item(user_id_str, feed_date, p, sort_order))
                    sort_order += 1
                except StopIteration:
                    practice_done = True

            # Add 1 metric problem
            try:
                m = next(metric_iter)
                items.append(self._build_metric_item(user_id_str, feed_date, m, sort_order))
                sort_order += 1
            except StopIteration:
                metric_done = True

        if items:
            self.supabase.table("daily_problem_feed").insert(items).execute()

        return self._format_feed_response(user_id, feed_date, items)

    async def extend_feed(self, user_id: UUID) -> dict:
        feed_date = date.today()
        user_id_str = str(user_id)

        # Get existing slugs to exclude
        existing = (
            self.supabase.table("daily_problem_feed")
            .select("problem_slug, sort_order")
            .eq("user_id", user_id_str)
            .eq("feed_date", feed_date.isoformat())
            .order("sort_order", desc=True)
            .execute()
        )

        excluded = {item["problem_slug"] for item in (existing.data or [])}
        max_order = max((item["sort_order"] for item in (existing.data or [])), default=0)

        extra_practice = await self._get_practice_problems(user_id, 5, excluded)
        extra_metric = await self._get_metric_problems(user_id, 3, excluded)

        items = []
        sort_order = max_order + 1

        for p in extra_practice:
            items.append(self._build_practice_item(user_id_str, feed_date, p, sort_order))
            sort_order += 1
        for m in extra_metric:
            items.append(self._build_metric_item(user_id_str, feed_date, m, sort_order))
            sort_order += 1

        if items:
            self.supabase.table("daily_problem_feed").insert(items).execute()

        # Return full feed
        return self._get_existing_feed(user_id, feed_date)

    async def regenerate_feed(self, user_id: UUID) -> dict:
        feed_date = date.today()
        user_id_str = str(user_id)

        # Count regenerations today
        existing_resp = (
            self.supabase.table("daily_problem_feed")
            .select("id, status")
            .eq("user_id", user_id_str)
            .eq("feed_date", feed_date.isoformat())
            .execute()
        )

        # Delete pending items only
        if existing_resp.data:
            pending_ids = [item["id"] for item in existing_resp.data if item["status"] == "pending"]
            if pending_ids:
                self.supabase.table("daily_problem_feed").delete().in_("id", pending_ids).execute()

        # Generate new feed (completed items remain)
        return await self.generate_feed(user_id, feed_date)

    async def _get_practice_problems(
        self, user_id: UUID, count: int, excluded: set = None, focus_notes: Optional[str] = None
    ) -> list[dict]:
        excluded = excluded or set()

        recommendations = await self.recommendation_engine.get_recommendations(
            user_id, limit=count + 10, focus_notes=focus_notes
        )

        problems = []
        for rec in recommendations:
            if rec.problem_slug in excluded:
                continue
            excluded.add(rec.problem_slug)
            problems.append({
                "problem_slug": rec.problem_slug,
                "problem_title": rec.problem_title,
                "difficulty": rec.difficulty.value if rec.difficulty else None,
                "tags": rec.tags,
                "source": rec.source,
                "reason": rec.reason,
            })
            if len(problems) >= count:
                break

        return problems

    async def _get_metric_problems(
        self, user_id: UUID, count: int, excluded: set = None, focus_notes: Optional[str] = None
    ) -> list[dict]:
        excluded = excluded or set()
        user_id_str = str(user_id)

        # Get user's solved problems to exclude from metric
        solved_resp = (
            self.supabase.table("submissions")
            .select("problem_slug")
            .eq("user_id", user_id_str)
            .eq("status", "Accepted")
            .execute()
        )
        solved_slugs = {s["problem_slug"] for s in (solved_resp.data or [])}
        all_excluded = excluded | solved_slugs

        # Get previously used metric slugs
        prev_metric_resp = (
            self.supabase.table("metric_attempts")
            .select("problem_slug")
            .eq("user_id", user_id_str)
            .execute()
        )
        prev_metric = {s["problem_slug"] for s in (prev_metric_resp.data or [])}
        all_excluded = all_excluded | prev_metric

        # Get user skill context
        skills_resp = (
            self.supabase.table("skill_scores")
            .select("tag, score")
            .eq("user_id", user_id_str)
            .order("score")
            .execute()
        )
        skill_context = skills_resp.data or []

        # Get targets for difficulty distribution
        targets_resp = (
            self.supabase.table("win_rate_targets")
            .select("easy_target, medium_target, hard_target")
            .eq("user_id", user_id_str)
            .limit(1)
            .execute()
        )
        targets = targets_resp.data[0] if targets_resp.data else {
            "easy_target": 0.9, "medium_target": 0.7, "hard_target": 0.5
        }

        if not self.gemini.configured:
            return self._fallback_metric_problems(count, all_excluded)

        prompt = self._build_metric_prompt(
            count, list(all_excluded)[:200], skill_context, targets, focus_notes=focus_notes
        )

        try:
            response = await asyncio.to_thread(self.gemini.model.generate_content, prompt)
            text = response.text.strip()

            if "```json" in text:
                text = text.split("```json")[1].split("```")[0]
            elif "```" in text:
                text = text.split("```")[1].split("```")[0]

            result = json.loads(text)
            problems = result.get("problems", [])

            # Filter out any that are in excluded set
            filtered = []
            for p in problems:
                slug = p.get("slug", "")
                if slug and slug not in all_excluded:
                    filtered.append({
                        "problem_slug": slug,
                        "problem_title": p.get("title"),
                        "difficulty": p.get("difficulty"),
                        "tags": p.get("tags", []),
                        "rationale": p.get("rationale", "Selected as metric problem"),
                    })
                    all_excluded.add(slug)
                if len(filtered) >= count:
                    break

            return filtered

        except Exception as e:
            print(f"Gemini metric problem selection failed: {e}")
            return self._fallback_metric_problems(count, all_excluded)

    def _build_metric_prompt(
        self, count: int, excluded_slugs: list, skill_context: list, targets: dict,
        focus_notes: Optional[str] = None,
    ) -> str:
        skills_text = ""
        if skill_context:
            weak = [s for s in skill_context if s["score"] < 60]
            strong = [s for s in skill_context if s["score"] >= 60]
            if weak:
                skills_text += "Weak areas: " + ", ".join(f"{s['tag']} ({s['score']:.0f})" for s in weak[:5]) + "\n"
            if strong:
                skills_text += "Strong areas: " + ", ".join(f"{s['tag']} ({s['score']:.0f})" for s in strong[:5]) + "\n"

        # Compute how many of each difficulty
        easy_count = max(1, round(count * 0.3))
        medium_count = max(1, round(count * 0.5))
        hard_count = count - easy_count - medium_count

        focus_section = ""
        if focus_notes:
            focus_section = f"\n## User Focus Notes\nThe user has requested the following focus areas. Prioritize problems that align with these notes:\n{focus_notes}\n"

        return f"""You are a LeetCode problem selector. Select {count} REAL LeetCode problems that the user has NOT seen before. These are "metric" problems to measure true ability on unseen problems.

## Requirements
- Select REAL LeetCode problems with correct slugs (e.g., "two-sum", "merge-intervals")
- Mix of difficulties: ~{easy_count} Easy, ~{medium_count} Medium, ~{hard_count} Hard
- Cover a variety of topics/patterns
- DO NOT select any of these already-seen slugs: {excluded_slugs[:100]}

## User Context
{skills_text}
Target win rates: Easy {targets.get('easy_target', 0.9)*100:.0f}%, Medium {targets.get('medium_target', 0.7)*100:.0f}%, Hard {targets.get('hard_target', 0.5)*100:.0f}%
{focus_section}
## Output Format (JSON only)
{{
  "problems": [
    {{
      "slug": "problem-slug",
      "title": "Problem Title",
      "difficulty": "Easy|Medium|Hard",
      "tags": ["Array", "Two Pointers"],
      "rationale": "Why this problem was selected"
    }}
  ]
}}

Only output JSON, nothing else."""

    def _fallback_metric_problems(self, count: int, excluded: set) -> list[dict]:
        """Fallback metric problems when Gemini is unavailable."""
        # Curated list of well-known LeetCode problems across difficulties
        fallback_pool = [
            {"slug": "valid-parentheses", "title": "Valid Parentheses", "difficulty": "Easy", "tags": ["Stack"]},
            {"slug": "reverse-linked-list", "title": "Reverse Linked List", "difficulty": "Easy", "tags": ["Linked List"]},
            {"slug": "maximum-subarray", "title": "Maximum Subarray", "difficulty": "Medium", "tags": ["DP", "Array"]},
            {"slug": "product-of-array-except-self", "title": "Product of Array Except Self", "difficulty": "Medium", "tags": ["Array"]},
            {"slug": "group-anagrams", "title": "Group Anagrams", "difficulty": "Medium", "tags": ["Hash Table", "String"]},
            {"slug": "course-schedule", "title": "Course Schedule", "difficulty": "Medium", "tags": ["Graph", "BFS"]},
            {"slug": "word-break", "title": "Word Break", "difficulty": "Medium", "tags": ["DP"]},
            {"slug": "serialize-and-deserialize-binary-tree", "title": "Serialize and Deserialize Binary Tree", "difficulty": "Hard", "tags": ["Tree", "BFS"]},
            {"slug": "trapping-rain-water", "title": "Trapping Rain Water", "difficulty": "Hard", "tags": ["Two Pointers", "Stack"]},
            {"slug": "merge-k-sorted-lists", "title": "Merge k Sorted Lists", "difficulty": "Hard", "tags": ["Linked List", "Heap"]},
            {"slug": "longest-increasing-subsequence", "title": "Longest Increasing Subsequence", "difficulty": "Medium", "tags": ["DP", "Binary Search"]},
            {"slug": "find-median-from-data-stream", "title": "Find Median from Data Stream", "difficulty": "Hard", "tags": ["Heap"]},
            {"slug": "lru-cache", "title": "LRU Cache", "difficulty": "Medium", "tags": ["Hash Table", "Linked List"]},
            {"slug": "min-stack", "title": "Min Stack", "difficulty": "Medium", "tags": ["Stack"]},
            {"slug": "climbing-stairs", "title": "Climbing Stairs", "difficulty": "Easy", "tags": ["DP"]},
        ]

        results = []
        for p in fallback_pool:
            if p["slug"] not in excluded:
                results.append({
                    "problem_slug": p["slug"],
                    "problem_title": p["title"],
                    "difficulty": p["difficulty"],
                    "tags": p["tags"],
                    "rationale": "Selected from curated metric pool",
                })
                if len(results) >= count:
                    break

        return results

    def _build_practice_item(self, user_id: str, feed_date: date, problem: dict, sort_order: int) -> dict:
        return {
            "user_id": user_id,
            "feed_date": feed_date.isoformat(),
            "problem_slug": problem["problem_slug"],
            "problem_title": problem.get("problem_title"),
            "difficulty": problem.get("difficulty"),
            "tags": problem.get("tags", []),
            "feed_type": "practice",
            "practice_source": problem.get("source"),
            "practice_reason": problem.get("reason"),
            "sort_order": sort_order,
            "status": "pending",
        }

    def _build_metric_item(self, user_id: str, feed_date: date, problem: dict, sort_order: int) -> dict:
        return {
            "user_id": user_id,
            "feed_date": feed_date.isoformat(),
            "problem_slug": problem["problem_slug"],
            "problem_title": problem.get("problem_title"),
            "difficulty": problem.get("difficulty"),
            "tags": problem.get("tags", []),
            "feed_type": "metric",
            "metric_rationale": problem.get("rationale"),
            "sort_order": sort_order,
            "status": "pending",
        }

    def _get_existing_feed(self, user_id: UUID, feed_date: date) -> Optional[dict]:
        response = (
            self.supabase.table("daily_problem_feed")
            .select("*")
            .eq("user_id", str(user_id))
            .eq("feed_date", feed_date.isoformat())
            .order("sort_order")
            .execute()
        )

        if not response.data:
            return None

        return self._format_feed_response(user_id, feed_date, response.data)

    def _format_feed_response(self, user_id: UUID, feed_date: date, items: list) -> dict:
        completed = sum(1 for i in items if i.get("status") == "completed")
        practice = sum(1 for i in items if i.get("feed_type") == "practice")
        metric = sum(1 for i in items if i.get("feed_type") == "metric")

        return {
            "user_id": str(user_id),
            "feed_date": feed_date.isoformat(),
            "items": items,
            "completed_count": completed,
            "total_count": len(items),
            "practice_count": practice,
            "metric_count": metric,
        }
