#!/usr/bin/env python3
"""
Book ingestion script for extracting content from PDFs into the system design review system.

Usage:
    python scripts/ingest_book.py reliable.pdf
    python scripts/ingest_book.py reliable.pdf --track-name "Reliable ML"
    python scripts/ingest_book.py reliable.pdf --dry-run
    python scripts/ingest_book.py reliable.pdf --structure-only

Features:
- Two-pass chunked processing for large PDFs
- Pass 1: Discover chapters and sections
- Pass 2: Extract key concepts and case studies
- Creates a new system design track from book content
- Idempotent - can re-run without duplicating data
"""

import argparse
import asyncio
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
from supabase import create_client

# Load environment variables
load_dotenv(Path(__file__).parent.parent / ".env")


def create_supabase_client():
    """Create Supabase client from environment variables.

    Uses service role key for admin operations (bypasses RLS).
    """
    url = os.getenv("SUPABASE_URL")
    # Prefer service role key for admin operations
    key = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_KEY") or os.getenv("SUPABASE_ANON_KEY")

    if not url or not key:
        print("Error: SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY (or SUPABASE_KEY) must be set")
        sys.exit(1)

    return create_client(url, key)


def print_progress(message: str):
    """Print progress message with timestamp."""
    timestamp = datetime.now().strftime("%H:%M:%S")
    print(f"[{timestamp}] {message}")


def print_structure(book_structure: dict):
    """Pretty print the discovered book structure."""
    print("\n" + "=" * 60)
    print(f"BOOK: {book_structure.get('title', 'Unknown')}")
    print(f"Total Pages: {book_structure.get('total_pages', 0)}")
    print("=" * 60)

    for chapter in book_structure.get("chapters", []):
        print(f"\nChapter {chapter.get('chapter_number', '?')}: {chapter.get('title', 'Untitled')}")
        print(f"  Pages: {chapter.get('page_start', '?')} - {chapter.get('page_end', '?')}")

        if chapter.get("summary"):
            summary = chapter["summary"][:200] + "..." if len(chapter.get("summary", "")) > 200 else chapter.get("summary", "")
            print(f"  Summary: {summary}")

        if chapter.get("key_concepts"):
            print(f"  Key Concepts: {', '.join(chapter['key_concepts'][:5])}")
            if len(chapter.get("key_concepts", [])) > 5:
                print(f"    ... and {len(chapter['key_concepts']) - 5} more")

        if chapter.get("sections"):
            print(f"  Sections: {len(chapter['sections'])}")
            for section in chapter["sections"][:3]:
                print(f"    - {section.get('title', 'Untitled')}")
            if len(chapter.get("sections", [])) > 3:
                print(f"    ... and {len(chapter['sections']) - 3} more")

        if chapter.get("case_studies"):
            print(f"  Case Studies: {len(chapter['case_studies'])}")
            for cs in chapter["case_studies"][:2]:
                print(f"    - {cs.get('name', 'Unnamed')}: {cs.get('systems', [])}")


def create_track_from_book(supabase, book_structure: dict, track_name: str, dry_run: bool = False) -> str:
    """Create a system design track from extracted book content."""
    # Build topics from chapters
    topics = []
    for chapter in book_structure.get("chapters", []):
        # Collect example systems from case studies
        example_systems = []
        for cs in chapter.get("case_studies", []):
            example_systems.extend(cs.get("systems", []))
        # Deduplicate
        example_systems = list(dict.fromkeys(example_systems))[:5]

        topics.append({
            "name": chapter.get("title", f"Chapter {chapter.get('chapter_number', '?')}"),
            "order": chapter.get("chapter_number", 0),
            "difficulty": "hard",  # ML reliability is hard
            "example_systems": example_systems if example_systems else ["Production ML systems"],
            "key_concepts": chapter.get("key_concepts", [])[:10],
        })

    track_data = {
        "name": track_name,
        "description": f"System design topics from '{book_structure.get('title', 'Reliable Machine Learning')}' covering ML reliability, robustness, and production patterns",
        "track_type": "mle",
        "topics": topics,
        "total_topics": len(topics),
        "rubric": {
            "depth": 3,
            "tradeoffs": 3,
            "clarity": 2,
            "scalability": 2,
        },
    }

    if dry_run:
        print("\n[DRY RUN] Would create track:")
        print(json.dumps(track_data, indent=2))
        return "dry-run-track-id"

    # Upsert track (uses ON CONFLICT from migration)
    result = supabase.table("system_design_tracks").upsert(
        track_data,
        on_conflict="name",
    ).execute()

    track_id = result.data[0]["id"] if result.data else None
    print(f"\nCreated/updated track: {track_name} (ID: {track_id})")
    return track_id


def save_book_content(supabase, book_structure: dict, track_id: str, dry_run: bool = False):
    """Save extracted book content to database."""
    book_title = book_structure.get("title", "Reliable Machine Learning")

    for chapter in book_structure.get("chapters", []):
        content_data = {
            "book_title": book_title,
            "chapter_number": chapter.get("chapter_number", 0),
            "chapter_title": chapter.get("title", "Untitled"),
            "sections": chapter.get("sections", []),
            "key_concepts": chapter.get("key_concepts", []),
            "case_studies": chapter.get("case_studies", []),
            "summary": chapter.get("summary"),
            "page_start": chapter.get("page_start"),
            "page_end": chapter.get("page_end"),
            "track_id": track_id if track_id != "dry-run-track-id" else None,
        }

        if dry_run:
            print(f"[DRY RUN] Would save chapter {chapter.get('chapter_number')}: {chapter.get('title')}")
            continue

        # Upsert content (uses ON CONFLICT from migration)
        supabase.table("book_content").upsert(
            content_data,
            on_conflict="book_title,chapter_number",
        ).execute()
        print(f"Saved chapter {chapter.get('chapter_number')}: {chapter.get('title')}")


async def main():
    parser = argparse.ArgumentParser(
        description="Ingest a PDF book into the system design review system"
    )
    parser.add_argument("pdf_path", help="Path to the PDF file")
    parser.add_argument(
        "--track-name",
        default="Reliable ML",
        help="Name for the created track (default: 'Reliable ML')",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be done without making changes",
    )
    parser.add_argument(
        "--structure-only",
        action="store_true",
        help="Only run structure discovery (Pass 1), skip content extraction",
    )
    parser.add_argument(
        "--output-json",
        help="Output extracted structure to JSON file",
    )

    args = parser.parse_args()

    # Validate PDF path
    pdf_path = Path(args.pdf_path)
    if not pdf_path.exists():
        # Try relative to monorepo root
        pdf_path = Path(__file__).parent.parent.parent / args.pdf_path
        if not pdf_path.exists():
            print(f"Error: PDF not found: {args.pdf_path}")
            sys.exit(1)

    pdf_path = pdf_path.resolve()
    print(f"PDF path: {pdf_path}")

    # Check for Google API key
    if not os.getenv("GOOGLE_API_KEY"):
        print("Error: GOOGLE_API_KEY must be set for Gemini integration")
        sys.exit(1)

    # Import the service (after env vars are loaded)
    from app.services.book_ingestion_service import BookIngestionService

    service = BookIngestionService()

    if not service.configured:
        print("Error: Gemini API not configured")
        sys.exit(1)

    total_pages = service.get_total_pages(str(pdf_path))
    print(f"PDF has {total_pages} pages")

    if args.structure_only:
        # Pass 1 only: Structure discovery
        print("\nRunning Pass 1: Structure Discovery...")
        chapters_info = await service.discover_structure(str(pdf_path), print_progress)

        print(f"\nDiscovered {len(chapters_info)} chapters:")
        for ch in chapters_info:
            print(f"  {ch.get('title', 'Untitled')} (pages {ch.get('page_start')}-{ch.get('page_end')})")
            if ch.get("sections"):
                for sec in ch["sections"][:3]:
                    print(f"    - {sec.get('title')}")

        if args.output_json:
            with open(args.output_json, "w") as f:
                json.dump({"chapters": chapters_info}, f, indent=2)
            print(f"\nStructure saved to: {args.output_json}")

        return

    # Full ingestion
    print("\nStarting full book ingestion...")
    book_structure = await service.ingest_book(str(pdf_path), print_progress)

    # Convert to dict for processing
    book_dict = {
        "title": book_structure.title,
        "chapters": [
            {
                "chapter_number": ch.chapter_number,
                "title": ch.title,
                "summary": ch.summary,
                "sections": [s.model_dump() for s in ch.sections],
                "key_concepts": ch.key_concepts,
                "case_studies": [cs.model_dump() for cs in ch.case_studies],
                "page_start": ch.page_start,
                "page_end": ch.page_end,
            }
            for ch in book_structure.chapters
        ],
        "total_pages": book_structure.total_pages,
    }

    # Print extracted structure
    print_structure(book_dict)

    # Save to JSON if requested
    if args.output_json:
        with open(args.output_json, "w") as f:
            json.dump(book_dict, f, indent=2)
        print(f"\nFull content saved to: {args.output_json}")

    # Create track and save to database
    supabase = create_supabase_client()

    track_id = create_track_from_book(supabase, book_dict, args.track_name, args.dry_run)
    save_book_content(supabase, book_dict, track_id, args.dry_run)

    print("\nIngestion complete!")
    if not args.dry_run:
        print(f"Track '{args.track_name}' is ready for use in system design reviews.")


if __name__ == "__main__":
    asyncio.run(main())
