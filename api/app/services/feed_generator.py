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

    def _get_journal_entries(self, user_id: UUID) -> list[dict]:
        """Fetch up to 5 unaddressed journal entries for prompt context."""
        try:
            resp = (
                self.supabase.table("mistake_journal")
                .select("entry_text, tags")
                .eq("user_id", str(user_id))
                .eq("is_addressed", False)
                .order("created_at", desc=True)
                .limit(5)
                .execute()
            )
            return resp.data or []
        except Exception:
            return []

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
        journal_entries = self._get_journal_entries(user_id)

        # Get practice and metric problems in parallel
        practice_problems, metric_problems = await asyncio.gather(
            self._get_practice_problems(user_id, self.PRACTICE_COUNT, focus_notes=focus_notes),
            self._get_metric_problems(user_id, self.METRIC_COUNT, focus_notes=focus_notes, journal_entries=journal_entries),
        )

        # Build feed items
        items = []
        sort_order = 0

        # Interleave: first 3 are metric (new), then alternate 1 metric / 2 practice
        practice_iter = iter(practice_problems)
        metric_iter = iter(metric_problems)
        practice_done = False
        metric_done = False

        # Lead with 3 metric (new) problems
        for _ in range(3):
            try:
                m = next(metric_iter)
                items.append(self._build_metric_item(user_id_str, feed_date, m, sort_order))
                sort_order += 1
            except StopIteration:
                metric_done = True
                break

        # Then alternate: 2 practice, 1 metric
        while not practice_done or not metric_done:
            for _ in range(2):
                try:
                    p = next(practice_iter)
                    items.append(self._build_practice_item(user_id_str, feed_date, p, sort_order))
                    sort_order += 1
                except StopIteration:
                    practice_done = True

            try:
                m = next(metric_iter)
                items.append(self._build_metric_item(user_id_str, feed_date, m, sort_order))
                sort_order += 1
            except StopIteration:
                metric_done = True

        # Deduplicate before inserting
        seen_slugs = set()
        deduped = []
        for item in items:
            slug = item["problem_slug"]
            if slug not in seen_slugs:
                seen_slugs.add(slug)
                deduped.append(item)
        items = deduped

        if items:
            self.supabase.table("daily_problem_feed").upsert(
                items, on_conflict="user_id,feed_date,problem_slug"
            ).execute()

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
            self.supabase.table("daily_problem_feed").upsert(
                items, on_conflict="user_id,feed_date,problem_slug"
            ).execute()

        # Return full feed
        return self._get_existing_feed(user_id, feed_date)

    async def regenerate_feed(self, user_id: UUID) -> dict:
        feed_date = date.today()
        user_id_str = str(user_id)

        # Get existing items
        existing_resp = (
            self.supabase.table("daily_problem_feed")
            .select("id, status, problem_slug")
            .eq("user_id", user_id_str)
            .eq("feed_date", feed_date.isoformat())
            .execute()
        )

        completed_slugs = set()
        if existing_resp.data:
            pending_ids = [item["id"] for item in existing_resp.data if item["status"] == "pending"]
            completed_slugs = {item["problem_slug"] for item in existing_resp.data if item["status"] == "completed"}
            if pending_ids:
                self.supabase.table("daily_problem_feed").delete().in_("id", pending_ids).execute()

        # Generate new feed, excluding completed slugs so we don't get unique constraint violations
        focus_notes = self._get_focus_notes(user_id)
        journal_entries = self._get_journal_entries(user_id)

        practice_problems, metric_problems = await asyncio.gather(
            self._get_practice_problems(user_id, self.PRACTICE_COUNT, excluded=completed_slugs, focus_notes=focus_notes),
            self._get_metric_problems(user_id, self.METRIC_COUNT, excluded=completed_slugs, focus_notes=focus_notes, journal_entries=journal_entries),
        )

        # Build items, starting sort_order after any completed items
        items = []
        sort_order = len(completed_slugs)

        # Lead with 3 metric (new) problems
        practice_iter = iter(practice_problems)
        metric_iter = iter(metric_problems)
        practice_done = False
        metric_done = False

        for _ in range(3):
            try:
                m = next(metric_iter)
                items.append(self._build_metric_item(user_id_str, feed_date, m, sort_order))
                sort_order += 1
            except StopIteration:
                metric_done = True
                break

        while not practice_done or not metric_done:
            for _ in range(2):
                try:
                    p = next(practice_iter)
                    items.append(self._build_practice_item(user_id_str, feed_date, p, sort_order))
                    sort_order += 1
                except StopIteration:
                    practice_done = True
            try:
                m = next(metric_iter)
                items.append(self._build_metric_item(user_id_str, feed_date, m, sort_order))
                sort_order += 1
            except StopIteration:
                metric_done = True

        # Deduplicate: remove collisions with completed items and internal duplicates
        seen_slugs = set(completed_slugs)
        deduped = []
        for item in items:
            slug = item["problem_slug"]
            if slug not in seen_slugs:
                seen_slugs.add(slug)
                deduped.append(item)
        items = deduped

        if items:
            self.supabase.table("daily_problem_feed").upsert(
                items, on_conflict="user_id,feed_date,problem_slug"
            ).execute()

        return self._get_existing_feed(user_id, feed_date)

    async def _get_practice_problems(
        self, user_id: UUID, count: int, excluded: set = None, focus_notes: Optional[str] = None
    ) -> list[dict]:
        """Get analogous practice problems — NEW problems targeting the same weak concepts."""
        excluded = excluded or set()
        user_id_str = str(user_id)

        # Get context about what needs practice (weak skills, patterns, review topics)
        practice_context = await self.recommendation_engine.get_practice_context(user_id, limit=count)

        # Get all previously seen slugs to exclude
        solved_resp = (
            self.supabase.table("submissions")
            .select("problem_slug")
            .eq("user_id", user_id_str)
            .execute()
        )
        seen_slugs = {s["problem_slug"] for s in (solved_resp.data or [])}
        all_excluded = excluded | seen_slugs

        # Also exclude previous practice slugs from recent feeds
        prev_feed_resp = (
            self.supabase.table("daily_problem_feed")
            .select("problem_slug")
            .eq("user_id", user_id_str)
            .eq("feed_type", "practice")
            .order("feed_date", desc=True)
            .limit(100)
            .execute()
        )
        all_excluded |= {p["problem_slug"] for p in (prev_feed_resp.data or [])}

        if not self.gemini.configured:
            return self._fallback_practice_problems(count, all_excluded, practice_context)

        prompt = self._build_practice_prompt(count, list(all_excluded)[:200], practice_context, focus_notes)

        try:
            response = await asyncio.to_thread(self.gemini.model.generate_content, prompt)
            text = response.text.strip()

            if "```json" in text:
                text = text.split("```json")[1].split("```")[0]
            elif "```" in text:
                text = text.split("```")[1].split("```")[0]

            result = json.loads(text)
            problems = result.get("problems", [])

            filtered = []
            for p in problems:
                slug = p.get("slug", "")
                if slug and slug not in all_excluded:
                    filtered.append({
                        "problem_slug": slug,
                        "problem_title": p.get("title"),
                        "difficulty": p.get("difficulty"),
                        "tags": p.get("tags", []),
                        "source": "analogous",
                        "reason": p.get("rationale", "Analogous practice problem"),
                    })
                    all_excluded.add(slug)
                if len(filtered) >= count:
                    break

            return filtered

        except Exception as e:
            print(f"Gemini practice problem selection failed: {e}")
            return self._fallback_practice_problems(count, all_excluded, practice_context)

    async def _get_metric_problems(
        self, user_id: UUID, count: int, excluded: set = None, focus_notes: Optional[str] = None,
        journal_entries: list[dict] = None,
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
            count, list(all_excluded)[:200], skill_context, targets,
            focus_notes=focus_notes, journal_entries=journal_entries,
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
        focus_notes: Optional[str] = None, journal_entries: list[dict] = None,
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

        journal_section = ""
        if journal_entries:
            entries_text = "\n".join(f"- {e['entry_text']}" for e in journal_entries[:5])
            journal_section = f"\n## User's Self-Identified Mistakes\nThe user has logged these specific mistakes and weak areas. Prioritize problems that address them:\n{entries_text}\n"

        return f"""You are a LeetCode problem selector. Select {count} REAL LeetCode problems that the user has NOT seen before. These are "metric" problems to measure true ability on unseen problems.

## Requirements
- Select REAL LeetCode problems with correct slugs (e.g., "two-sum", "merge-intervals")
- Mix of difficulties: ~{easy_count} Easy, ~{medium_count} Medium, ~{hard_count} Hard
- Cover a variety of topics/patterns
- DO NOT select any of these already-seen slugs: {excluded_slugs[:100]}

## User Context
{skills_text}
Target win rates: Easy {targets.get('easy_target', 0.9)*100:.0f}%, Medium {targets.get('medium_target', 0.7)*100:.0f}%, Hard {targets.get('hard_target', 0.5)*100:.0f}%
{focus_section}{journal_section}
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

    def _build_practice_prompt(
        self, count: int, excluded_slugs: list, context: dict, focus_notes: Optional[str] = None,
    ) -> str:
        """Build Gemini prompt for analogous practice problems."""
        sections = []

        if context.get("weak_skills"):
            skills = ", ".join(f"{s['tag']} (score: {s['score']:.0f})" for s in context["weak_skills"])
            sections.append(f"Weak skill areas needing reinforcement: {skills}")

        if context.get("due_review_topics"):
            topics = []
            for r in context["due_review_topics"][:5]:
                tags_str = ", ".join(r["tags"]) if r["tags"] else "unknown"
                topics.append(f"- {r['original_slug']} (tags: {tags_str}, reason: {r['reason']})")
            sections.append("Problems due for review (find ANALOGOUS problems, NOT these exact ones):\n" + "\n".join(topics))

        if context.get("recurring_patterns"):
            patterns = ", ".join(f"{p['pattern']} ({p['count']}x)" for p in context["recurring_patterns"])
            sections.append(f"Recurring mistake patterns: {patterns}")

        if context.get("journal_topics"):
            entries = "\n".join(f"- {j['text']}" for j in context["journal_topics"])
            sections.append(f"Self-identified mistakes:\n{entries}")

        if focus_notes:
            sections.append(f"User focus notes: {focus_notes}")

        context_text = "\n\n".join(sections) if sections else "No specific weakness data available. Select a diverse mix."

        return f"""You are a LeetCode problem selector. Select {count} REAL LeetCode problems for targeted practice.

## Key Principle
These are ANALOGOUS practice problems. The user has weaknesses in certain areas — select NEW problems that exercise the SAME concepts and patterns, but are DIFFERENT problems they haven't seen. Think: "if they struggled with Two Sum, suggest Three Sum or Two Sum II."

## User's Weak Areas
{context_text}

## Requirements
- Select REAL LeetCode problems with correct slugs (e.g., "two-sum", "three-sum-ii-input-array-is-sorted")
- Problems must target the identified weak areas and patterns
- Mix difficulties: ~30% Easy, ~50% Medium, ~20% Hard
- Each problem should include a rationale explaining which weakness it addresses
- DO NOT select any of these already-seen slugs: {excluded_slugs[:100]}

## Output Format (JSON only)
{{
  "problems": [
    {{
      "slug": "problem-slug",
      "title": "Problem Title",
      "difficulty": "Easy|Medium|Hard",
      "tags": ["Array", "Two Pointers"],
      "rationale": "Practices [concept] — analogous to [original problem] which you struggled with"
    }}
  ]
}}

Only output JSON, nothing else."""

    def _fallback_practice_problems(self, count: int, excluded: set, context: dict) -> list[dict]:
        """Fallback practice problems when Gemini is unavailable, grouped by common weak areas."""
        fallback_pool = [
            {"slug": "two-sum-ii-input-array-is-sorted", "title": "Two Sum II", "difficulty": "Medium", "tags": ["Array", "Two Pointers"]},
            {"slug": "3sum", "title": "3Sum", "difficulty": "Medium", "tags": ["Array", "Two Pointers", "Sorting"]},
            {"slug": "container-with-most-water", "title": "Container With Most Water", "difficulty": "Medium", "tags": ["Array", "Two Pointers"]},
            {"slug": "best-time-to-buy-and-sell-stock-ii", "title": "Best Time to Buy and Sell Stock II", "difficulty": "Medium", "tags": ["Array", "DP", "Greedy"]},
            {"slug": "rotate-array", "title": "Rotate Array", "difficulty": "Medium", "tags": ["Array"]},
            {"slug": "move-zeroes", "title": "Move Zeroes", "difficulty": "Easy", "tags": ["Array", "Two Pointers"]},
            {"slug": "house-robber", "title": "House Robber", "difficulty": "Medium", "tags": ["DP"]},
            {"slug": "coin-change", "title": "Coin Change", "difficulty": "Medium", "tags": ["DP"]},
            {"slug": "unique-paths", "title": "Unique Paths", "difficulty": "Medium", "tags": ["DP"]},
            {"slug": "binary-tree-level-order-traversal", "title": "Binary Tree Level Order Traversal", "difficulty": "Medium", "tags": ["Tree", "BFS"]},
            {"slug": "validate-binary-search-tree", "title": "Validate BST", "difficulty": "Medium", "tags": ["Tree", "DFS"]},
            {"slug": "number-of-islands", "title": "Number of Islands", "difficulty": "Medium", "tags": ["Graph", "BFS", "DFS"]},
            {"slug": "clone-graph", "title": "Clone Graph", "difficulty": "Medium", "tags": ["Graph", "BFS", "DFS"]},
            {"slug": "implement-trie-prefix-tree", "title": "Implement Trie", "difficulty": "Medium", "tags": ["Trie"]},
            {"slug": "kth-largest-element-in-an-array", "title": "Kth Largest Element", "difficulty": "Medium", "tags": ["Heap", "Sorting"]},
            {"slug": "top-k-frequent-elements", "title": "Top K Frequent Elements", "difficulty": "Medium", "tags": ["Hash Table", "Heap"]},
            {"slug": "daily-temperatures", "title": "Daily Temperatures", "difficulty": "Medium", "tags": ["Stack"]},
            {"slug": "longest-common-subsequence", "title": "Longest Common Subsequence", "difficulty": "Medium", "tags": ["DP", "String"]},
            {"slug": "palindromic-substrings", "title": "Palindromic Substrings", "difficulty": "Medium", "tags": ["DP", "String"]},
            {"slug": "search-in-rotated-sorted-array", "title": "Search in Rotated Sorted Array", "difficulty": "Medium", "tags": ["Binary Search", "Array"]},
        ]

        # Score fallback problems by relevance to weak areas
        weak_tags = {s["tag"].lower() for s in context.get("weak_skills", [])}
        review_tags = set()
        for r in context.get("due_review_topics", []):
            for tag in (r.get("tags") or []):
                review_tags.add(tag.lower())
        target_tags = weak_tags | review_tags

        def relevance(p: dict) -> int:
            return sum(1 for t in p["tags"] if t.lower() in target_tags)

        # Sort by relevance, then take top N
        ranked = sorted(
            [p for p in fallback_pool if p["slug"] not in excluded],
            key=relevance,
            reverse=True,
        )

        return [
            {
                "problem_slug": p["slug"],
                "problem_title": p["title"],
                "difficulty": p["difficulty"],
                "tags": p["tags"],
                "source": "analogous",
                "reason": "Analogous practice (from curated pool)",
            }
            for p in ranked[:count]
        ]

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
