"""Mastery endpoints - DSA domain readiness assessment."""

from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from supabase import Client

from app.db.supabase import get_supabase
from app.models.schemas import (
    DomainDetailResponse,
    DomainScore,
    MasteryResponse,
    PathProblem,
    Submission,
)

router = APIRouter()

# Google DSA Domain mappings
# Maps LeetCode tags to our 16 Google-readiness domains
DOMAIN_MAPPINGS = {
    "Arrays & Hashing": ["Array", "Hash Table", "String", "Sorting"],
    "Two Pointers": ["Two Pointers"],
    "Sliding Window": ["Sliding Window"],
    "Stack": ["Stack", "Monotonic Stack"],
    "Binary Search": ["Binary Search"],
    "Linked List": ["Linked List"],
    "Trees": ["Tree", "Binary Tree", "Binary Search Tree", "Depth-First Search", "Breadth-First Search"],
    "Tries": ["Trie"],
    "Heap / Priority Queue": ["Heap (Priority Queue)", "Heap"],
    "Backtracking": ["Backtracking", "Recursion"],
    "Graphs": ["Graph", "Union Find", "Topological Sort"],
    "Dynamic Programming": ["Dynamic Programming", "Memoization"],
    "Greedy": ["Greedy"],
    "Intervals": ["Interval", "Line Sweep"],
    "Math & Geometry": ["Math", "Geometry", "Matrix", "Simulation"],
    "Bit Manipulation": ["Bit Manipulation"],
}

# All domains (used to ensure we show all 16 even if unpracticed)
ALL_DOMAINS = list(DOMAIN_MAPPINGS.keys())


def get_status(score: float) -> str:
    """Convert score to status label."""
    if score >= 80:
        return "STRONG"
    elif score >= 60:
        return "GOOD"
    elif score >= 40:
        return "FAIR"
    else:
        return "WEAK"


def map_tag_to_domain(tag: str) -> str | None:
    """Map a LeetCode tag to our domain."""
    for domain, tags in DOMAIN_MAPPINGS.items():
        if tag in tags:
            return domain
    return None


@router.get("/mastery/{user_id}", response_model=MasteryResponse)
async def get_mastery(
    user_id: UUID,
    supabase: Annotated[Client, Depends(get_supabase)] = None,
):
    """
    Get comprehensive mastery data across all 16 DSA domains.

    Returns readiness score and domain breakdown for Google-level preparation.
    """
    try:
        # Get all skill scores for user
        skills_response = (
            supabase.table("skill_scores")
            .select("tag, score, total_attempts, success_rate")
            .eq("user_id", str(user_id))
            .execute()
        )

        # Map skills to domains
        domain_scores = {domain: {"scores": [], "attempts": 0, "solved": 0} for domain in ALL_DOMAINS}

        if skills_response.data:
            for skill in skills_response.data:
                tag = skill["tag"]
                domain = map_tag_to_domain(tag)
                if domain:
                    domain_scores[domain]["scores"].append(skill["score"])
                    domain_scores[domain]["attempts"] += skill.get("total_attempts", 0)
                    # Estimate solved from success rate * attempts
                    solved = int(skill.get("success_rate", 0) * skill.get("total_attempts", 0))
                    domain_scores[domain]["solved"] += solved

        # Calculate domain averages
        domains = []
        total_score = 0
        practiced_domains = 0

        for domain_name in ALL_DOMAINS:
            data = domain_scores[domain_name]
            if data["scores"]:
                avg_score = sum(data["scores"]) / len(data["scores"])
                practiced_domains += 1
            else:
                avg_score = 0.0

            total_score += avg_score

            domains.append(
                DomainScore(
                    name=domain_name,
                    score=round(avg_score, 1),
                    status=get_status(avg_score),
                    problems_attempted=data["attempts"],
                    problems_solved=data["solved"],
                    sub_patterns=[],  # Can be enhanced with sub-pattern breakdown
                )
            )

        # Sort domains by score (show weakest first for focus)
        domains.sort(key=lambda d: d.score)

        # Calculate overall readiness
        # Weight practiced domains more than unpracticed
        if practiced_domains > 0:
            readiness_score = total_score / len(ALL_DOMAINS)
        else:
            readiness_score = 0.0

        # Identify weak and strong areas
        weak_areas = [d.name for d in domains if d.status == "WEAK" and d.problems_attempted > 0]
        strong_areas = [d.name for d in domains if d.status == "STRONG"]

        # Generate readiness summary
        if readiness_score >= 75:
            summary = "Strong foundation across most domains. Focus on maintaining consistency."
        elif readiness_score >= 50:
            summary = f"Solid progress. Focus on {', '.join(weak_areas[:2])} to reach interview readiness."
        elif readiness_score >= 25:
            summary = f"Building fundamentals. Prioritize {', '.join(weak_areas[:2])} and practice consistently."
        else:
            summary = "Start with Arrays & Hashing and Two Pointers to build your foundation."

        return MasteryResponse(
            user_id=user_id,
            readiness_score=round(readiness_score, 1),
            readiness_summary=summary,
            domains=domains,
            weak_areas=weak_areas,
            strong_areas=strong_areas,
            generated_at=datetime.utcnow(),
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get mastery data: {str(e)}")


@router.get("/mastery/{user_id}/{domain_name}", response_model=DomainDetailResponse)
async def get_domain_detail(
    user_id: UUID,
    domain_name: str,
    supabase: Annotated[Client, Depends(get_supabase)] = None,
):
    """
    Get detailed breakdown of a specific domain.

    Includes sub-patterns, failure analysis, and recommended path.
    """
    try:
        # Validate domain
        if domain_name not in DOMAIN_MAPPINGS:
            raise HTTPException(status_code=404, detail=f"Domain '{domain_name}' not found")

        relevant_tags = DOMAIN_MAPPINGS[domain_name]

        # Get skill scores for relevant tags
        sub_patterns = []
        total_score = 0
        total_attempts = 0
        total_solved = 0

        for tag in relevant_tags:
            skill_response = (
                supabase.table("skill_scores")
                .select("score, total_attempts, success_rate")
                .eq("user_id", str(user_id))
                .eq("tag", tag)
                .execute()
            )

            if skill_response.data:
                skill = skill_response.data[0]
                score = skill["score"]
                attempts = skill.get("total_attempts", 0)
                solved = int(skill.get("success_rate", 0) * attempts)

                sub_patterns.append({
                    "name": tag,
                    "score": round(score, 1),
                    "attempted": attempts,
                    "solved": solved,
                })

                total_score += score
                total_attempts += attempts
                total_solved += solved
            else:
                sub_patterns.append({
                    "name": tag,
                    "score": 0.0,
                    "attempted": 0,
                    "solved": 0,
                })

        # Calculate domain score
        if sub_patterns:
            practiced = [s for s in sub_patterns if s["attempted"] > 0]
            if practiced:
                avg_score = sum(s["score"] for s in practiced) / len(practiced)
            else:
                avg_score = 0.0
        else:
            avg_score = 0.0

        domain = DomainScore(
            name=domain_name,
            score=round(avg_score, 1),
            status=get_status(avg_score),
            problems_attempted=total_attempts,
            problems_solved=total_solved,
            sub_patterns=sub_patterns,
        )

        # Get recent submissions for this domain
        recent_submissions = []
        for tag in relevant_tags[:3]:  # Limit to avoid too many queries
            subs_response = (
                supabase.table("submissions")
                .select("*")
                .eq("user_id", str(user_id))
                .contains("tags", [tag])
                .order("submitted_at", desc=True)
                .limit(3)
                .execute()
            )
            if subs_response.data:
                for s in subs_response.data:
                    if not any(r.id == s["id"] for r in recent_submissions):
                        recent_submissions.append(Submission(**s))

        recent_submissions = recent_submissions[:5]  # Limit total

        # Generate failure analysis
        failure_analysis = await _analyze_failures(supabase, user_id, relevant_tags)

        # Get recommended path (easier problems in this domain)
        recommended_path = await _get_domain_path(supabase, domain_name)

        return DomainDetailResponse(
            domain=domain,
            failure_analysis=failure_analysis,
            recommended_path=recommended_path,
            recent_submissions=recent_submissions,
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get domain detail: {str(e)}")


async def _analyze_failures(
    supabase: Client,
    user_id: UUID,
    tags: list[str],
) -> str:
    """Analyze failure patterns for given tags."""
    try:
        # Get recent failures
        failures = []
        for tag in tags[:3]:
            response = (
                supabase.table("submissions")
                .select("status, difficulty")
                .eq("user_id", str(user_id))
                .neq("status", "Accepted")
                .contains("tags", [tag])
                .order("submitted_at", desc=True)
                .limit(5)
                .execute()
            )
            if response.data:
                failures.extend(response.data)

        if not failures:
            return "No failure data yet. Keep practicing to get personalized analysis."

        # Analyze failure types
        status_counts = {}
        difficulty_counts = {}
        for f in failures:
            status = f.get("status", "Unknown")
            diff = f.get("difficulty", "Unknown")
            status_counts[status] = status_counts.get(status, 0) + 1
            difficulty_counts[diff] = difficulty_counts.get(diff, 0) + 1

        # Generate analysis
        most_common_error = max(status_counts, key=status_counts.get)
        most_failed_diff = max(difficulty_counts, key=difficulty_counts.get)

        if most_common_error == "Time Limit Exceeded":
            return f"Most failures are TLE on {most_failed_diff} problems. Focus on optimizing time complexity and recognizing when O(n^2) won't work."
        elif most_common_error == "Wrong Answer":
            return f"Most failures are Wrong Answer on {most_failed_diff} problems. Review edge cases and trace through your logic carefully."
        elif most_common_error == "Runtime Error":
            return f"Frequent runtime errors suggest issues with null checks or array bounds. Add defensive programming habits."
        else:
            return f"Common failure: {most_common_error}. Practice more {most_failed_diff} problems to build confidence."

    except Exception:
        return "Unable to analyze failures at this time."


async def _get_domain_path(
    supabase: Client,
    domain_name: str,
    limit: int = 5,
) -> list[PathProblem]:
    """Get recommended problems for a domain from NeetCode 150."""
    try:
        # Get NeetCode 150 path
        path_response = (
            supabase.table("learning_paths")
            .select("categories")
            .eq("id", "11111111-1111-1111-1111-111111111150")
            .single()
            .execute()
        )

        if not path_response.data:
            return []

        categories = path_response.data.get("categories", [])

        # Find matching category
        for cat in categories:
            if cat["name"] == domain_name or domain_name.lower() in cat["name"].lower():
                problems = cat.get("problems", [])[:limit]
                return [
                    PathProblem(
                        slug=p["slug"],
                        title=p["title"],
                        difficulty=p["difficulty"],
                        order=p["order"],
                    )
                    for p in problems
                ]

        return []
    except Exception:
        return []
