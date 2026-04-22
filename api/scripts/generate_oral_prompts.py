#!/usr/bin/env python3
"""
Generate oral monologue prompts from book_content for each chapter of a language track.

Creates 10-15 prompts per chapter stored in language_oral_prompts.
Uses Gemini to generate varied monologue prompts from grammar rules, vocab, and themes.

Usage:
    cd api
    python scripts/generate_oral_prompts.py --track-id 5eba8cda-1cbf-4d07-b770-1204a7b54a75
    python scripts/generate_oral_prompts.py --track-id <uuid> --dry-run
    python scripts/generate_oral_prompts.py --track-id <uuid> --chapters 1,5,12
"""

import argparse
import json
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")

import google.generativeai as genai
from supabase import create_client


def create_supabase_client():
    url = os.getenv("SUPABASE_URL")
    key = (
        os.getenv("SUPABASE_SERVICE_ROLE_KEY")
        or os.getenv("SUPABASE_KEY")
        or os.getenv("SUPABASE_ANON_KEY")
    )
    if not url or not key:
        print("Error: SUPABASE_URL and SUPABASE_KEY must be set")
        sys.exit(1)
    return create_client(url, key)


def configure_gemini():
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        print("Error: GOOGLE_API_KEY must be set")
        sys.exit(1)
    genai.configure(api_key=api_key)
    return genai.GenerativeModel("gemini-2.0-flash")


def fetch_track_and_content(sb, track_id: str):
    """Fetch track topics and book_content for each chapter."""
    track_resp = sb.table("language_tracks").select("*").eq("id", track_id).execute()
    if not track_resp.data:
        print(f"Error: Track {track_id} not found")
        sys.exit(1)
    track = track_resp.data[0]

    book_resp = (
        sb.table("book_content")
        .select("*")
        .eq("language_track_id", track_id)
        .order("chapter_number")
        .execute()
    )

    # Index book_content by chapter_title
    book_by_chapter = {}
    for row in book_resp.data:
        book_by_chapter[row["chapter_title"]] = row

    return track, book_by_chapter


def build_generation_prompt(topic: dict, book_content: dict | None, language: str, level: str) -> str:
    """Build the Gemini prompt for generating oral monologue prompts."""
    chapter_name = topic["name"]
    key_concepts = topic.get("key_concepts", [])
    difficulty = topic.get("difficulty", "medium")

    book_context = ""
    if book_content:
        summary = book_content.get("summary", "")
        sections = book_content.get("sections", [])
        bc_concepts = book_content.get("key_concepts", [])

        section_text = ""
        if sections:
            for s in sections[:5]:  # limit to first 5 sections
                title = s.get("title", "")
                sec_summary = s.get("summary", "")
                points = s.get("key_points", [])
                section_text += f"\n  - {title}: {sec_summary}"
                if points:
                    section_text += " | Points: " + "; ".join(points[:3])

        book_context = f"""
TEXTBOOK REFERENCE:
Chapter: {chapter_name}
Summary: {summary}
Key Grammar/Vocab: {', '.join(bc_concepts[:15])}
Sections: {section_text}
"""

    return f"""You are an expert French language teacher designing oral practice prompts for a {level.upper()} student targeting CEFR C1.

CHAPTER: {chapter_name}
DIFFICULTY: {difficulty}
KEY CONCEPTS: {', '.join(key_concepts[:10])}
{book_context}

Generate exactly 12 monologue prompts for this chapter. Each prompt should:
1. Require the student to speak for 1-3 minutes in French
2. Naturally exercise the grammar concepts from this chapter (without being a grammar drill)
3. Require argumentation, description, explanation, narrative, or opinion
4. Vary in register: some formal (essay-style), some conversational, some professional
5. Be entirely in French
6. Push the student toward C1-level discourse: nuance, concession, reformulation, abstract reasoning

For each prompt, specify:
- prompt_text: The full monologue prompt in French (2-4 sentences setting up the task)
- theme: A short 2-4 word theme label in French
- grammar_targets: 2-3 specific grammar points from this chapter the prompt exercises
- vocab_targets: 3-5 vocabulary items or expressions the student should try to use
- suggested_duration_seconds: 60, 90, 120, or 180 depending on complexity

Format as JSON array:
[
  {{
    "prompt_text": "Décrivez une situation où...",
    "theme": "Vie quotidienne",
    "grammar_targets": ["subjonctif après expressions de doute", "concordance des temps"],
    "vocab_targets": ["en revanche", "à condition que", "une prise de conscience"],
    "suggested_duration_seconds": 120
  }},
  ...
]

Generate 12 prompts now. Return ONLY the JSON array, no other text."""


def parse_prompts(response_text: str) -> list[dict]:
    """Extract JSON array from Gemini response."""
    import re

    # Try to find JSON array in response
    match = re.search(r"\[[\s\S]*\]", response_text)
    if not match:
        raise ValueError("No JSON array found in response")

    text = match.group(0)
    # Fix common Gemini JSON issues
    text = re.sub(r"\\(?![\"\\nrtbfu/])", r"\\\\", text)

    return json.loads(text)


def generate_prompts_for_chapter(
    model, topic: dict, book_content: dict | None, language: str, level: str
) -> list[dict]:
    """Generate oral prompts for a single chapter."""
    prompt = build_generation_prompt(topic, book_content, language, level)
    response = model.generate_content(prompt)
    return parse_prompts(response.text)


def main():
    parser = argparse.ArgumentParser(description="Generate oral prompts for a language track")
    parser.add_argument("--track-id", required=True, help="Language track UUID")
    parser.add_argument("--dry-run", action="store_true", help="Print prompts without inserting")
    parser.add_argument("--chapters", help="Comma-separated chapter orders to generate (e.g. 1,5,12)")
    args = parser.parse_args()

    sb = create_supabase_client()
    model = configure_gemini()
    track, book_by_chapter = fetch_track_and_content(sb, args.track_id)

    topics = track["topics"]
    language = track["language"]
    level = track["level"]
    track_id = track["id"]

    # Filter chapters if specified
    if args.chapters:
        target_orders = set(int(x.strip()) for x in args.chapters.split(","))
        topics = [t for t in topics if t["order"] in target_orders]

    print(f"Track: {track['name']} ({language} {level})")
    print(f"Chapters to process: {len(topics)}")
    print()

    total_generated = 0
    total_inserted = 0

    for topic in topics:
        chapter_name = topic["name"]
        chapter_order = topic["order"]

        # Check if prompts already exist for this chapter
        existing = (
            sb.table("language_oral_prompts")
            .select("id", count="exact")
            .eq("track_id", track_id)
            .eq("chapter_ref", chapter_name)
            .execute()
        )
        if existing.count and existing.count > 0:
            print(f"  Chapter {chapter_order}: {chapter_name} — {existing.count} prompts already exist, skipping")
            continue

        print(f"  Chapter {chapter_order}: {chapter_name} — generating...", end=" ", flush=True)

        book_content = book_by_chapter.get(chapter_name)

        try:
            prompts = generate_prompts_for_chapter(model, topic, book_content, language, level)
            print(f"got {len(prompts)} prompts")
            total_generated += len(prompts)

            if args.dry_run:
                for i, p in enumerate(prompts):
                    print(f"    [{i+1}] {p.get('theme', '?')}: {p['prompt_text'][:80]}...")
            else:
                rows = []
                for i, p in enumerate(prompts):
                    rows.append(
                        {
                            "track_id": track_id,
                            "chapter_ref": chapter_name,
                            "chapter_order": chapter_order,
                            "prompt_text": p["prompt_text"],
                            "theme": p.get("theme", ""),
                            "grammar_targets": p.get("grammar_targets", []),
                            "vocab_targets": p.get("vocab_targets", []),
                            "suggested_duration_seconds": p.get("suggested_duration_seconds", 120),
                            "sort_order": i,
                        }
                    )

                result = sb.table("language_oral_prompts").insert(rows).execute()
                inserted = len(result.data) if result.data else 0
                total_inserted += inserted
                print(f"    Inserted {inserted} rows")

            # Rate limit: avoid hitting Gemini too fast
            time.sleep(2)

        except Exception as e:
            print(f"ERROR: {e}")
            continue

    print()
    print(f"Done. Generated: {total_generated}, Inserted: {total_inserted}")


if __name__ == "__main__":
    main()
