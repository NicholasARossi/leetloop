"""Mission Generator Service - Gemini-driven daily mission generation."""

import json
from datetime import datetime, date, timedelta
from typing import Optional
from uuid import UUID

from supabase import Client

from app.services.gemini_gateway import GeminiGateway
from app.utils import parse_iso_datetime


class MissionGenerator:
    """
    Generates personalized daily missions using Gemini as the brain.

    The generator synthesizes ALL user data to create optimal practice sessions:
    - User's career goal (company/role/deadline)
    - Current learning path progress
    - Skill scores by domain
    - Review queue (failed problems)
    - Submission history and patterns

    Gemini outputs:
    - Daily focus objective
    - 4-6 problems with reasoning for each selection
    - Balance explanation (path vs gap-filling)
    - Pacing status relative to goal
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
            Mission data dictionary with problems and reasoning
        """
        if mission_date is None:
            mission_date = date.today()

        # Check for existing mission
        existing = await self._get_existing_mission(user_id, mission_date)

        if existing and not force_regenerate:
            return await self._enrich_mission(existing, user_id)

        if existing and force_regenerate:
            # Check regeneration limit
            if existing.get("regenerated_count", 0) >= 3:
                enriched = await self._enrich_mission(existing, user_id)
                enriched["can_regenerate"] = False
                return enriched

        # Build comprehensive context for Gemini
        context = await self._build_gemini_context(user_id)

        # Generate mission with Gemini
        gemini_response = await self._call_gemini(context)

        # Build and save mission
        mission_data = await self._build_mission_data(
            user_id,
            mission_date,
            gemini_response,
            context,
            existing,
        )

        return await self._enrich_mission(mission_data, user_id)

    async def _build_gemini_context(self, user_id: UUID) -> dict:
        """
        Build comprehensive context for Gemini mission generation.

        Gathers:
        - User's career goal (from meta_objectives)
        - Current learning path + progress
        - Skill scores by domain
        - Review queue items
        - Recent submission patterns
        """
        user_id_str = str(user_id)
        context = {
            "target_company": None,
            "target_role": None,
            "target_deadline": None,
            "weekly_commitment": 25,
            "days_until_deadline": None,
            "current_path": None,
            "skill_scores": [],
            "review_queue": [],
            "problems_attempted_total": 0,
            "problems_solved_total": 0,
            "current_streak": 0,
            "recent_failure_patterns": [],
            "recent_slow_solves": [],
            "solved_problems": [],
        }

        # Get user's objective (goal)
        objective_response = (
            self.supabase.table("meta_objectives")
            .select("*")
            .eq("user_id", user_id_str)
            .eq("status", "active")
            .limit(1)
            .execute()
        )

        if objective_response.data:
            obj = objective_response.data[0]
            context["target_company"] = obj.get("target_company")
            context["target_role"] = obj.get("target_role")
            context["weekly_commitment"] = obj.get("weekly_problem_target", 25)

            deadline = obj.get("target_deadline")
            if deadline:
                if isinstance(deadline, str):
                    deadline = datetime.fromisoformat(deadline).date()
                context["target_deadline"] = deadline.isoformat()
                context["days_until_deadline"] = (deadline - date.today()).days

        # Get current path
        settings_response = (
            self.supabase.table("user_settings")
            .select("current_path_id")
            .eq("user_id", user_id_str)
            .execute()
        )

        current_path_id = "11111111-1111-1111-1111-111111111150"  # Default NeetCode 150
        if settings_response.data and settings_response.data[0].get("current_path_id"):
            current_path_id = settings_response.data[0]["current_path_id"]

        # Get path details
        path_response = (
            self.supabase.table("learning_paths")
            .select("id, name, categories")
            .eq("id", current_path_id)
            .single()
            .execute()
        )

        # Get path progress
        progress_response = (
            self.supabase.table("user_path_progress")
            .select("completed_problems, current_category")
            .eq("user_id", user_id_str)
            .eq("path_id", current_path_id)
            .execute()
        )

        completed_problems = []
        current_category = None
        if progress_response.data:
            completed_problems = progress_response.data[0].get("completed_problems", []) or []
            current_category = progress_response.data[0].get("current_category")

        # Also get solved from submissions
        accepted_response = (
            self.supabase.table("submissions")
            .select("problem_slug")
            .eq("user_id", user_id_str)
            .eq("status", "Accepted")
            .execute()
        )
        if accepted_response.data:
            solved_slugs = {s["problem_slug"] for s in accepted_response.data}
            completed_problems = list(set(completed_problems) | solved_slugs)

        context["solved_problems"] = completed_problems

        if path_response.data:
            categories = path_response.data.get("categories", [])
            total_problems = sum(len(cat.get("problems", [])) for cat in categories)

            # Find next uncompleted problem index
            solved_set = set(completed_problems)
            next_index = 0
            for cat in sorted(categories, key=lambda x: x.get("order", 0)):
                for prob in sorted(cat.get("problems", []), key=lambda x: x.get("order", 0)):
                    if prob["slug"] not in solved_set:
                        break
                    next_index += 1
                else:
                    continue
                break

            context["current_path"] = {
                "id": current_path_id,
                "name": path_response.data.get("name", "NeetCode 150"),
                "total_problems": total_problems,
                "completed_count": len(completed_problems),
                "next_uncompleted_index": next_index,
                "current_category": current_category,
                "categories": categories,  # Include for problem selection
            }

        # Get skill scores
        skills_response = (
            self.supabase.table("skill_scores")
            .select("tag, score, total_attempts, avg_time_seconds")
            .eq("user_id", user_id_str)
            .order("score")
            .execute()
        )

        if skills_response.data:
            for skill in skills_response.data:
                score = skill.get("score", 0)
                if score < 40:
                    status = "weak"
                elif score < 60:
                    status = "developing"
                elif score < 80:
                    status = "proficient"
                else:
                    status = "mastered"

                context["skill_scores"].append({
                    "domain": skill["tag"],
                    "score": score,
                    "status": status,
                    "recent_failures": 0,  # TODO: calculate
                    "average_solve_time": skill.get("avg_time_seconds"),
                })

        # Get review queue
        reviews_response = (
            self.supabase.table("review_queue")
            .select("problem_slug, reason, next_review, interval_days, last_reviewed")
            .eq("user_id", user_id_str)
            .lte("next_review", datetime.utcnow().isoformat())
            .order("priority", desc=True)
            .limit(5)
            .execute()
        )

        if reviews_response.data:
            for review in reviews_response.data:
                last_attempt = review.get("last_reviewed") or review.get("next_review")
                context["review_queue"].append({
                    "problem_id": review["problem_slug"],
                    "last_attempt": last_attempt,
                    "failure_reason": review.get("reason"),
                    "interval": review.get("interval_days", 1),
                })

        # Get submission counts
        stats_response = (
            self.supabase.table("submissions")
            .select("id, status", count="exact")
            .eq("user_id", user_id_str)
            .execute()
        )

        if stats_response.count:
            context["problems_attempted_total"] = stats_response.count

        solved_response = (
            self.supabase.table("submissions")
            .select("problem_slug")
            .eq("user_id", user_id_str)
            .eq("status", "Accepted")
            .execute()
        )

        if solved_response.data:
            context["problems_solved_total"] = len(set(s["problem_slug"] for s in solved_response.data))

        # Get streak
        streak_response = (
            self.supabase.table("user_streaks")
            .select("current_streak, last_activity_date")
            .eq("user_id", user_id_str)
            .execute()
        )

        if streak_response.data:
            streak_data = streak_response.data[0]
            last_date = streak_data.get("last_activity_date")
            if last_date:
                try:
                    last_date_obj = parse_iso_datetime(last_date).date() if isinstance(last_date, str) else last_date
                    days_diff = (date.today() - last_date_obj).days
                    if days_diff <= 1:
                        context["current_streak"] = streak_data.get("current_streak", 0)
                except Exception:
                    pass

        # Get recent failure patterns
        seven_days_ago = (datetime.utcnow() - timedelta(days=7)).isoformat()
        failures_response = (
            self.supabase.table("submissions")
            .select("tags")
            .eq("user_id", user_id_str)
            .neq("status", "Accepted")
            .gte("submitted_at", seven_days_ago)
            .execute()
        )

        if failures_response.data:
            tag_counts = {}
            for f in failures_response.data:
                for tag in (f.get("tags") or []):
                    tag_counts[tag] = tag_counts.get(tag, 0) + 1
            # Top 5 failure patterns
            sorted_tags = sorted(tag_counts.items(), key=lambda x: -x[1])[:5]
            context["recent_failure_patterns"] = [tag for tag, _ in sorted_tags]

        # Get slow solves
        slow_response = (
            self.supabase.table("problem_attempt_stats")
            .select("problem_slug")
            .eq("user_id", user_id_str)
            .eq("is_slow_solve", True)
            .order("last_attempt_at", desc=True)
            .limit(5)
            .execute()
        )

        if slow_response.data:
            context["recent_slow_solves"] = [s["problem_slug"] for s in slow_response.data]

        return context

    async def _call_gemini(self, context: dict) -> dict:
        """
        Call Gemini to generate the daily mission.

        Returns structured response with problems and reasoning.
        """
        # Build available problems pool from path
        available_problems = []
        path = context.get("current_path")
        solved_set = set(context.get("solved_problems", []))

        if path and path.get("categories"):
            for cat in sorted(path["categories"], key=lambda x: x.get("order", 0)):
                for prob in sorted(cat.get("problems", []), key=lambda x: x.get("order", 0)):
                    if prob["slug"] not in solved_set:
                        available_problems.append({
                            "slug": prob["slug"],
                            "title": prob["title"],
                            "difficulty": prob.get("difficulty"),
                            "category": cat["name"],
                        })

        # Build review problems
        review_problems = [
            {"slug": r["problem_id"], "reason": r.get("failure_reason", "Due for review")}
            for r in context.get("review_queue", [])
        ]

        prompt = self._build_gemini_prompt(context, available_problems, review_problems)

        if not self.gemini.configured:
            return self._fallback_mission(context, available_problems, review_problems)

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
            print(f"Gemini mission generation failed: {e}")
            return self._fallback_mission(context, available_problems, review_problems)

    def _build_gemini_prompt(
        self,
        context: dict,
        available_problems: list,
        review_problems: list,
    ) -> str:
        """Build the Gemini prompt for mission generation."""

        # Goal section
        goal_section = "## User Goal\n"
        if context.get("target_company"):
            goal_section += f"Target: {context['target_company']} - {context.get('target_role', 'Software Engineer')}\n"
            if context.get("days_until_deadline"):
                goal_section += f"Days until deadline: {context['days_until_deadline']}\n"
            goal_section += f"Weekly commitment: {context.get('weekly_commitment', 25)} problems\n"
        else:
            goal_section += "No specific goal set - focus on balanced skill development\n"

        # Path section
        path_section = "## Current Learning Path\n"
        if context.get("current_path"):
            path = context["current_path"]
            progress_pct = (path["completed_count"] / path["total_problems"] * 100) if path["total_problems"] > 0 else 0
            path_section += f"Path: {path['name']}\n"
            path_section += f"Progress: {path['completed_count']}/{path['total_problems']} ({progress_pct:.0f}%)\n"
            if path.get("current_category"):
                path_section += f"Current category: {path['current_category']}\n"
        else:
            path_section += "No learning path selected\n"

        # Skills section
        skills_section = "## Skill Scores\n"
        weak_skills = [s for s in context.get("skill_scores", []) if s["status"] in ["weak", "developing"]]
        strong_skills = [s for s in context.get("skill_scores", []) if s["status"] in ["proficient", "mastered"]]

        if weak_skills:
            skills_section += "WEAK areas (need focus):\n"
            for s in weak_skills[:5]:
                skills_section += f"  - {s['domain']}: {s['score']:.0f}% ({s['status']})\n"
        if strong_skills:
            skills_section += "STRONG areas:\n"
            for s in strong_skills[:3]:
                skills_section += f"  - {s['domain']}: {s['score']:.0f}%\n"
        if not weak_skills and not strong_skills:
            skills_section += "No skill data yet\n"

        # Review queue section
        review_section = "## Review Queue (Due for Spaced Repetition)\n"
        if review_problems:
            for r in review_problems:
                skills_section += f"  - {r['slug']}: {r.get('reason', 'Failed previously')}\n"
        else:
            review_section += "No reviews due\n"

        # Available problems section
        problems_section = "## Available Problems from Path\n"
        if available_problems:
            for p in available_problems[:15]:  # Show next 15
                problems_section += f"  - {p['slug']}: {p['title']} ({p['difficulty']}) - {p['category']}\n"
        else:
            problems_section += "No problems available\n"

        # Recent patterns
        patterns_section = "## Recent Patterns\n"
        if context.get("recent_failure_patterns"):
            patterns_section += f"Common failure topics: {', '.join(context['recent_failure_patterns'])}\n"
        if context.get("recent_slow_solves"):
            patterns_section += f"Slow solves: {', '.join(context['recent_slow_solves'][:3])}\n"
        patterns_section += f"Current streak: {context.get('current_streak', 0)} days\n"
        patterns_section += f"Total solved: {context.get('problems_solved_total', 0)} problems\n"

        prompt = f"""You are a LeetCode practice coach. Generate a personalized daily mission based on all user data.

{goal_section}

{path_section}

{skills_section}

{review_section}

{patterns_section}

{problems_section}

## Instructions
Generate an optimal daily practice session (4-6 problems):
1. PRIORITIZE review items if any are due (spaced repetition is critical)
2. Include problems from the learning path to maintain progress
3. Mix in gap-filling problems to address weak skills
4. You MAY reorder path problems if it helps hit multiple learning objectives
5. Always explain WHY each problem was chosen
6. Consider deadline pacing - are they ahead or behind?

## Output Format (JSON only)
{{
  "daily_objective": "Short phrase describing today's focus (e.g., 'Master Two Pointer patterns')",
  "problems": [
    {{
      "problem_id": "problem-slug-from-available",
      "source": "path|gap_fill|review|reinforcement",
      "reasoning": "Why this problem was chosen - be specific",
      "priority": 1,
      "skills": ["skill1", "skill2"],
      "estimated_difficulty": "easy|medium|hard"
    }}
  ],
  "balance_explanation": "Today is X% path, Y% gap-filling because...",
  "pacing_status": "ahead|on_track|behind|critical",
  "pacing_note": "You're X days ahead/behind schedule" or "On track for your deadline"
}}

Only output the JSON, nothing else."""

        return prompt

    def _fallback_mission(
        self,
        context: dict,
        available_problems: list,
        review_problems: list,
    ) -> dict:
        """Generate fallback mission when Gemini is unavailable."""
        problems = []

        # Add reviews first (max 2)
        for i, r in enumerate(review_problems[:2]):
            problems.append({
                "problem_id": r["slug"],
                "source": "review",
                "reasoning": r.get("reason", "Due for spaced repetition review"),
                "priority": i + 1,
                "skills": [],
                "estimated_difficulty": "medium",
            })

        # Add path problems (fill to 5 total)
        remaining = 5 - len(problems)
        for i, p in enumerate(available_problems[:remaining]):
            problems.append({
                "problem_id": p["slug"],
                "source": "path",
                "reasoning": f"Next problem in your {p['category']} progression",
                "priority": len(problems) + 1,
                "skills": [p["category"]],
                "estimated_difficulty": p.get("difficulty", "medium").lower(),
            })

        # Determine objective
        weak_skills = [s for s in context.get("skill_scores", []) if s["status"] == "weak"]
        if weak_skills:
            objective = f"Strengthen {weak_skills[0]['domain']}"
        elif review_problems:
            objective = "Review and consolidate"
        else:
            objective = "Continue learning path progress"

        # Calculate pacing
        pacing_status = "on_track"
        pacing_note = "Keep up the consistent practice!"
        if context.get("days_until_deadline"):
            days = context["days_until_deadline"]
            if days < 14:
                pacing_status = "critical"
                pacing_note = f"Only {days} days until deadline - increase daily practice"
            elif days < 30:
                pacing_status = "behind"
                pacing_note = f"{days} days remaining - stay focused"

        return {
            "daily_objective": objective,
            "problems": problems,
            "balance_explanation": "Balanced mix of reviews and new path problems",
            "pacing_status": pacing_status,
            "pacing_note": pacing_note,
        }

    async def _build_mission_data(
        self,
        user_id: UUID,
        mission_date: date,
        gemini_response: dict,
        context: dict,
        existing: dict = None,
    ) -> dict:
        """Build mission data structure and save to database."""
        user_id_str = str(user_id)

        # Get problem details for each selected problem
        problem_details = {}
        path = context.get("current_path", {})
        if path.get("categories"):
            for cat in path["categories"]:
                for prob in cat.get("problems", []):
                    problem_details[prob["slug"]] = {
                        "title": prob["title"],
                        "difficulty": prob.get("difficulty"),
                        "category": cat["name"],
                    }

        # Enrich problems with titles
        # Handle both formats: "problems" array (expected) or "main_quests" (Gemini sometimes returns)
        problems = []
        raw_problems = gemini_response.get("problems", [])

        # If no "problems" key, try extracting from main_quests
        if not raw_problems and gemini_response.get("main_quests"):
            raw_problems = gemini_response.get("main_quests", [])

        for i, p in enumerate(raw_problems):
            # Handle both "problem_id" and "slug" field names
            problem_id = p.get("problem_id") or p.get("slug")
            if not problem_id:
                continue
            details = problem_details.get(problem_id, {})
            problems.append({
                "problem_id": problem_id,
                "problem_title": details.get("title") or p.get("title") or problem_id.replace("-", " ").title(),
                "difficulty": details.get("difficulty") or p.get("difficulty"),
                "source": p.get("source") or p.get("category", "path"),
                "reasoning": p.get("reasoning", "Selected for your practice"),
                "priority": p.get("priority") or p.get("order") or (i + 1),
                "skills": p.get("skills", [p.get("category")] if p.get("category") else []),
                "estimated_difficulty": p.get("estimated_difficulty") or p.get("difficulty"),
                "completed": False,
            })

        # Build mission data
        mission_data = {
            "user_id": user_id_str,
            "mission_date": mission_date.isoformat(),
            "daily_objective": gemini_response.get("daily_objective", "Focus on practice"),
            "objective_title": gemini_response.get("daily_objective", "Focus on practice"),
            "objective_description": gemini_response.get("balance_explanation", ""),
            "objective_skill_tags": [],
            "balance_explanation": gemini_response.get("balance_explanation"),
            "pacing_status": gemini_response.get("pacing_status"),
            "pacing_note": gemini_response.get("pacing_note"),
            "problems": problems,
            "main_quests": gemini_response.get("main_quests", []),
            "side_quests": gemini_response.get("side_quests", []),
            "completed_main_quests": [],
            "completed_side_quests": [],
            "regenerated_count": (existing.get("regenerated_count", 0) + 1) if existing else 0,
            "generated_at": datetime.utcnow().isoformat(),
            "gemini_response": gemini_response,
            "generation_context": {
                "target_company": context.get("target_company"),
                "days_until_deadline": context.get("days_until_deadline"),
            },
        }

        # Save to database
        await self._save_mission(user_id, mission_date, mission_data, existing is not None)

        return mission_data

    async def _get_existing_mission(self, user_id: UUID, mission_date: date) -> dict:
        """Get existing mission for the date if it exists."""
        response = (
            self.supabase.table("daily_missions")
            .select("*")
            .eq("user_id", str(user_id))
            .eq("mission_date", mission_date.isoformat())
            .execute()
        )

        if response.data:
            mission = response.data[0]

            # Also get mission_problems
            problems_response = (
                self.supabase.table("mission_problems")
                .select("*")
                .eq("mission_id", mission["id"])
                .order("priority")
                .execute()
            )

            if problems_response.data:
                mission["problems"] = problems_response.data

            return mission

        return None

    async def _save_mission(
        self,
        user_id: UUID,
        mission_date: date,
        mission_data: dict,
        is_update: bool,
    ) -> None:
        """Save or update the mission in the database."""
        user_id_str = str(user_id)

        # Prepare main mission data
        main_data = {
            "user_id": user_id_str,
            "mission_date": mission_date.isoformat(),
            "objective_title": mission_data.get("objective_title", mission_data.get("daily_objective", "")),
            "objective_description": mission_data.get("objective_description", ""),
            "objective_skill_tags": mission_data.get("objective_skill_tags", []),
            "daily_objective": mission_data.get("daily_objective"),
            "balance_explanation": mission_data.get("balance_explanation"),
            "pacing_status": mission_data.get("pacing_status"),
            "pacing_note": mission_data.get("pacing_note"),
            "main_quests": mission_data.get("main_quests", []),
            "side_quests": mission_data.get("side_quests", []),
            "completed_main_quests": mission_data.get("completed_main_quests", []),
            "completed_side_quests": mission_data.get("completed_side_quests", []),
            "regenerated_count": mission_data.get("regenerated_count", 0),
            "generated_at": mission_data.get("generated_at"),
            "gemini_response": mission_data.get("gemini_response"),
            "generation_context": mission_data.get("generation_context", {}),
            "updated_at": datetime.utcnow().isoformat(),
        }

        if is_update:
            # Get existing mission ID
            existing = (
                self.supabase.table("daily_missions")
                .select("id")
                .eq("user_id", user_id_str)
                .eq("mission_date", mission_date.isoformat())
                .single()
                .execute()
            )

            if existing.data:
                mission_id = existing.data["id"]

                # Update mission
                self.supabase.table("daily_missions").update(main_data).eq("id", mission_id).execute()

                # Delete old problems
                self.supabase.table("mission_problems").delete().eq("mission_id", mission_id).execute()

                # Insert new problems
                await self._save_mission_problems(mission_id, mission_data.get("problems", []))
        else:
            # Insert new mission
            result = self.supabase.table("daily_missions").insert(main_data).execute()

            if result.data:
                mission_id = result.data[0]["id"]
                await self._save_mission_problems(mission_id, mission_data.get("problems", []))

    async def _save_mission_problems(self, mission_id: str, problems: list) -> None:
        """Save mission problems to the junction table."""
        if not problems:
            return

        problem_records = []
        for p in problems:
            problem_records.append({
                "mission_id": mission_id,
                "problem_id": p.get("problem_id"),
                "problem_title": p.get("problem_title"),
                "difficulty": p.get("difficulty"),
                "source": p.get("source", "path"),
                "reasoning": p.get("reasoning", ""),
                "priority": p.get("priority", 0),
                "skills": p.get("skills", []),
                "estimated_difficulty": p.get("estimated_difficulty"),
                "completed": p.get("completed", False),
            })

        if problem_records:
            self.supabase.table("mission_problems").insert(problem_records).execute()

    async def _enrich_mission(self, mission_data: dict, user_id: UUID) -> dict:
        """
        Enrich mission data with computed fields for the response.
        """
        user_id_str = str(user_id) if isinstance(user_id, UUID) else mission_data.get("user_id")

        # Get streak
        streak = 0
        streak_response = (
            self.supabase.table("user_streaks")
            .select("current_streak, last_activity_date")
            .eq("user_id", user_id_str)
            .execute()
        )
        if streak_response.data:
            streak_data = streak_response.data[0]
            last_date = streak_data.get("last_activity_date")
            if last_date:
                try:
                    last_date_obj = parse_iso_datetime(last_date).date() if isinstance(last_date, str) else last_date
                    days_diff = (date.today() - last_date_obj).days
                    if days_diff <= 1:
                        streak = streak_data.get("current_streak", 0)
                except Exception:
                    pass

        # Get today's completed problems
        today = date.today().isoformat()
        completed_today_response = (
            self.supabase.table("submissions")
            .select("problem_slug")
            .eq("user_id", user_id_str)
            .eq("status", "Accepted")
            .gte("submitted_at", f"{today}T00:00:00")
            .execute()
        )
        completed_today_slugs = set()
        if completed_today_response.data:
            completed_today_slugs = {s["problem_slug"] for s in completed_today_response.data}

        # Update problem completion status
        problems = mission_data.get("problems", [])
        for p in problems:
            problem_id = p.get("problem_id")
            if problem_id in completed_today_slugs:
                p["completed"] = True

        completed_count = sum(1 for p in problems if p.get("completed"))

        return {
            "user_id": user_id_str,
            "mission_date": mission_data.get("mission_date", date.today().isoformat()),
            "daily_objective": mission_data.get("daily_objective") or mission_data.get("objective_title", "Focus on practice"),
            "problems": problems,
            "balance_explanation": mission_data.get("balance_explanation"),
            "pacing_status": mission_data.get("pacing_status"),
            "pacing_note": mission_data.get("pacing_note"),
            "streak": streak,
            "total_completed_today": len(completed_today_slugs),
            "completed_count": completed_count,
            "can_regenerate": mission_data.get("regenerated_count", 0) < 3,
            "generated_at": mission_data.get("generated_at", datetime.utcnow().isoformat()),
            # Legacy fields for backward compatibility
            "objective": {
                "title": mission_data.get("daily_objective") or mission_data.get("objective_title", ""),
                "description": mission_data.get("balance_explanation") or mission_data.get("objective_description", ""),
                "skill_tags": mission_data.get("objective_skill_tags", []),
                "target_count": len(problems),
                "completed_count": completed_count,
            },
            "main_quests": mission_data.get("main_quests", []),
            "side_quests": mission_data.get("side_quests", []),
        }

    async def generate_all_missions(self) -> dict:
        """
        Generate missions for all active users.

        Called by cron job for batch generation.
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
            return {"generated": 0, "skipped": 0, "failed": 0, "total_users": 0}

        # Deduplicate user IDs
        user_ids = list(set(row["user_id"] for row in users_response.data))

        generated = 0
        skipped = 0
        failed = 0

        for user_id in user_ids:
            try:
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
