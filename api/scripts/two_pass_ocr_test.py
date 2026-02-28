#!/usr/bin/env python3
"""
Two-pass OCR test: Raw transcription → structured JSON parsing.

Pass 1: Send page image to Gemini Vision → get faithful raw text
Pass 2: Send raw text to Gemini (text-only) → get structured JSON

Tests on first chapter pages to validate the approach.

Usage:
    python scripts/two_pass_ocr_test.py
    python scripts/two_pass_ocr_test.py --book-pages 8,9,10,11,12,13
"""

import argparse
import asyncio
import glob
import io
import json
import os
import re
import sys
import time
from datetime import datetime
from pathlib import Path

import fitz
import google.generativeai as genai
from PIL import Image

sys.path.insert(0, str(Path(__file__).parent.parent))
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")

# Book page = PDF 1-indexed page + 1 (cover takes PDF page 1)
# So PDF 0-indexed = book_page - 2
BOOK_PAGE_OFFSET = 2


def book_page_to_pdf_index(book_page: int) -> int:
    return book_page - BOOK_PAGE_OFFSET


def render_page(doc: fitz.Document, pdf_index: int, dpi: int = 200) -> Image.Image:
    page = doc.load_page(pdf_index)
    zoom = dpi / 72
    pix = page.get_pixmap(matrix=fitz.Matrix(zoom, zoom))
    return Image.open(io.BytesIO(pix.tobytes("jpeg")))


def parse_json(text: str) -> dict | None:
    fence = re.search(r"```(?:json)?\s*\n([\s\S]*?)\n```", text)
    if fence:
        try:
            return json.loads(fence.group(1))
        except json.JSONDecodeError:
            pass
    brace = re.search(r"\{[\s\S]*\}", text)
    if brace:
        try:
            return json.loads(brace.group())
        except json.JSONDecodeError:
            pass
    return None


def log(msg: str):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")


# ---------------------------------------------------------------------------
# Pass 1: Raw OCR
# ---------------------------------------------------------------------------

PASS1_PROMPT = """You are performing OCR on a scanned page from a French grammar textbook (Grammaire Progressive du Français, Niveau Avancé).

Transcribe EVERYTHING on this page exactly as it appears, preserving:
- All French text with correct accents (é, è, ê, ë, à, â, ù, û, ü, ô, î, ï, ç)
- Bold text (use **bold**)
- Italic text (use *italic*)
- Numbered lists, bullet points
- Blank lines / fill-in-the-blank spaces (use _____ for blanks)
- Section headings and subheadings
- Boxed/highlighted text (wrap with [BOX]...[/BOX])
- Warning triangles / notes (prefix with [NOTE])
- Page number at the bottom

IMPORTANT:
- Be extremely faithful to the original text
- Do NOT summarize or skip anything
- Do NOT translate to English
- Ignore any faded/reversed text bleeding through from the other side of the page
- Output as plain text with markdown formatting"""


# ---------------------------------------------------------------------------
# Pass 2: Structure parsing (text-only, no image)
# ---------------------------------------------------------------------------

PASS2_PROMPT = """You are parsing OCR'd text from a French grammar textbook page into structured JSON.

Here is the raw OCR text from book page {book_page}:

---
{raw_text}
---

Analyze this text and determine the page type, then extract structured content.

If this is a GRAMMAR EXPLANATION page (contains rules, examples, linguistic explanations):
{{
  "page_type": "grammar",
  "book_page": {book_page},
  "chapter_number": <int or null>,
  "chapter_title": "<e.g. L'ARTICLE>",
  "section_title": "<specific grammar topic, e.g. L'ARTICLE DÉFINI>",
  "intro_box": ["<sentences from any highlighted/boxed intro section>"],
  "rules": [
    {{
      "heading": "<rule category>",
      "explanation": "<explanation in French>",
      "examples": ["<example sentences>"],
      "notes": ["<exceptions, warnings, special cases>"]
    }}
  ]
}}

If this is an EXERCISES page (contains numbered exercises with instructions):
{{
  "page_type": "exercises",
  "book_page": {book_page},
  "chapter_title": "<from header>",
  "exercises": [
    {{
      "number": <int>,
      "instruction": "<bold instruction text>",
      "type": "<fill_blank | matching | composition | transformation | dialogue | free_response | underline>",
      "context": "<any setup text, word banks, model sentences, or null>",
      "items": [
        {{
          "number": <int or null>,
          "text": "<the sentence/question with _____ for blanks>",
          "blanks": <number of blanks>
        }}
      ]
    }}
  ]
}}

RULES:
- Preserve ALL French text with proper accents
- Do NOT translate anything
- Represent blanks as _____
- For free-form exercises (composition, free_response), put the full prompt as a single item
- Determine chapter_number from context (e.g. "1" if this is chapter 1 L'ARTICLE)
- Return ONLY valid JSON, no commentary"""


async def pass1_ocr(model, doc, book_page: int) -> str:
    """Pass 1: Raw OCR via vision."""
    pdf_idx = book_page_to_pdf_index(book_page)
    img = render_page(doc, pdf_idx)
    t0 = time.time()
    response = await asyncio.to_thread(
        model.generate_content, [PASS1_PROMPT, img]
    )
    elapsed = time.time() - t0
    log(f"  Pass 1 (OCR) book page {book_page}: {elapsed:.1f}s, {len(response.text)} chars")
    return response.text


async def pass2_parse(model, raw_text: str, book_page: int) -> dict:
    """Pass 2: Parse raw text into structured JSON (text-only, no image)."""
    prompt = PASS2_PROMPT.format(raw_text=raw_text, book_page=book_page)
    t0 = time.time()
    response = await asyncio.to_thread(
        model.generate_content, prompt
    )
    elapsed = time.time() - t0
    parsed = parse_json(response.text)
    log(f"  Pass 2 (parse) book page {book_page}: {elapsed:.1f}s, parsed={'YES' if parsed else 'NO'}")
    return parsed or {"_error": "JSON parse failed", "_raw": response.text[:1000]}


def print_results(pages_data: list[dict]):
    """Print structured results."""
    print("\n" + "=" * 70)
    print("  TWO-PASS OCR RESULTS")
    print("=" * 70)

    for pd in pages_data:
        book_page = pd["book_page"]
        raw = pd["raw_text"]
        structured = pd["structured"]

        print(f"\n{'─' * 60}")
        print(f"  BOOK PAGE {book_page}")
        print(f"  Pass 1: {len(raw)} chars  |  Pass 2: {structured.get('page_type', 'FAILED')}")
        print(f"{'─' * 60}")

        page_type = structured.get("page_type")

        if page_type == "grammar":
            print(f"  Chapter: {structured.get('chapter_number')} — {structured.get('chapter_title')}")
            print(f"  Section: {structured.get('section_title')}")
            intro = structured.get("intro_box", [])
            if intro:
                print(f"  Intro box ({len(intro)} sentences):")
                for s in intro[:3]:
                    print(f"    {s}")
            rules = structured.get("rules", [])
            print(f"  Rules: {len(rules)}")
            for i, r in enumerate(rules):
                heading = r.get("heading", "N/A")
                examples = r.get("examples", [])
                notes = r.get("notes", [])
                print(f"    [{i+1}] {heading}")
                for ex in examples[:2]:
                    print(f"        ex: {ex}")
                for n in notes[:1]:
                    print(f"        note: {n[:100]}")

        elif page_type == "exercises":
            print(f"  Chapter: {structured.get('chapter_title')}")
            exercises = structured.get("exercises", [])
            print(f"  Exercises: {len(exercises)}")
            total_items = 0
            for ex in exercises:
                items = ex.get("items", [])
                total_items += len(items)
                print(f"    [{ex.get('number')}] {ex.get('type', '?')} — {len(items)} items")
                print(f"        {ex.get('instruction', 'N/A')[:90]}")
                if items:
                    first = items[0]
                    print(f"        item 1: {str(first.get('text', ''))[:80]}")
            print(f"  Total items across all exercises: {total_items}")

        else:
            print(f"  PARSE FAILED")
            print(f"  Error: {structured.get('_error', 'unknown')}")
            if "_raw" in structured:
                print(f"  Raw response: {structured['_raw'][:300]}")

    # Summary
    print(f"\n{'=' * 70}")
    print("  SUMMARY")
    print(f"{'=' * 70}")
    grammar_pages = [p for p in pages_data if p["structured"].get("page_type") == "grammar"]
    exercise_pages = [p for p in pages_data if p["structured"].get("page_type") == "exercises"]
    failed = [p for p in pages_data if p["structured"].get("page_type") not in ("grammar", "exercises")]

    total_rules = sum(
        len(p["structured"].get("rules", []))
        for p in grammar_pages
    )
    total_exercises = sum(
        len(p["structured"].get("exercises", []))
        for p in exercise_pages
    )
    total_items = sum(
        sum(len(ex.get("items", [])) for ex in p["structured"].get("exercises", []))
        for p in exercise_pages
    )

    print(f"  Grammar pages: {len(grammar_pages)}  ({total_rules} rules extracted)")
    print(f"  Exercise pages: {len(exercise_pages)}  ({total_exercises} exercises, {total_items} items)")
    print(f"  Failed: {len(failed)}")
    print(f"\n  Full book projection (192 PDF pages ≈ 184 content pages):")
    print(f"    Pass 1: ~184 vision API calls")
    print(f"    Pass 2: ~184 text-only API calls")
    print(f"    Total: ~368 API calls")
    print(f"{'=' * 70}")


async def main():
    parser = argparse.ArgumentParser(description="Two-pass OCR test on grammar PDF")
    parser.add_argument("--book-pages", default="8,9,10,11,12,13",
                        help="Book page numbers (1-indexed as printed in the book). Default: 8-13 (ch.1 L'Article)")
    parser.add_argument("--output-dir", default="/tmp/two_pass_ocr",
                        help="Directory to save results")
    args = parser.parse_args()

    book_pages = [int(p.strip()) for p in args.book_pages.split(",")]

    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        print("Error: GOOGLE_API_KEY required")
        sys.exit(1)

    genai.configure(api_key=api_key)
    gemini_model = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")
    model = genai.GenerativeModel(gemini_model)
    log(f"Model: {gemini_model}")

    pdf_files = glob.glob("grammaire progressive*2008*")
    if not pdf_files:
        print("Error: Cannot find grammaire progressive PDF")
        sys.exit(1)

    pdf_path = pdf_files[0]
    doc = fitz.open(pdf_path)
    log(f"Opened: {Path(pdf_path).name} ({len(doc)} pages)")
    log(f"Book pages: {book_pages}")

    os.makedirs(args.output_dir, exist_ok=True)
    pages_data = []

    for bp in book_pages:
        pdf_idx = book_page_to_pdf_index(bp)
        if pdf_idx < 0 or pdf_idx >= len(doc):
            log(f"Skipping book page {bp} (PDF index {pdf_idx} out of range)")
            continue

        log(f"Processing book page {bp} (PDF index {pdf_idx})...")

        # Pass 1: Raw OCR
        raw_text = await pass1_ocr(model, doc, bp)

        # Save raw OCR
        with open(f"{args.output_dir}/p{bp:03d}_raw.md", "w") as f:
            f.write(raw_text)

        # Pass 2: Parse to JSON
        structured = await pass2_parse(model, raw_text, bp)

        # Save structured
        with open(f"{args.output_dir}/p{bp:03d}_structured.json", "w") as f:
            json.dump(structured, f, indent=2, ensure_ascii=False)

        pages_data.append({
            "book_page": bp,
            "pdf_index": pdf_idx,
            "raw_text": raw_text,
            "structured": structured,
        })

    doc.close()

    print_results(pages_data)

    # Save combined results
    combined = []
    for pd in pages_data:
        combined.append({
            "book_page": pd["book_page"],
            "pdf_index": pd["pdf_index"],
            "raw_char_count": len(pd["raw_text"]),
            "structured": pd["structured"],
        })
    with open(f"{args.output_dir}/combined_results.json", "w") as f:
        json.dump(combined, f, indent=2, ensure_ascii=False)
    log(f"Results saved to {args.output_dir}/")


if __name__ == "__main__":
    asyncio.run(main())
