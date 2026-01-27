#!/usr/bin/env python3
"""
Test script for LLM-driven side quest recommendations.

Usage:
    python scripts/test_side_quest_recommendations.py <user_id>
    python scripts/test_side_quest_recommendations.py <user_id> --verbose
    python scripts/test_side_quest_recommendations.py <user_id> --dry-run

Features:
- Connects to real Supabase
- Shows all gathered context
- Prints full prompt (in verbose mode)
- Shows LLM response and parsed side quests
"""

import argparse
import asyncio
import json
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path
from uuid import UUID

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
from supabase import create_client

# Load environment variables
load_dotenv(Path(__file__).parent.parent / ".env")


def create_supabase_client():
    """Create Supabase client from environment variables."""
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_ANON_KEY") or os.getenv("SUPABASE_KEY")

    if not url or not key:
        print("Error: SUPABASE_URL and SUPABASE_ANON_KEY must be set")
        sys.exit(1)

    return create_client(url, key)


def gather_context(supabase, user_id: str) -> dict:
    """Gather all context for side quest generation (mirrors _gather_context)."""
    context = {
        "recent_failures": [],
        "recent_failures_with_code": [],
        "slow_solves": [],
        "weak_skills": [],
        "struggles": [],
        "path_progress": {},
        "solved_problems": [],
    }

    seven_days_ago = (datetime.utcnow() - timedelta(days=7)).isoformat()

    # Get ALL recent failures WITH code
    print("\n--- Fetching recent failures with code ---")
    failures_response = (
        supabase.table("submissions")
        .select("problem_slug, problem_title, difficulty, tags, status, code, language, submitted_at")
        .eq("user_id", user_id)
        .neq("status", "Accepted")
        .gte("submitted_at", seven_days_ago)
        .order("submitted_at", desc=True)
        .execute()
    )
    if failures_response.data:
        context["recent_failures"] = failures_response.data
        context["recent_failures_with_code"] = [
            f for f in failures_response.data if f.get("code")
        ]
        print(f"Found {len(failures_response.data)} failures, {len(context['recent_failures_with_code'])} with code")

    # Get slow solves
    print("\n--- Fetching slow solves ---")
    slow_response = (
        supabase.table("problem_attempt_stats")
        .select("problem_slug, problem_title, difficulty, total_attempts, time_to_first_success_seconds")
        .eq("user_id", user_id)
        .eq("is_slow_solve", True)
        .order("last_attempt_at", desc=True)
        .limit(10)
        .execute()
    )
    if slow_response.data:
        context["slow_solves"] = slow_response.data
        print(f"Found {len(slow_response.data)} slow solves")

    # Get struggles
    print("\n--- Fetching struggles ---")
    struggle_response = (
        supabase.table("problem_attempt_stats")
        .select("problem_slug, problem_title, difficulty, failed_attempts")
        .eq("user_id", user_id)
        .eq("is_struggle", True)
        .order("last_attempt_at", desc=True)
        .limit(5)
        .execute()
    )
    if struggle_response.data:
        context["struggles"] = struggle_response.data
        print(f"Found {len(struggle_response.data)} struggles")

    # Get weak skills
    print("\n--- Fetching weak skills ---")
    skills_response = (
        supabase.table("skill_scores")
        .select("tag, score, total_attempts")
        .eq("user_id", user_id)
        .lt("score", 60)
        .order("score")
        .limit(5)
        .execute()
    )
    if skills_response.data:
        context["weak_skills"] = skills_response.data
        print(f"Found {len(skills_response.data)} weak skills")

    # Get path progress
    print("\n--- Fetching path progress ---")
    settings_response = (
        supabase.table("user_settings")
        .select("current_path_id")
        .eq("user_id", user_id)
        .execute()
    )
    current_path_id = "11111111-1111-1111-1111-111111111150"  # Default NeetCode 150
    if settings_response.data and settings_response.data[0].get("current_path_id"):
        current_path_id = settings_response.data[0]["current_path_id"]
    context["current_path_id"] = current_path_id

    progress_response = (
        supabase.table("user_path_progress")
        .select("completed_problems, current_category")
        .eq("user_id", user_id)
        .eq("path_id", current_path_id)
        .execute()
    )
    if progress_response.data:
        context["path_progress"] = progress_response.data[0]
        context["solved_problems"] = list(set(progress_response.data[0].get("completed_problems", []) or []))
        print(f"Current category: {context['path_progress'].get('current_category')}")
        print(f"Solved: {len(context['solved_problems'])} problems")

    # Also add accepted submissions to solved problems
    accepted_response = (
        supabase.table("submissions")
        .select("problem_slug")
        .eq("user_id", user_id)
        .eq("status", "Accepted")
        .execute()
    )
    if accepted_response.data:
        for s in accepted_response.data:
            if s["problem_slug"] not in context["solved_problems"]:
                context["solved_problems"].append(s["problem_slug"])

    return context


def get_candidate_quests(supabase, user_id: str, context: dict) -> list[dict]:
    """Gather candidate side quests (mirrors candidate gathering in _generate_side_quests)."""
    candidates = []
    solved = set(context.get("solved_problems", []))

    # Reviews due
    print("\n--- Fetching review queue ---")
    reviews_response = (
        supabase.table("review_queue")
        .select("problem_slug, problem_title, reason")
        .eq("user_id", user_id)
        .lte("next_review", datetime.utcnow().isoformat())
        .order("priority", desc=True)
        .limit(3)
        .execute()
    )
    if reviews_response.data:
        for r in reviews_response.data:
            candidates.append({
                "slug": r["problem_slug"],
                "title": r.get("problem_title") or r["problem_slug"].replace("-", " ").title(),
                "difficulty": None,
                "reason": r.get("reason", "Due for review"),
                "quest_type": "review_due",
            })
        print(f"Found {len(reviews_response.data)} reviews due")

    # Skill gap problems
    if context.get("weak_skills"):
        print("\n--- Finding skill gap problems ---")
        for skill in context["weak_skills"]:
            failed_response = (
                supabase.table("submissions")
                .select("problem_slug, problem_title, difficulty")
                .eq("user_id", user_id)
                .neq("status", "Accepted")
                .contains("tags", [skill["tag"]])
                .order("submitted_at", desc=True)
                .limit(2)
                .execute()
            )
            if failed_response.data:
                for prob in failed_response.data:
                    if prob["problem_slug"] not in solved and not any(
                        c["slug"] == prob["problem_slug"] for c in candidates
                    ):
                        candidates.append({
                            "slug": prob["problem_slug"],
                            "title": prob.get("problem_title") or prob["problem_slug"].replace("-", " ").title(),
                            "difficulty": prob.get("difficulty"),
                            "reason": f"Strengthen {skill['tag']} (score: {skill['score']:.0f}%)",
                            "quest_type": "skill_gap",
                        })

    # Slow solves
    if context.get("slow_solves"):
        for slow in context["slow_solves"]:
            if not any(c["slug"] == slow["problem_slug"] for c in candidates):
                candidates.append({
                    "slug": slow["problem_slug"],
                    "title": slow.get("problem_title") or slow["problem_slug"].replace("-", " ").title(),
                    "difficulty": slow.get("difficulty"),
                    "reason": f"Took {slow['total_attempts']} attempts",
                    "quest_type": "slow_solve",
                })

    return candidates


def get_path_info(supabase, context: dict) -> dict:
    """Get path info for prompt building."""
    path_id = context.get("current_path_id", "11111111-1111-1111-1111-111111111150")
    solved = set(context.get("solved_problems", []))
    current_category = context.get("path_progress", {}).get("current_category")

    path_response = (
        supabase.table("learning_paths")
        .select("categories, name")
        .eq("id", path_id)
        .single()
        .execute()
    )

    if not path_response.data:
        return {"total_problems": 150, "upcoming_in_category": []}

    categories = path_response.data.get("categories", [])
    total_problems = sum(len(cat.get("problems", [])) for cat in categories)

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


def build_side_quest_prompt(context: dict, candidates: list[dict], path_info: dict) -> str:
    """Build the rich prompt for LLM side quest selection."""
    prompt_parts = []

    current_category = context.get("path_progress", {}).get("current_category", "Unknown")
    solved_count = len(context.get("solved_problems", []))
    total_problems = path_info.get("total_problems", 150)
    upcoming = path_info.get("upcoming_in_category", [])

    prompt_parts.append(f"""## Your Position in NeetCode 150 (Main Plot)
Current Category: {current_category}
Problems Completed: {solved_count}/{total_problems}
Next up in path: {', '.join(upcoming[:3]) if upcoming else 'None'}

This learner is working through "{current_category}" - side quests should complement this focus.""")

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

    solved = context.get("solved_problems", [])
    solved_display = ", ".join(solved[:50])
    if len(solved) > 50:
        solved_display += f", ... ({len(solved)} total)"
    prompt_parts.append(f"\n## Solved Problems ({len(solved)} total)\n{solved_display}\n")

    prompt_parts.append("\n## Candidate Problems for Side Quests")
    for cq in candidates:
        prompt_parts.append(f"- {cq['slug']}: {cq['title']} ({cq.get('difficulty', 'Unknown')}) - Source: {cq['quest_type']}")

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


def call_gemini(prompt: str, dry_run: bool = False) -> dict:
    """Call Gemini API with the prompt."""
    if dry_run:
        print("\n[DRY RUN] Would send prompt to Gemini")
        return {"analysis": "Dry run - no API call made", "side_quests": []}

    try:
        import google.generativeai as genai

        api_key = os.getenv("GOOGLE_API_KEY")
        if not api_key:
            print("Error: GOOGLE_API_KEY not set")
            return {"error": "No API key"}

        genai.configure(api_key=api_key)
        model_name = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")
        model = genai.GenerativeModel(model_name)

        print(f"\n--- Calling Gemini ({model_name}) ---")
        response = model.generate_content(prompt)
        text = response.text.strip()

        # Extract JSON
        if "```json" in text:
            text = text.split("```json")[1].split("```")[0]
        elif "```" in text:
            text = text.split("```")[1].split("```")[0]

        return json.loads(text)

    except ImportError:
        print("Error: google-generativeai not installed. Run: pip install google-generativeai")
        return {"error": "Module not installed"}
    except json.JSONDecodeError as e:
        print(f"Error parsing JSON response: {e}")
        print(f"Raw response:\n{text}")
        return {"error": "JSON parse error", "raw": text}
    except Exception as e:
        print(f"Error calling Gemini: {e}")
        return {"error": str(e)}


def print_context_summary(context: dict) -> None:
    """Print a summary of gathered context."""
    print("\n" + "=" * 60)
    print("CONTEXT SUMMARY")
    print("=" * 60)

    print(f"\nPath: {context.get('current_path_id', 'unknown')}")
    print(f"Current Category: {context.get('path_progress', {}).get('current_category', 'unknown')}")
    print(f"Solved Problems: {len(context.get('solved_problems', []))}")

    print(f"\nRecent Failures: {len(context.get('recent_failures', []))}")
    print(f"  - With Code: {len(context.get('recent_failures_with_code', []))}")

    if context.get("recent_failures_with_code"):
        print("\n  Failures with code:")
        for f in context["recent_failures_with_code"][:5]:
            title = f.get("problem_title") or f.get("problem_slug")
            status = f.get("status")
            print(f"    - {title}: {status}")
        if len(context["recent_failures_with_code"]) > 5:
            print(f"    ... and {len(context['recent_failures_with_code']) - 5} more")

    if context.get("weak_skills"):
        print(f"\nWeak Skills ({len(context['weak_skills'])}):")
        for skill in context["weak_skills"]:
            print(f"  - {skill['tag']}: {skill['score']:.1f}%")

    if context.get("slow_solves"):
        print(f"\nSlow Solves ({len(context['slow_solves'])}):")
        for slow in context["slow_solves"][:3]:
            print(f"  - {slow.get('problem_title', slow['problem_slug'])}: {slow['total_attempts']} attempts")


def main():
    parser = argparse.ArgumentParser(description="Test LLM-driven side quest recommendations")
    parser.add_argument("user_id", help="User ID to test with")
    parser.add_argument("--verbose", "-v", action="store_true", help="Show full prompt")
    parser.add_argument("--dry-run", "-n", action="store_true", help="Don't call Gemini, just show prompt")
    args = parser.parse_args()

    # Validate user_id
    try:
        user_uuid = UUID(args.user_id)
    except ValueError:
        print(f"Error: Invalid UUID format: {args.user_id}")
        sys.exit(1)

    print(f"Testing side quest recommendations for user: {args.user_id}")

    # Create Supabase client
    supabase = create_supabase_client()

    # Gather context
    print("\n" + "=" * 60)
    print("GATHERING CONTEXT")
    print("=" * 60)
    context = gather_context(supabase, args.user_id)
    print_context_summary(context)

    # Get candidates
    print("\n" + "=" * 60)
    print("GATHERING CANDIDATES")
    print("=" * 60)
    candidates = get_candidate_quests(supabase, args.user_id, context)
    print(f"\nTotal candidates: {len(candidates)}")
    for c in candidates:
        print(f"  - [{c['quest_type']}] {c['title']}")

    if not candidates:
        print("\nNo candidates found. Cannot generate side quests.")
        sys.exit(0)

    # Get path info
    path_info = get_path_info(supabase, context)
    print(f"\nPath: {path_info.get('path_name')}")
    print(f"Total problems: {path_info.get('total_problems')}")
    print(f"Upcoming: {', '.join(path_info.get('upcoming_in_category', [])[:3])}")

    # Build prompt
    prompt = build_side_quest_prompt(context, candidates, path_info)

    if args.verbose or args.dry_run:
        print("\n" + "=" * 60)
        print("FULL PROMPT")
        print("=" * 60)
        print(prompt)

    print(f"\nPrompt length: {len(prompt)} characters")

    # Call Gemini
    if not context.get("recent_failures_with_code"):
        print("\nNo failures with code - LLM selection would be skipped (falling back to rule-based)")
        print("\nRule-based selection:")
        for i, c in enumerate(candidates[:3], 1):
            print(f"  {i}. {c['title']} - {c['reason']}")
        sys.exit(0)

    result = call_gemini(prompt, dry_run=args.dry_run)

    print("\n" + "=" * 60)
    print("LLM RESPONSE")
    print("=" * 60)
    print(json.dumps(result, indent=2))

    if "side_quests" in result:
        print("\n" + "=" * 60)
        print("SELECTED SIDE QUESTS")
        print("=" * 60)
        print(f"\nAnalysis: {result.get('analysis', 'N/A')}\n")
        for i, sq in enumerate(result["side_quests"], 1):
            print(f"{i}. {sq.get('title', sq.get('slug'))}")
            print(f"   Reason: {sq.get('reason')}")
            print(f"   Target: {sq.get('target_weakness')}")
            print()


if __name__ == "__main__":
    main()
