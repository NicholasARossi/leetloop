"""Mission Generator Service - Creates personalized daily missions using LLM."""

import json
from datetime import datetime, date, timedelta
from typing import Optional
from uuid import UUID

from supabase import Client

from app.services.gemini_gateway import GeminiGateway


class MissionGenerator:
    """
    Generates personalized daily missions for users.

    The generator:
    1. Gathers context about user's recent struggles and progress
    2. Uses LLM to create a focused daily objective
    3. Selects main quest problems from the user's learning path
    4. Uses LLM to select complementary side quest problems
    """

    def __init__(self, supabase: Client, gemini: Optional[GeminiGateway] = None):
        self.supabase = supabase
        self.gemini = gemini or GeminiGateway()

    async def generate_mission(
        self,
        user_id: UUID,
        mission_date: date = None,
        force_regenerate: bool = False,
    ) -> dict:
        """
        Generate or retrieve a daily mission for a user.

        Args:
            user_id: The user's ID
            mission_date: The date for the mission (defaults to today)
            force_regenerate: Whether to regenerate even if a mission exists

        Returns:
            Mission data dictionary
        """
        if mission_date is None:
            mission_date = date.today()

        # Check for existing mission
        existing = await self._get_existing_mission(user_id, mission_date)

        if existing and not force_regenerate:
            return await self._enrich_mission(existing)

        if existing and force_regenerate:
            # Check regeneration limit
            if existing.get("regenerated_count", 0) >= 3:
                return await self._enrich_mission(existing)

        # Gather context for generation
        context = await self._gather_context(user_id)

        # Generate objective
        objective = await self._generate_objective(context)

        # Get main quests from learning path
        main_quests = await self._get_main_quests(user_id, context)

        # Generate side quests
        side_quests = await self._generate_side_quests(user_id, context, objective)

        # Build mission data
        mission_data = {
            "user_id": str(user_id),
            "mission_date": mission_date.isoformat(),
            "objective_title": objective["title"],
            "objective_description": objective["description"],
            "objective_skill_tags": objective.get("skill_tags", []),
            "main_quests": main_quests,
            "side_quests": side_quests,
            "completed_main_quests": [],
            "completed_side_quests": [],
            "regenerated_count": (existing.get("regenerated_count", 0) + 1) if existing else 0,
            "generated_at": datetime.utcnow().isoformat(),
            "generation_context": context,
        }

        # Save to database
        await self._save_mission(user_id, mission_date, mission_data, existing is not None)

        return await self._enrich_mission(mission_data)

    async def _gather_context(self, user_id: UUID) -> dict:
        """
        Gather context about user's recent performance for mission generation.

        Returns dict with:
        - recent_failures: Problems failed in last 7 days
        - slow_solves: Problems that took many attempts
        - weak_skills: Skills with score < 60
        - path_progress: Current path completion status
        - solved_problems: Set of already-solved problem slugs
        """
        context = {
            "recent_failures": [],
            "slow_solves": [],
            "weak_skills": [],
            "path_progress": {},
            "solved_problems": set(),
        }

        user_id_str = str(user_id)

        # Get ALL recent failures (last 7 days) WITH code for LLM analysis
        seven_days_ago = (datetime.utcnow() - timedelta(days=7)).isoformat()
        failures_response = (
            self.supabase.table("submissions")
            .select("problem_slug, problem_title, difficulty, tags, status, code, language, submitted_at")
            .eq("user_id", user_id_str)
            .neq("status", "Accepted")
            .gte("submitted_at", seven_days_ago)
            .order("submitted_at", desc=True)
            .execute()  # No limit - fetch all for LLM context
        )
        if failures_response.data:
            context["recent_failures"] = failures_response.data
            # Also store failures with code separately for side quest prompt
            context["recent_failures_with_code"] = [
                f for f in failures_response.data if f.get("code")
            ]

        # Get slow solves from problem_attempt_stats
        slow_response = (
            self.supabase.table("problem_attempt_stats")
            .select("problem_slug, problem_title, difficulty, total_attempts, time_to_first_success_seconds")
            .eq("user_id", user_id_str)
            .eq("is_slow_solve", True)
            .order("last_attempt_at", desc=True)
            .limit(10)
            .execute()
        )
        if slow_response.data:
            context["slow_solves"] = slow_response.data

        # Get struggles (currently failing problems)
        struggle_response = (
            self.supabase.table("problem_attempt_stats")
            .select("problem_slug, problem_title, difficulty, failed_attempts")
            .eq("user_id", user_id_str)
            .eq("is_struggle", True)
            .order("last_attempt_at", desc=True)
            .limit(5)
            .execute()
        )
        if struggle_response.data:
            context["struggles"] = struggle_response.data

        # Get weak skills
        skills_response = (
            self.supabase.table("skill_scores")
            .select("tag, score, total_attempts")
            .eq("user_id", user_id_str)
            .lt("score", 60)
            .order("score")
            .limit(5)
            .execute()
        )
        if skills_response.data:
            context["weak_skills"] = skills_response.data

        # Get current path progress
        settings_response = (
            self.supabase.table("user_settings")
            .select("current_path_id")
            .eq("user_id", user_id_str)
            .execute()
        )
        current_path_id = None
        if settings_response.data and settings_response.data[0].get("current_path_id"):
            current_path_id = settings_response.data[0]["current_path_id"]
        else:
            # Default to NeetCode 150
            current_path_id = "11111111-1111-1111-1111-111111111150"

        context["current_path_id"] = current_path_id

        # Get path progress
        progress_response = (
            self.supabase.table("user_path_progress")
            .select("completed_problems, current_category")
            .eq("user_id", user_id_str)
            .eq("path_id", current_path_id)
            .execute()
        )
        if progress_response.data:
            context["path_progress"] = progress_response.data[0]
            context["solved_problems"] = set(progress_response.data[0].get("completed_problems", []) or [])

        # Also add accepted submissions to solved problems
        accepted_response = (
            self.supabase.table("submissions")
            .select("problem_slug")
            .eq("user_id", user_id_str)
            .eq("status", "Accepted")
            .execute()
        )
        if accepted_response.data:
            for s in accepted_response.data:
                context["solved_problems"].add(s["problem_slug"])

        # Convert set to list for JSON serialization
        context["solved_problems"] = list(context["solved_problems"])

        return context

    async def _generate_objective(self, context: dict) -> dict:
        """
        Use LLM to generate a focused daily objective based on user's struggles.

        Returns:
            Dict with title, description, skill_tags
        """
        # Build prompt
        failures_summary = []
        if context.get("recent_failures"):
            tag_counts = {}
            for f in context["recent_failures"]:
                for tag in (f.get("tags") or []):
                    tag_counts[tag] = tag_counts.get(tag, 0) + 1
            failures_summary = sorted(tag_counts.items(), key=lambda x: -x[1])[:5]

        slow_summary = []
        if context.get("slow_solves"):
            slow_summary = [
                f"{s['problem_title']} ({s['total_attempts']} attempts)"
                for s in context["slow_solves"][:3]
            ]

        weak_summary = []
        if context.get("weak_skills"):
            weak_summary = [
                f"{s['tag']} (score: {s['score']:.0f}%)"
                for s in context["weak_skills"]
            ]

        prompt = f"""Based on this LeetCode learner's recent performance, generate a focused daily objective.

Recent failure patterns (tag: count):
{failures_summary if failures_summary else "No recent failures"}

Slow solves (took many attempts):
{slow_summary if slow_summary else "None"}

Weak skill areas:
{weak_summary if weak_summary else "No data yet"}

Generate a motivating daily objective that:
1. Targets the MOST important weakness pattern
2. Is specific and achievable in one session
3. Frames the struggle positively

Output as JSON:
{{
  "title": "Master [pattern/skill]",
  "description": "A 1-2 sentence description of why this focus will help and what to practice",
  "skill_tags": ["tag1", "tag2"]
}}

Only output the JSON, nothing else."""

        if not self.gemini.configured:
            # Fallback when LLM not available
            if weak_summary:
                primary_skill = context["weak_skills"][0]["tag"]
                return {
                    "title": f"Strengthen {primary_skill}",
                    "description": f"Your {primary_skill} skills need work. Focus on understanding the core pattern through deliberate practice.",
                    "skill_tags": [primary_skill],
                }
            return {
                "title": "Build Your Foundation",
                "description": "Focus on solving problems consistently. Each attempt teaches you something valuable.",
                "skill_tags": [],
            }

        try:
            response = self.gemini.model.generate_content(prompt)
            text = response.text.strip()
            # Extract JSON from response
            if "```json" in text:
                text = text.split("```json")[1].split("```")[0]
            elif "```" in text:
                text = text.split("```")[1].split("```")[0]
            return json.loads(text)
        except Exception as e:
            print(f"LLM objective generation failed: {e}")
            # Fallback
            if context.get("weak_skills"):
                primary_skill = context["weak_skills"][0]["tag"]
                return {
                    "title": f"Strengthen {primary_skill}",
                    "description": f"Focus on {primary_skill} problems today to build a stronger foundation.",
                    "skill_tags": [primary_skill],
                }
            return {
                "title": "Build Your Foundation",
                "description": "Focus on solving problems consistently today.",
                "skill_tags": [],
            }

    def _build_side_quest_prompt(
        self,
        context: dict,
        candidate_quests: list[dict],
        path_info: dict,
    ) -> str:
        """
        Build a rich prompt for LLM-driven side quest selection.

        Includes:
        - Current position in NeetCode 150 (main plot)
        - All failures from last 7 days WITH code
        - List of solved problems
        - Candidate problems pool
        """
        prompt_parts = []

        # Section 1: Main plot position
        current_category = context.get("path_progress", {}).get("current_category", "Unknown")
        solved_count = len(context.get("solved_problems", []))
        total_problems = path_info.get("total_problems", 150)
        upcoming = path_info.get("upcoming_in_category", [])

        prompt_parts.append(f"""## Your Position in NeetCode 150 (Main Plot)
Current Category: {current_category}
Problems Completed: {solved_count}/{total_problems}
Next up in path: {', '.join(upcoming[:3]) if upcoming else 'None'}

This learner is working through "{current_category}" - side quests should complement this focus.""")

        # Section 2: All failures with code
        failures_with_code = context.get("recent_failures_with_code", [])
        if failures_with_code:
            prompt_parts.append("\n## All Failures from Last 7 Days (with code)\n")
            for i, f in enumerate(failures_with_code, 1):
                title = f.get("problem_title") or f.get("problem_slug", "").replace("-", " ").title()
                difficulty = f.get("difficulty", "Unknown")
                status = f.get("status", "Failed")
                tags = ", ".join(f.get("tags") or []) or "No tags"
                language = f.get("language", "python")
                code = f.get("code", "# No code available")

                prompt_parts.append(f"""### Failure {i}: {title} ({difficulty}) - {status}
Tags: {tags}
Language: {language}

```{language}
{code}
```
""")
        else:
            prompt_parts.append("\n## Recent Failures\nNo failures with code in the last 7 days.\n")

        # Section 3: Solved problems (truncated list)
        solved = context.get("solved_problems", [])
        solved_display = ", ".join(solved[:50])
        if len(solved) > 50:
            solved_display += f", ... ({len(solved)} total)"
        prompt_parts.append(f"\n## Solved Problems ({len(solved)} total)\n{solved_display}\n")

        # Section 4: Candidate problems
        prompt_parts.append("\n## Candidate Problems for Side Quests")
        for cq in candidate_quests:
            prompt_parts.append(f"- {cq['slug']}: {cq['title']} ({cq.get('difficulty', 'Unknown')}) - Source: {cq['quest_type']}")

        # Section 5: Instructions
        prompt_parts.append("""
## Your Task
Analyze ALL the failure code above. Look for:
1. CODE PATTERNS: What mistakes keep appearing? (e.g., O(n^3) brute force instead of O(n^2) two pointers)
2. ALGORITHM GAPS: Which techniques don't they understand? (e.g., not using sorted array with two pointers)
3. ERROR TYPES: TLE = efficiency problem, WA = logic bug, RE = edge cases

Select 2-3 side quests from the candidates that:
1. Address the ROOT CAUSE of failures (not symptoms)
2. Complement their current NeetCode 150 category
3. Build toward mastery of the weak pattern

If no candidates are appropriate, explain why and suggest what type of problem would help.

Output JSON only:
{
  "analysis": "Brief analysis of the learner's struggle patterns based on the code",
  "side_quests": [
    {
      "slug": "problem-slug-from-candidates",
      "title": "Problem Title",
      "reason": "Why this problem addresses the root cause of their failures",
      "target_weakness": "The skill or pattern this addresses",
      "quest_type": "skill_gap|review_due|slow_solve"
    }
  ]
}""")

        return "\n".join(prompt_parts)

    async def _get_path_info(self, context: dict) -> dict:
        """Get path metadata for the side quest prompt."""
        path_id = context.get("current_path_id", "11111111-1111-1111-1111-111111111150")
        solved = set(context.get("solved_problems", []))
        current_category = context.get("path_progress", {}).get("current_category")

        path_response = (
            self.supabase.table("learning_paths")
            .select("categories, name")
            .eq("id", path_id)
            .single()
            .execute()
        )

        if not path_response.data:
            return {"total_problems": 150, "upcoming_in_category": []}

        categories = path_response.data.get("categories", [])
        total_problems = sum(len(cat.get("problems", [])) for cat in categories)

        # Find upcoming problems in current category
        upcoming = []
        for cat in categories:
            if cat.get("name") == current_category:
                for prob in sorted(cat.get("problems", []), key=lambda x: x.get("order", 0)):
                    if prob["slug"] not in solved:
                        upcoming.append(prob["title"])
                break

        return {
            "total_problems": total_problems,
            "upcoming_in_category": upcoming,
            "path_name": path_response.data.get("name", "NeetCode 150"),
        }

    async def _get_main_quests(self, user_id: UUID, context: dict) -> list[dict]:
        """
        Get next problems from user's learning path as main quests.

        Returns list of up to 5 problems in order.
        """
        path_id = context.get("current_path_id", "11111111-1111-1111-1111-111111111150")
        solved = set(context.get("solved_problems", []))

        # Get path data
        path_response = (
            self.supabase.table("learning_paths")
            .select("categories")
            .eq("id", path_id)
            .single()
            .execute()
        )

        if not path_response.data:
            return []

        categories = path_response.data.get("categories", [])
        main_quests = []

        for cat in sorted(categories, key=lambda x: x.get("order", 0)):
            if len(main_quests) >= 5:
                break
            for prob in sorted(cat.get("problems", []), key=lambda x: x.get("order", 0)):
                if len(main_quests) >= 5:
                    break

                status = "completed" if prob["slug"] in solved else "upcoming"
                if status == "upcoming" and not any(q["status"] == "current" for q in main_quests):
                    status = "current"

                # Include some completed to show progress, but prioritize uncompleted
                if status == "completed" and len([q for q in main_quests if q["status"] == "completed"]) >= 2:
                    continue

                main_quests.append({
                    "slug": prob["slug"],
                    "title": prob["title"],
                    "difficulty": prob.get("difficulty"),
                    "category": cat["name"],
                    "order": len(main_quests) + 1,
                    "status": status,
                })

        return main_quests

    async def _generate_side_quests(
        self,
        user_id: UUID,
        context: dict,
        objective: dict,
    ) -> list[dict]:
        """
        Generate side quests using LLM-driven selection with rich context.

        Process:
        1. Gather candidate pool (reviews, weak skills, slow solves)
        2. Build rich prompt with code context
        3. Call Gemini to SELECT and EXPLAIN side quests
        4. Fall back to rule-based if LLM fails

        Returns list of 2-3 side quests.
        """
        user_id_str = str(user_id)
        solved = set(context.get("solved_problems", []))

        # Step 1: Gather candidate pool
        candidate_quests = []

        # 1a. Check for reviews due
        reviews_response = (
            self.supabase.table("review_queue")
            .select("problem_slug, problem_title, reason")
            .eq("user_id", user_id_str)
            .lte("next_review", datetime.utcnow().isoformat())
            .order("priority", desc=True)
            .limit(3)
            .execute()
        )
        if reviews_response.data:
            for r in reviews_response.data:
                candidate_quests.append({
                    "slug": r["problem_slug"],
                    "title": r.get("problem_title") or r["problem_slug"].replace("-", " ").title(),
                    "difficulty": None,
                    "reason": r.get("reason", "Due for review - failed previously"),
                    "source_problem_slug": None,
                    "target_weakness": "retention",
                    "quest_type": "review_due",
                    "completed": False,
                })

        # 1b. Add skill gap problems
        if context.get("weak_skills"):
            for skill in context["weak_skills"]:
                failed_response = (
                    self.supabase.table("submissions")
                    .select("problem_slug, problem_title, difficulty")
                    .eq("user_id", user_id_str)
                    .neq("status", "Accepted")
                    .contains("tags", [skill["tag"]])
                    .order("submitted_at", desc=True)
                    .limit(2)
                    .execute()
                )
                if failed_response.data:
                    for prob in failed_response.data:
                        if prob["problem_slug"] not in solved and not any(
                            q["slug"] == prob["problem_slug"] for q in candidate_quests
                        ):
                            candidate_quests.append({
                                "slug": prob["problem_slug"],
                                "title": prob.get("problem_title") or prob["problem_slug"].replace("-", " ").title(),
                                "difficulty": prob.get("difficulty"),
                                "reason": f"Strengthen {skill['tag']} (score: {skill['score']:.0f}%)",
                                "source_problem_slug": None,
                                "target_weakness": skill["tag"],
                                "quest_type": "skill_gap",
                                "completed": False,
                            })

        # 1c. Add slow solve retries
        if context.get("slow_solves"):
            for slow in context["slow_solves"]:
                if not any(q["slug"] == slow["problem_slug"] for q in candidate_quests):
                    candidate_quests.append({
                        "slug": slow["problem_slug"],
                        "title": slow.get("problem_title") or slow["problem_slug"].replace("-", " ").title(),
                        "difficulty": slow.get("difficulty"),
                        "reason": f"Took {slow['total_attempts']} attempts - solidify your understanding",
                        "source_problem_slug": None,
                        "target_weakness": "slow_solve",
                        "quest_type": "slow_solve",
                        "completed": False,
                    })

        # If no candidates, return empty
        if not candidate_quests:
            return []

        # Step 2: Try LLM-driven selection if configured and we have code context
        if self.gemini.configured and context.get("recent_failures_with_code"):
            try:
                path_info = await self._get_path_info(context)
                prompt = self._build_side_quest_prompt(context, candidate_quests, path_info)

                response = self.gemini.model.generate_content(prompt)
                text = response.text.strip()

                # Extract JSON from response
                if "```json" in text:
                    text = text.split("```json")[1].split("```")[0]
                elif "```" in text:
                    text = text.split("```")[1].split("```")[0]

                llm_response = json.loads(text)

                # Build side quests from LLM selection
                llm_side_quests = []
                candidate_map = {cq["slug"]: cq for cq in candidate_quests}

                for sq in llm_response.get("side_quests", []):
                    slug = sq.get("slug")
                    if slug in candidate_map:
                        base = candidate_map[slug].copy()
                        # Use LLM's explanation as reason
                        base["reason"] = sq.get("reason", base["reason"])
                        base["target_weakness"] = sq.get("target_weakness", base["target_weakness"])
                        base["quest_type"] = sq.get("quest_type", base["quest_type"])
                        base["llm_analysis"] = llm_response.get("analysis", "")
                        llm_side_quests.append(base)

                if llm_side_quests:
                    print(f"LLM selected {len(llm_side_quests)} side quests")
                    return llm_side_quests[:3]

            except Exception as e:
                print(f"LLM side quest selection failed: {e}, falling back to rule-based")

        # Step 3: Fall back to rule-based selection
        return self._rule_based_side_quests(candidate_quests)

    def _rule_based_side_quests(self, candidates: list[dict]) -> list[dict]:
        """
        Rule-based fallback for side quest selection.

        Priority:
        1. Review due items (spaced repetition)
        2. Skill gap problems
        3. Slow solve retries
        """
        side_quests = []
        quest_type_priority = ["review_due", "skill_gap", "slow_solve"]

        for quest_type in quest_type_priority:
            for cq in candidates:
                if len(side_quests) >= 3:
                    break
                if cq["quest_type"] == quest_type and cq["slug"] not in [q["slug"] for q in side_quests]:
                    side_quests.append(cq)

        return side_quests[:3]

    async def _get_existing_mission(self, user_id: UUID, mission_date: date) -> Optional[dict]:
        """Get existing mission for the date if it exists."""
        response = (
            self.supabase.table("daily_missions")
            .select("*")
            .eq("user_id", str(user_id))
            .eq("mission_date", mission_date.isoformat())
            .execute()
        )
        if response.data:
            return response.data[0]
        return None

    async def _save_mission(
        self,
        user_id: UUID,
        mission_date: date,
        mission_data: dict,
        is_update: bool,
    ) -> None:
        """Save or update the mission in the database."""
        data = {
            "user_id": str(user_id),
            "mission_date": mission_date.isoformat(),
            "objective_title": mission_data["objective_title"],
            "objective_description": mission_data["objective_description"],
            "objective_skill_tags": mission_data["objective_skill_tags"],
            "main_quests": mission_data["main_quests"],
            "side_quests": mission_data["side_quests"],
            "completed_main_quests": mission_data["completed_main_quests"],
            "completed_side_quests": mission_data["completed_side_quests"],
            "regenerated_count": mission_data["regenerated_count"],
            "generated_at": mission_data["generated_at"],
            "generation_context": mission_data["generation_context"],
            "updated_at": datetime.utcnow().isoformat(),
        }

        if is_update:
            self.supabase.table("daily_missions").update(data).eq(
                "user_id", str(user_id)
            ).eq("mission_date", mission_date.isoformat()).execute()
        else:
            self.supabase.table("daily_missions").insert(data).execute()

    async def _enrich_mission(self, mission_data: dict) -> dict:
        """
        Enrich mission data with computed fields for the response.

        Adds streak, completion counts, quest statuses, etc.
        """
        user_id = mission_data["user_id"]

        # Get streak
        streak = 0
        streak_response = (
            self.supabase.table("user_streaks")
            .select("current_streak, last_activity_date")
            .eq("user_id", user_id)
            .execute()
        )
        if streak_response.data:
            streak_data = streak_response.data[0]
            last_date = streak_data.get("last_activity_date")
            if last_date:
                last_date_obj = datetime.fromisoformat(last_date.replace("Z", "+00:00")).date() if isinstance(last_date, str) else last_date
                days_diff = (date.today() - last_date_obj).days
                if days_diff <= 1:
                    streak = streak_data.get("current_streak", 0)

        # Get today's completed problems from submissions
        today = date.today().isoformat()
        completed_today_response = (
            self.supabase.table("submissions")
            .select("problem_slug")
            .eq("user_id", user_id)
            .eq("status", "Accepted")
            .gte("submitted_at", f"{today}T00:00:00")
            .execute()
        )
        completed_today_slugs = set()
        if completed_today_response.data:
            completed_today_slugs = {s["problem_slug"] for s in completed_today_response.data}

        # Update main quest statuses
        main_quests = mission_data.get("main_quests", [])
        completed_main = set(mission_data.get("completed_main_quests", []))
        has_current = False

        for quest in main_quests:
            if quest["slug"] in completed_today_slugs or quest["slug"] in completed_main:
                quest["status"] = "completed"
            elif not has_current and quest.get("status") != "completed":
                quest["status"] = "current"
                has_current = True
            else:
                quest["status"] = "upcoming"

        # Update side quest completion
        side_quests = mission_data.get("side_quests", [])
        completed_side = set(mission_data.get("completed_side_quests", []))
        for quest in side_quests:
            quest["completed"] = quest["slug"] in completed_today_slugs or quest["slug"] in completed_side

        # Count completions
        main_completed = sum(1 for q in main_quests if q.get("status") == "completed")
        side_completed = sum(1 for q in side_quests if q.get("completed"))
        total_completed = main_completed + side_completed

        return {
            "user_id": user_id,
            "mission_date": mission_data["mission_date"],
            "objective": {
                "title": mission_data["objective_title"],
                "description": mission_data["objective_description"],
                "skill_tags": mission_data.get("objective_skill_tags", []),
                "target_count": len(main_quests) + len(side_quests),
                "completed_count": total_completed,
            },
            "main_quests": main_quests,
            "side_quests": side_quests,
            "streak": streak,
            "total_completed_today": len(completed_today_slugs),
            "can_regenerate": mission_data.get("regenerated_count", 0) < 3,
            "generated_at": mission_data["generated_at"],
        }

    async def generate_all_missions(self) -> dict:
        """
        Generate missions for all active users.

        Called by cron job for batch generation.

        Returns:
            Dict with counts of generated, skipped, failed
        """
        # Get users with activity in last 30 days
        thirty_days_ago = (datetime.utcnow() - timedelta(days=30)).isoformat()
        users_response = (
            self.supabase.table("submissions")
            .select("user_id")
            .gte("submitted_at", thirty_days_ago)
            .execute()
        )

        if not users_response.data:
            return {"generated": 0, "skipped": 0, "failed": 0}

        # Deduplicate user IDs
        user_ids = list(set(row["user_id"] for row in users_response.data))

        generated = 0
        skipped = 0
        failed = 0

        for user_id in user_ids:
            try:
                # Check if mission already exists for today
                existing = await self._get_existing_mission(UUID(user_id), date.today())
                if existing:
                    skipped += 1
                    continue

                await self.generate_mission(UUID(user_id))
                generated += 1
            except Exception as e:
                print(f"Failed to generate mission for {user_id}: {e}")
                failed += 1

        return {
            "generated": generated,
            "skipped": skipped,
            "failed": failed,
            "total_users": len(user_ids),
        }
