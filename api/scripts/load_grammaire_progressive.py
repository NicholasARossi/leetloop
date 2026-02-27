#!/usr/bin/env python3
"""
Load pre-ingested Grammaire Progressive du Français JSON files into the LeetLoop database.

Reads the 37 structured JSON files from api/data/grammaire_progressive/ and creates:
1. A language_track record with 27 topics (one per numbered chapter)
2. 27 book_content rows (one per numbered chapter) linked to the track

Usage:
    cd api
    python scripts/load_grammaire_progressive.py
    python scripts/load_grammaire_progressive.py --dry-run
"""

import json
import os
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
from supabase import create_client

load_dotenv(Path(__file__).parent.parent / ".env")

DATA_DIR = Path(__file__).parent.parent / "data" / "grammaire_progressive"
TRACK_NAME = "Grammaire Progressive B2"
LANGUAGE = "french"
LEVEL = "b2"


def create_supabase_client():
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_KEY") or os.getenv("SUPABASE_ANON_KEY")
    if not url or not key:
        print("Error: SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY must be set")
        sys.exit(1)
    return create_client(url, key)


def load_manifest():
    manifest_path = DATA_DIR / "manifest.json"
    if not manifest_path.exists():
        print(f"Error: manifest.json not found at {manifest_path}")
        sys.exit(1)
    return json.load(open(manifest_path))


def build_chapter_summary(chapter_data: dict) -> str:
    """Generate a text summary from grammar rules and exercises for Gemini context."""
    parts = []
    title = chapter_data.get("chapter_title", "")
    parts.append(f"Chapitre: {title}")

    for section in chapter_data.get("sections", []):
        section_title = section.get("section_title", "")
        subtitle = section.get("subtitle", "")
        if section_title:
            label = f"{section_title} ({subtitle})" if subtitle else section_title
            parts.append(f"\n{label}")

        # Summarize grammar rules
        for rule in section.get("grammar_rules", []):
            rule_text = rule.get("rule", "")
            if rule_text:
                parts.append(f"- {rule_text}")
            examples = rule.get("examples", [])
            if examples:
                parts.append(f"  Ex: {examples[0]}")

        # Intro examples
        intro = section.get("intro_examples", [])
        if intro and not section.get("grammar_rules"):
            parts.append(f"  Exemples: {'; '.join(intro[:3])}")

    return "\n".join(parts)[:2000]  # Truncate for DB storage


def extract_key_concepts(chapter_data: dict) -> list[str]:
    """Extract key grammar concepts from a chapter's rules."""
    concepts = set()
    for section in chapter_data.get("sections", []):
        section_title = section.get("section_title", "")
        if section_title:
            concepts.add(section_title)

        for rule in section.get("grammar_rules", []):
            # Extract from categories
            for cat in rule.get("categories", []):
                name = cat.get("name") or cat.get("label", "")
                if name:
                    concepts.add(name)

    return sorted(concepts)[:15]


def build_sections_for_db(chapter_data: dict) -> list[dict]:
    """Convert chapter sections to the format expected by book_content.sections JSONB."""
    db_sections = []
    for section in chapter_data.get("sections", []):
        rules_summary = []
        for rule in section.get("grammar_rules", []):
            rules_summary.append(rule.get("rule", ""))

        exercise_count = len(section.get("exercises", []))

        db_sections.append({
            "title": section.get("section_title", ""),
            "subtitle": section.get("subtitle"),
            "summary": "; ".join(rules_summary[:5]),
            "key_points": rules_summary[:10],
            "exercise_count": exercise_count,
        })
    return db_sections


def difficulty_for_chapter(chapter_num: int) -> str:
    """Assign difficulty based on chapter position in the book."""
    if chapter_num <= 3:
        return "easy"
    elif chapter_num <= 13:
        return "medium"
    else:
        return "hard"


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Load Grammaire Progressive into LeetLoop database")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be done")
    args = parser.parse_args()

    manifest = load_manifest()
    timestamp = datetime.now().strftime("%H:%M:%S")

    # Collect numbered chapters only (skip bilans, annexes, index)
    numbered_chapters = []
    for entry in manifest["chapters"]:
        if entry.get("number") is None:
            continue
        if entry.get("status") != "complete":
            print(f"Warning: Chapter {entry['number']} ({entry['title']}) not complete, skipping")
            continue
        numbered_chapters.append(entry)

    print(f"[{timestamp}] Found {len(numbered_chapters)} numbered chapters to load")

    # Load and process each chapter JSON
    topics = []
    book_content_rows = []

    for entry in numbered_chapters:
        chapter_file = entry.get("file")
        if not chapter_file:
            print(f"  Warning: No file for chapter {entry['number']}, skipping")
            continue

        chapter_path = DATA_DIR / chapter_file
        if not chapter_path.exists():
            print(f"  Warning: File not found: {chapter_path}, skipping")
            continue

        chapter_data = json.load(open(chapter_path))
        chapter_num = entry["number"]
        chapter_title = chapter_data.get("chapter_title", entry["title"])

        # Build topic entry
        key_concepts = extract_key_concepts(chapter_data)
        topics.append({
            "name": chapter_title,
            "order": chapter_num,
            "difficulty": difficulty_for_chapter(chapter_num),
            "key_concepts": key_concepts,
        })

        # Build book_content row
        summary = build_chapter_summary(chapter_data)
        db_sections = build_sections_for_db(chapter_data)

        book_content_rows.append({
            "book_title": "Grammaire Progressive du Français - Niveau Avancé",
            "chapter_number": chapter_num,
            "chapter_title": chapter_title,
            "sections": db_sections,
            "key_concepts": key_concepts,
            "case_studies": [],
            "summary": summary,
            "page_start": entry.get("page_start"),
            "page_end": entry.get("page_end"),
        })

        rule_count = sum(len(s.get("grammar_rules", [])) for s in chapter_data.get("sections", []))
        exercise_count = sum(len(s.get("exercises", [])) for s in chapter_data.get("sections", []))
        print(f"  Ch.{chapter_num:2d}: {chapter_title:<50s} | {rule_count:2d} rules | {exercise_count:2d} exercises | {len(key_concepts):2d} concepts")

    # Build track data
    track_data = {
        "name": TRACK_NAME,
        "description": "Grammaire avancée du français couvrant articles, adjectifs, temps verbaux, subjonctif, conditionnel, infinitif, participes, formes passive/pronominale/impersonnelle, discours indirect, adverbes, prépositions, pronoms, expressions du temps/cause/conséquence/comparaison/opposition/concession/but/condition/hypothèse et modalisation.",
        "language": LANGUAGE,
        "level": LEVEL,
        "topics": topics,
        "total_topics": len(topics),
        "rubric": {
            "accuracy": 3,
            "grammar": 3,
            "vocabulary": 2,
            "naturalness": 2,
        },
        "source_book": "Grammaire Progressive du Français - Niveau Avancé",
    }

    print(f"\n{'=' * 60}")
    print(f"Track: {TRACK_NAME}")
    print(f"Topics: {len(topics)}")
    print(f"Book content rows: {len(book_content_rows)}")
    print(f"{'=' * 60}")

    if args.dry_run:
        print("\n[DRY RUN] Would create track:")
        print(json.dumps(track_data, indent=2, ensure_ascii=False)[:500] + "...")
        print(f"\n[DRY RUN] Would create {len(book_content_rows)} book_content rows")
        for row in book_content_rows:
            print(f"  Ch.{row['chapter_number']}: {row['chapter_title']} (p.{row['page_start']}-{row['page_end']})")
        return

    # Create track
    supabase = create_supabase_client()

    print("\nCreating language track...")
    result = supabase.table("language_tracks").upsert(
        track_data,
        on_conflict="name",
    ).execute()

    track_id = result.data[0]["id"] if result.data else None
    if not track_id:
        print("Error: Failed to create track")
        sys.exit(1)
    print(f"Track created: {TRACK_NAME} (ID: {track_id})")

    # Save book_content rows
    print(f"\nSaving {len(book_content_rows)} book_content rows...")
    for row in book_content_rows:
        row["language_track_id"] = track_id
        supabase.table("book_content").upsert(
            row,
            on_conflict="book_title,chapter_number",
        ).execute()
        print(f"  Saved Ch.{row['chapter_number']}: {row['chapter_title']}")

    print(f"\nDone! Track '{TRACK_NAME}' loaded with {len(book_content_rows)} chapters.")
    print(f"Users can now select this track and daily exercises will use the grammar content.")


if __name__ == "__main__":
    main()
