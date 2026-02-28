#!/usr/bin/env python3
"""
Compare 3 OCR extraction approaches on sample pages from a scanned grammar PDF.

Approach A: Raw transcription (faithful OCR, preserve layout)
Approach B: Structured extraction (grammar + exercises as JSON)
Approach C: Two-page spread (send both grammar + exercise page together)

Usage:
    python scripts/compare_ocr_approaches.py
    python scripts/compare_ocr_approaches.py --pages 8,9,10,11
    python scripts/compare_ocr_approaches.py --output-dir /tmp/ocr_comparison
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


def render_page(doc: fitz.Document, page_num: int, dpi: int = 200) -> Image.Image:
    page = doc.load_page(page_num)
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
# Approach A: Raw Transcription
# ---------------------------------------------------------------------------

PROMPT_A = """You are performing OCR on a scanned page from a French grammar textbook.

Transcribe EVERYTHING on this page exactly as it appears, preserving:
- All French text with correct accents (é, è, ê, ë, à, â, ù, û, ü, ô, î, ï, ç)
- Bold and italic indicators (use **bold** and *italic*)
- Numbered lists, bullet points
- Blank lines / fill-in-the-blank indicators (use _____ for blanks)
- Section headings and subheadings
- Any boxed/highlighted text (indicate with [BOX] markers)
- Warning/note triangles (indicate with [NOTE])
- Page numbers

Be extremely faithful to the original. Do not summarize or skip anything.
Output the full transcription as plain text with markdown formatting."""


# ---------------------------------------------------------------------------
# Approach B: Structured Extraction (single page)
# ---------------------------------------------------------------------------

PROMPT_B_GRAMMAR = """You are extracting structured content from a French grammar textbook page.

This is a GRAMMAR EXPLANATION page. Extract all content into this JSON structure:

{
  "page_type": "grammar",
  "chapter_number": <int>,
  "chapter_title": "<string>",
  "section_title": "<string - the specific grammar topic on this page>",
  "intro_examples": ["<sentences in the green/highlighted box at top>"],
  "grammar_rules": [
    {
      "rule_heading": "<the bold rule description>",
      "explanation": "<the rule explanation in French>",
      "examples": ["<example sentences, preserve French with accents>"],
      "notes": ["<any warnings, exceptions, or additional notes>"]
    }
  ],
  "contracted_forms": ["<any contracted/special forms mentioned>"],
  "page_number": <int from bottom of page>
}

CRITICAL: Preserve ALL French text with proper accents. Do not translate to English.
Return ONLY valid JSON."""

PROMPT_B_EXERCISE = """You are extracting structured content from a French grammar textbook page.

This is an EXERCISES page. Extract all exercises into this JSON structure:

{
  "page_type": "exercises",
  "chapter_title": "<from the header>",
  "exercises": [
    {
      "exercise_number": <int>,
      "instruction": "<the bold instruction text>",
      "exercise_type": "<fill_blank | matching | composition | transformation | dialogue | free_response>",
      "context": "<any setup text, model sentences, or word banks>",
      "items": [
        {
          "number": <int or null>,
          "prompt": "<the sentence/question with _____ for blanks>",
          "blank_count": <number of blanks to fill>
        }
      ]
    }
  ],
  "page_number": <int>
}

CRITICAL: Preserve ALL French text with proper accents. Represent blanks as _____.
For exercises without numbered items (like free composition), set items to a single entry with the full prompt.
Return ONLY valid JSON."""


# ---------------------------------------------------------------------------
# Approach C: Two-page spread (grammar + exercises together)
# ---------------------------------------------------------------------------

PROMPT_C = """You are extracting a complete grammar lesson from a French textbook.
These two pages form a lesson spread: the left page has grammar explanations, the right page has exercises.

Extract the COMPLETE lesson into this JSON structure:

{
  "chapter_number": <int>,
  "chapter_title": "<main chapter title>",
  "section_title": "<specific grammar topic for this spread>",
  "page_range": [<left page number>, <right page number>],

  "grammar": {
    "intro_examples": ["<highlighted example sentences from the green box>"],
    "rules": [
      {
        "heading": "<rule category/heading>",
        "explanation": "<explanation text>",
        "examples": ["<example sentences>"],
        "notes": ["<exceptions, warnings>"]
      }
    ]
  },

  "exercises": [
    {
      "number": <int>,
      "instruction": "<bold instruction>",
      "type": "<fill_blank | matching | composition | transformation | dialogue | free_response>",
      "context": "<setup text, word banks, model sentences>",
      "items": [
        {
          "number": <int or null>,
          "prompt": "<sentence with _____ for blanks>",
          "blank_count": <int>
        }
      ]
    }
  ]
}

CRITICAL:
- Preserve ALL French text with proper accents (é, è, ê, ë, à, â, ù, û, ü, ô, î, ï, ç)
- Do not translate anything to English
- Represent fill-in-the-blank spaces as _____
- Capture every exercise, every item, every example
Return ONLY valid JSON."""


async def run_approach_a(model, doc, page_num: int) -> dict:
    """Raw transcription of a single page."""
    img = render_page(doc, page_num)
    t0 = time.time()
    response = await asyncio.to_thread(
        model.generate_content, [PROMPT_A, img]
    )
    elapsed = time.time() - t0
    return {
        "approach": "A_raw_transcription",
        "page": page_num + 1,
        "elapsed_sec": round(elapsed, 2),
        "result": response.text,
        "char_count": len(response.text),
    }


async def run_approach_b(model, doc, page_num: int, page_type: str) -> dict:
    """Structured extraction of a single page."""
    img = render_page(doc, page_num)
    prompt = PROMPT_B_GRAMMAR if page_type == "grammar" else PROMPT_B_EXERCISE
    t0 = time.time()
    response = await asyncio.to_thread(
        model.generate_content, [prompt, img]
    )
    elapsed = time.time() - t0
    parsed = parse_json(response.text)
    return {
        "approach": f"B_structured_{page_type}",
        "page": page_num + 1,
        "elapsed_sec": round(elapsed, 2),
        "result": parsed or {"_raw": response.text[:2000]},
        "parsed_ok": parsed is not None,
        "char_count": len(response.text),
    }


async def run_approach_c(model, doc, left_page: int, right_page: int) -> dict:
    """Two-page spread extraction."""
    img_left = render_page(doc, left_page)
    img_right = render_page(doc, right_page)
    t0 = time.time()
    response = await asyncio.to_thread(
        model.generate_content, [PROMPT_C, img_left, img_right]
    )
    elapsed = time.time() - t0
    parsed = parse_json(response.text)
    return {
        "approach": "C_two_page_spread",
        "pages": [left_page + 1, right_page + 1],
        "elapsed_sec": round(elapsed, 2),
        "result": parsed or {"_raw": response.text[:2000]},
        "parsed_ok": parsed is not None,
        "char_count": len(response.text),
    }


def print_comparison(results: list[dict], output_dir: str | None):
    """Print a readable comparison of all approaches."""
    print("\n" + "=" * 70)
    print("  OCR APPROACH COMPARISON")
    print("=" * 70)

    for r in results:
        approach = r["approach"]
        print(f"\n{'─' * 60}")
        print(f"  {approach}")
        pages = r.get("pages", [r.get("page")])
        print(f"  Pages: {pages}  |  Time: {r['elapsed_sec']}s  |  Chars: {r['char_count']}")
        print(f"{'─' * 60}")

        if approach == "A_raw_transcription":
            # Show first 1500 chars of raw text
            text = r["result"]
            print(text[:1500])
            if len(text) > 1500:
                print(f"\n  ... ({len(text) - 1500} more chars)")

        elif approach.startswith("B_structured"):
            if r.get("parsed_ok"):
                result = r["result"]
                print(f"  JSON parsed: YES")
                if result.get("page_type") == "grammar":
                    rules = result.get("grammar_rules", [])
                    print(f"  Section: {result.get('section_title', 'N/A')}")
                    print(f"  Intro examples: {len(result.get('intro_examples', []))}")
                    print(f"  Grammar rules: {len(rules)}")
                    for i, rule in enumerate(rules[:3]):
                        print(f"    [{i+1}] {rule.get('rule_heading', 'N/A')}")
                        for ex in rule.get("examples", [])[:2]:
                            print(f"        ex: {ex}")
                elif result.get("page_type") == "exercises":
                    exercises = result.get("exercises", [])
                    print(f"  Chapter: {result.get('chapter_title', 'N/A')}")
                    print(f"  Exercises: {len(exercises)}")
                    for ex in exercises:
                        items = ex.get("items", [])
                        print(f"    [{ex.get('exercise_number')}] {ex.get('exercise_type', '?')} — {len(items)} items")
                        print(f"        {ex.get('instruction', 'N/A')[:80]}")
            else:
                print(f"  JSON parsed: NO")
                print(f"  Raw: {str(r['result'].get('_raw', ''))[:500]}")

        elif approach == "C_two_page_spread":
            if r.get("parsed_ok"):
                result = r["result"]
                print(f"  JSON parsed: YES")
                print(f"  Chapter: {result.get('chapter_number')} — {result.get('chapter_title', 'N/A')}")
                print(f"  Section: {result.get('section_title', 'N/A')}")
                rules = result.get("grammar", {}).get("rules", [])
                exercises = result.get("exercises", [])
                print(f"  Grammar rules: {len(rules)}")
                print(f"  Exercises: {len(exercises)}")
                for i, rule in enumerate(rules[:3]):
                    print(f"    Rule [{i+1}]: {rule.get('heading', 'N/A')}")
                    for ex in rule.get("examples", [])[:2]:
                        print(f"        ex: {ex}")
                total_items = sum(len(ex.get("items", [])) for ex in exercises)
                print(f"  Total exercise items: {total_items}")
                for ex in exercises:
                    items = ex.get("items", [])
                    print(f"    Ex [{ex.get('number')}] {ex.get('type', '?')} — {len(items)} items")
                    print(f"        {ex.get('instruction', 'N/A')[:80]}")
            else:
                print(f"  JSON parsed: NO")
                print(f"  Raw: {str(r['result'].get('_raw', ''))[:500]}")

    # Summary
    print(f"\n{'=' * 70}")
    print("  SUMMARY")
    print(f"{'=' * 70}")
    total_time = sum(r["elapsed_sec"] for r in results)
    print(f"  Total API time: {total_time:.1f}s  ({len(results)} calls)")
    print()
    for r in results:
        parsed_status = ""
        if "parsed_ok" in r:
            parsed_status = f"  parsed={'YES' if r['parsed_ok'] else 'NO'}"
        print(f"  {r['approach']:30s}  {r['elapsed_sec']:5.1f}s  {r['char_count']:5d} chars{parsed_status}")

    # Cost estimate for full book
    print(f"\n  Cost projection for full 192-page book:")
    approach_a_time = sum(r["elapsed_sec"] for r in results if r["approach"] == "A_raw_transcription")
    approach_a_count = sum(1 for r in results if r["approach"] == "A_raw_transcription")
    if approach_a_count:
        avg_a = approach_a_time / approach_a_count
        print(f"    Approach A (raw per page):     ~{192 * avg_a / 60:.0f} min, 192 API calls")

    approach_b_time = sum(r["elapsed_sec"] for r in results if r["approach"].startswith("B_"))
    approach_b_count = sum(1 for r in results if r["approach"].startswith("B_"))
    if approach_b_count:
        avg_b = approach_b_time / approach_b_count
        print(f"    Approach B (structured/page):  ~{192 * avg_b / 60:.0f} min, 192 API calls")

    approach_c_time = sum(r["elapsed_sec"] for r in results if r["approach"] == "C_two_page_spread")
    approach_c_count = sum(1 for r in results if r["approach"] == "C_two_page_spread")
    if approach_c_count:
        avg_c = approach_c_time / approach_c_count
        print(f"    Approach C (2-page spread):    ~{96 * avg_c / 60:.0f} min, ~96 API calls")

    print(f"\n{'=' * 70}")


async def main():
    parser = argparse.ArgumentParser(description="Compare OCR approaches on scanned grammar PDF")
    parser.add_argument("--pages", default="8,9,10,11",
                        help="Comma-separated page numbers (1-indexed). Default: 8,9,10,11 (first chapter)")
    parser.add_argument("--output-dir", default="/tmp/ocr_comparison",
                        help="Directory to save results")
    parser.add_argument("--approach", choices=["a", "b", "c", "all"], default="all",
                        help="Which approach to run (default: all)")
    args = parser.parse_args()

    pages = [int(p.strip()) - 1 for p in args.pages.split(",")]  # convert to 0-indexed

    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        print("Error: GOOGLE_API_KEY required")
        sys.exit(1)

    genai.configure(api_key=api_key)
    gemini_model = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")
    model = genai.GenerativeModel(gemini_model)
    log(f"Using model: {gemini_model}")

    # Find the PDF
    pdf_files = glob.glob("grammaire progressive*2008*")
    if not pdf_files:
        pdf_files = glob.glob("**/grammaire progressive*2008*", recursive=True)
    if not pdf_files:
        print("Error: Cannot find grammaire progressive PDF")
        sys.exit(1)

    pdf_path = pdf_files[0]
    doc = fitz.open(pdf_path)
    log(f"Opened: {pdf_path} ({len(doc)} pages)")
    log(f"Testing pages: {[p+1 for p in pages]}")

    os.makedirs(args.output_dir, exist_ok=True)
    results = []

    # We expect pages to come in pairs: grammar (even page_num), exercises (odd page_num)
    # For the default pages 8,9,10,11:
    #   8 = grammar (L'article défini), 9 = exercises
    #   10 = grammar (continued), 11 = exercises

    run_a = args.approach in ("a", "all")
    run_b = args.approach in ("b", "all")
    run_c = args.approach in ("c", "all")

    # Approach A: Raw transcription on each page
    if run_a:
        for pg in pages:
            log(f"Approach A: Raw transcription on page {pg+1}...")
            result = await run_approach_a(model, doc, pg)
            results.append(result)
            # Save raw text
            with open(f"{args.output_dir}/A_page_{pg+1:03d}.md", "w") as f:
                f.write(result["result"])

    # Approach B: Structured extraction per page
    if run_b:
        for i, pg in enumerate(pages):
            # Determine page type based on position in the book
            # In Grammaire Progressive: even book-pages are grammar, odd are exercises
            # Book page 8 (index 7) = grammar, page 9 (index 8) = exercises
            page_type = "grammar" if (pg + 1) % 2 == 0 else "exercises"
            log(f"Approach B: Structured ({page_type}) on page {pg+1}...")
            result = await run_approach_b(model, doc, pg, page_type)
            results.append(result)
            with open(f"{args.output_dir}/B_page_{pg+1:03d}.json", "w") as f:
                json.dump(result["result"], f, indent=2, ensure_ascii=False)

    # Approach C: Two-page spreads
    if run_c:
        for i in range(0, len(pages) - 1, 2):
            left, right = pages[i], pages[i + 1]
            log(f"Approach C: Two-page spread (pages {left+1}-{right+1})...")
            result = await run_approach_c(model, doc, left, right)
            results.append(result)
            with open(f"{args.output_dir}/C_pages_{left+1:03d}_{right+1:03d}.json", "w") as f:
                json.dump(result["result"], f, indent=2, ensure_ascii=False)

    doc.close()

    # Print comparison
    print_comparison(results, args.output_dir)

    # Save full results
    results_path = f"{args.output_dir}/comparison_results.json"
    with open(results_path, "w") as f:
        json.dump(results, f, indent=2, ensure_ascii=False, default=str)
    log(f"Full results saved to: {results_path}")
    log(f"Individual files in: {args.output_dir}/")


if __name__ == "__main__":
    asyncio.run(main())
