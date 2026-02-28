#!/usr/bin/env python3
"""
Standalone script to analyze a grammar PDF and produce a diagnostic report.

Runs several passes on a language-learning PDF to understand its structure,
text quality, and what extraction approach works best (text vs vision vs hybrid).
The output informs how the real ingestion pipeline should be built.

Usage:
    python scripts/analyze_language_pdf.py grammaire.pdf --language french --level b1
    python scripts/analyze_language_pdf.py grammaire.pdf --language french --level b1 --sample-pages 5,6,41,42
    python scripts/analyze_language_pdf.py grammaire.pdf --language french --level b1 --output-json analysis.json
"""

import argparse
import asyncio
import io
import json
import os
import sys
import unicodedata
from datetime import datetime
from pathlib import Path

import fitz  # PyMuPDF
import google.generativeai as genai
from PIL import Image

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv

# Load environment variables
load_dotenv(Path(__file__).parent.parent / ".env")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def timestamp() -> str:
    return datetime.now().strftime("%H:%M:%S")


def log(msg: str):
    print(f"[{timestamp()}] {msg}")


def render_page_image(doc: fitz.Document, page_num: int, dpi: int = 200) -> Image.Image:
    """Render a single PDF page to a PIL Image at the given DPI."""
    page = doc.load_page(page_num)
    zoom = dpi / 72
    mat = fitz.Matrix(zoom, zoom)
    pix = page.get_pixmap(matrix=mat)
    return Image.open(io.BytesIO(pix.tobytes("jpeg")))


def classify_text_quality(text: str) -> str:
    """Classify extracted text as good_text / partial_text / garbled / empty."""
    if not text or len(text.strip()) < 10:
        return "empty"

    printable = sum(1 for c in text if c.isprintable() or c in "\n\r\t")
    ratio = printable / len(text) if text else 0

    # Check for excessive replacement characters or encoding artefacts
    replacement_chars = text.count("\ufffd") + text.count("�")
    if replacement_chars > len(text) * 0.05:
        return "garbled"

    # Check for ligature / combining-character density (common in garbled PDF text)
    combining = sum(1 for c in text if unicodedata.category(c).startswith("M"))
    if combining > len(text) * 0.1:
        return "garbled"

    if ratio < 0.7:
        return "garbled"
    if ratio < 0.9:
        return "partial_text"
    return "good_text"


def spread_sample_pages(total: int, count: int = 10) -> list[int]:
    """Pick ~count pages evenly spread across the document (0-indexed)."""
    if total <= count:
        return list(range(total))
    step = max(1, total // count)
    pages = list(range(0, total, step))[:count]
    # Always include last page
    if pages[-1] != total - 1:
        pages[-1] = total - 1
    return pages


def parse_json_from_text(text: str) -> dict | None:
    """Extract the first JSON object from Gemini response text."""
    # Try to find JSON block in markdown fences first
    import re
    fence_match = re.search(r"```(?:json)?\s*\n([\s\S]*?)\n```", text)
    if fence_match:
        try:
            return json.loads(fence_match.group(1))
        except json.JSONDecodeError:
            pass
    # Fallback: find outermost braces
    brace_match = re.search(r"\{[\s\S]*\}", text)
    if brace_match:
        try:
            return json.loads(brace_match.group())
        except json.JSONDecodeError:
            pass
    return None


# ---------------------------------------------------------------------------
# Step 1: PDF Metadata & TOC Analysis
# ---------------------------------------------------------------------------

def analyze_metadata(pdf_path: str) -> dict:
    """Extract PDF metadata, TOC structure, and heading patterns."""
    doc = fitz.open(pdf_path)
    meta = doc.metadata or {}
    toc = doc.get_toc()
    total_pages = len(doc)
    file_size_mb = Path(pdf_path).stat().st_size / (1024 * 1024)
    doc.close()

    # Analyze TOC structure
    toc_analysis = {
        "entry_count": len(toc),
        "levels": {},
        "sample_entries": [],
    }
    heading_patterns = []
    if toc:
        for level, title, page in toc:
            toc_analysis["levels"][str(level)] = toc_analysis["levels"].get(str(level), 0) + 1
        toc_analysis["sample_entries"] = [
            {"level": lvl, "title": t, "page": p} for lvl, t, p in toc[:15]
        ]
        # Detect heading patterns
        titles = [t for _, t, _ in toc]
        if any(t.lower().startswith("leçon") or t.lower().startswith("lecon") for t in titles):
            heading_patterns.append("Leçon-numbered")
        if any(t.lower().startswith("chapitre") for t in titles):
            heading_patterns.append("Chapitre-numbered")
        if any(t[0].isdigit() for t in titles if t):
            heading_patterns.append("Digit-prefixed")
        if any(t.lower().startswith("chapter") for t in titles):
            heading_patterns.append("Chapter-numbered")
        if not heading_patterns:
            heading_patterns.append("Flat / unlabelled")

    return {
        "total_pages": total_pages,
        "file_size_mb": round(file_size_mb, 2),
        "title": meta.get("title", ""),
        "author": meta.get("author", ""),
        "subject": meta.get("subject", ""),
        "creator": meta.get("creator", ""),
        "toc": toc_analysis,
        "heading_patterns": heading_patterns,
    }


# ---------------------------------------------------------------------------
# Step 2: Text Extraction Quality Assessment
# ---------------------------------------------------------------------------

def assess_text_quality(pdf_path: str, sample_pages: list[int] | None = None) -> dict:
    """Extract text from sample pages and classify quality."""
    doc = fitz.open(pdf_path)
    total_pages = len(doc)

    if sample_pages is None:
        sample_pages = spread_sample_pages(total_pages)

    results = []
    for pg in sample_pages:
        if pg >= total_pages:
            continue
        page = doc.load_page(pg)
        text = page.get_text()
        quality = classify_text_quality(text)
        results.append({
            "page": pg + 1,  # 1-indexed for display
            "char_count": len(text),
            "quality": quality,
            "sample": text[:300].replace("\n", " ").strip(),
        })
    doc.close()

    # Summarise
    counts = {"good_text": 0, "partial_text": 0, "garbled": 0, "empty": 0}
    for r in results:
        counts[r["quality"]] += 1
    total = len(results) or 1

    return {
        "pages_sampled": len(results),
        "quality_counts": counts,
        "good_pct": round(100 * counts["good_text"] / total, 1),
        "partial_pct": round(100 * counts["partial_text"] / total, 1),
        "garbled_pct": round(100 * counts["garbled"] / total, 1),
        "empty_pct": round(100 * counts["empty"] / total, 1),
        "per_page": results,
    }


# ---------------------------------------------------------------------------
# Step 3: Vision-Based Sample Extraction
# ---------------------------------------------------------------------------

VISION_ANALYSIS_PROMPT = """You are analyzing a page from a {language} grammar textbook ({level} level).

Describe what you see on this page:
1. What grammar topic is this page about?
2. List the grammar rules explained
3. List any example sentences (preserve original {language})
4. List any vocabulary
5. Describe the page layout (tables, boxes, columns, illustrations)

Return your analysis as JSON:
{{
  "grammar_topic": "...",
  "grammar_rules": ["..."],
  "example_sentences": ["..."],
  "vocabulary": ["..."],
  "layout_description": "..."
}}"""


async def vision_analysis(
    model: genai.GenerativeModel,
    doc: fitz.Document,
    page_nums: list[int],
    language: str,
    level: str,
) -> list[dict]:
    """Send page images to Gemini vision and get grammar analysis."""
    results = []
    for pg in page_nums:
        log(f"  Vision analysis on page {pg + 1}...")
        img = render_page_image(doc, pg)
        prompt = VISION_ANALYSIS_PROMPT.format(language=language, level=level)
        try:
            response = await asyncio.to_thread(
                model.generate_content, [prompt, img]
            )
            parsed = parse_json_from_text(response.text)
            results.append({
                "page": pg + 1,
                "analysis": parsed or {"raw_text": response.text},
                "success": parsed is not None,
            })
        except Exception as e:
            results.append({
                "page": pg + 1,
                "analysis": {"error": str(e)},
                "success": False,
            })
    return results


# ---------------------------------------------------------------------------
# Step 4: Structure Discovery Comparison
# ---------------------------------------------------------------------------

STRUCTURE_PROMPT = """Analyze this content from a {language} grammar textbook ({level} level).

Identify all grammar lessons or topics you can find. For each one, extract:
- Lesson title / grammar topic
- Page number(s) if visible
- Key grammar points covered

Return as JSON:
{{
  "lessons_found": [
    {{"title": "...", "page": 0, "grammar_points": ["..."]}}
  ]
}}"""


async def compare_structure_discovery(
    model: genai.GenerativeModel,
    doc: fitz.Document,
    page_nums: list[int],
    language: str,
    level: str,
) -> dict:
    """Run text-based and vision-based structure discovery on the same pages, then compare."""
    prompt = STRUCTURE_PROMPT.format(language=language, level=level)

    # Text-based
    log("  Text-based structure discovery...")
    text_parts = []
    for pg in page_nums:
        page = doc.load_page(pg)
        text_parts.append(f"--- PAGE {pg + 1} ---\n{page.get_text()}")
    combined_text = "\n".join(text_parts)

    text_result = None
    try:
        response = await asyncio.to_thread(
            model.generate_content,
            f"{prompt}\n\nExtracted text:\n{combined_text[:50000]}",
        )
        text_result = parse_json_from_text(response.text)
    except Exception as e:
        text_result = {"error": str(e)}

    # Vision-based
    log("  Vision-based structure discovery...")
    images = [render_page_image(doc, pg) for pg in page_nums]
    vision_result = None
    try:
        response = await asyncio.to_thread(
            model.generate_content, [prompt] + images
        )
        vision_result = parse_json_from_text(response.text)
    except Exception as e:
        vision_result = {"error": str(e)}

    text_lessons = (text_result or {}).get("lessons_found", [])
    vision_lessons = (vision_result or {}).get("lessons_found", [])

    return {
        "pages_analyzed": [pg + 1 for pg in page_nums],
        "text_based": {
            "lessons_found": len(text_lessons),
            "result": text_result,
        },
        "vision_based": {
            "lessons_found": len(vision_lessons),
            "result": vision_result,
        },
        "recommendation": (
            "vision" if len(vision_lessons) > len(text_lessons)
            else "text" if len(text_lessons) > len(vision_lessons)
            else "hybrid"
        ),
    }


# ---------------------------------------------------------------------------
# Step 5: Content Extraction Sample
# ---------------------------------------------------------------------------

CONTENT_EXTRACTION_PROMPT = """Analyze these pages from a {language} grammar textbook ({level} level).

Extract:
1. Lesson title / grammar topic
2. Summary of the grammar rule(s) (2-3 sentences in English)
3. Key grammar concepts (list of terms/rules, in {language})
4. Example sentences from the page (preserve original {language})
5. Vocabulary introduced (if any)
6. Conjugation tables or grammar tables (if present)

Return as JSON:
{{
  "lesson_title": "...",
  "summary": "...",
  "grammar_concepts": ["...", "..."],
  "example_sentences": [{{"text": "...", "grammar_point": "..."}}],
  "vocabulary": [{{"word": "...", "type": "...", "note": "..."}}],
  "tables": [{{"type": "conjugation", "content": "..."}}]
}}"""


async def extract_content_sample(
    model: genai.GenerativeModel,
    doc: fitz.Document,
    page_nums: list[int],
    language: str,
    level: str,
) -> dict:
    """Full content extraction on a lesson spread (1-2 pages)."""
    images = [render_page_image(doc, pg) for pg in page_nums]
    prompt = CONTENT_EXTRACTION_PROMPT.format(language=language, level=level)

    try:
        response = await asyncio.to_thread(
            model.generate_content, [prompt] + images
        )
        parsed = parse_json_from_text(response.text)
        if parsed:
            # Show how it maps to existing book_content schema
            schema_mapping = {
                "chapter_title": parsed.get("lesson_title"),
                "summary": parsed.get("summary"),
                "key_concepts": parsed.get("grammar_concepts", []),
                "sections": [
                    {
                        "title": parsed.get("lesson_title"),
                        "key_points": [
                            s.get("text", s) if isinstance(s, dict) else s
                            for s in parsed.get("example_sentences", [])
                        ],
                    }
                ],
                "case_studies": [
                    {
                        "name": v.get("word", ""),
                        "description": v.get("note", ""),
                        "systems": [v.get("type", "")],
                    }
                    for v in parsed.get("vocabulary", [])
                    if isinstance(v, dict)
                ],
            }
            return {
                "pages": [pg + 1 for pg in page_nums],
                "extracted": parsed,
                "schema_mapping": schema_mapping,
                "success": True,
            }
        return {
            "pages": [pg + 1 for pg in page_nums],
            "raw_response": response.text[:2000],
            "success": False,
        }
    except Exception as e:
        return {
            "pages": [pg + 1 for pg in page_nums],
            "error": str(e),
            "success": False,
        }


# ---------------------------------------------------------------------------
# Report Printing
# ---------------------------------------------------------------------------

def print_report(report: dict):
    """Print a human-readable analysis report to stdout."""
    meta = report["metadata"]
    tq = report["text_quality"]

    print("\n" + "=" * 70)
    print("  LANGUAGE PDF ANALYSIS REPORT")
    print("=" * 70)

    # PDF Overview
    print(f"\n{'─' * 40}")
    print("  PDF OVERVIEW")
    print(f"{'─' * 40}")
    print(f"  File:       {report.get('pdf_path', 'N/A')}")
    print(f"  Pages:      {meta['total_pages']}")
    print(f"  Size:       {meta['file_size_mb']} MB")
    print(f"  Title:      {meta.get('title') or '(none)'}")
    print(f"  Author:     {meta.get('author') or '(none)'}")
    print(f"  Language:   {report.get('language', 'N/A')}")
    print(f"  Level:      {report.get('level', 'N/A')}")

    # TOC
    toc = meta.get("toc", {})
    print(f"\n  TOC Entries:     {toc.get('entry_count', 0)}")
    print(f"  Heading Patterns: {', '.join(meta.get('heading_patterns', ['none']))}")
    if toc.get("levels"):
        print(f"  TOC Levels:      {toc['levels']}")
    if toc.get("sample_entries"):
        print("  Sample TOC:")
        for entry in toc["sample_entries"][:8]:
            indent = "    " * entry["level"]
            print(f"    {indent}{entry['title']} (p.{entry['page']})")

    # Text Quality
    print(f"\n{'─' * 40}")
    print("  TEXT EXTRACTION QUALITY")
    print(f"{'─' * 40}")
    print(f"  Pages sampled: {tq['pages_sampled']}")
    print(f"  Good text:     {tq['good_pct']}%")
    print(f"  Partial text:  {tq['partial_pct']}%")
    print(f"  Garbled:       {tq['garbled_pct']}%")
    print(f"  Empty:         {tq['empty_pct']}%")
    print()
    for pg in tq["per_page"]:
        status = {"good_text": "+", "partial_text": "~", "garbled": "!", "empty": "-"}[pg["quality"]]
        print(f"  [{status}] Page {pg['page']:>4}  ({pg['char_count']:>5} chars)  {pg['quality']}")
        if pg["sample"]:
            print(f"         {pg['sample'][:100]}...")

    # Vision Analysis
    if report.get("vision_analysis"):
        print(f"\n{'─' * 40}")
        print("  VISION-BASED ANALYSIS")
        print(f"{'─' * 40}")
        for va in report["vision_analysis"]:
            print(f"\n  Page {va['page']}:")
            analysis = va.get("analysis", {})
            if va["success"]:
                print(f"    Topic: {analysis.get('grammar_topic', 'N/A')}")
                rules = analysis.get("grammar_rules", [])
                if rules:
                    print(f"    Rules: {', '.join(rules[:5])}")
                examples = analysis.get("example_sentences", [])
                if examples:
                    print(f"    Examples ({len(examples)}):")
                    for ex in examples[:3]:
                        print(f"      - {ex}")
                layout = analysis.get("layout_description", "")
                if layout:
                    print(f"    Layout: {layout[:150]}")
            else:
                print(f"    Error: {analysis.get('error', analysis.get('raw_text', 'unknown')[:200])}")

    # Structure Comparison
    if report.get("structure_comparison"):
        sc = report["structure_comparison"]
        print(f"\n{'─' * 40}")
        print("  STRUCTURE DISCOVERY COMPARISON")
        print(f"{'─' * 40}")
        print(f"  Pages analyzed: {sc['pages_analyzed']}")
        print(f"  Text-based:   {sc['text_based']['lessons_found']} lessons found")
        print(f"  Vision-based: {sc['vision_based']['lessons_found']} lessons found")
        print(f"  Recommendation: {sc['recommendation']}")

    # Content Extraction Sample
    if report.get("content_sample"):
        cs = report["content_sample"]
        print(f"\n{'─' * 40}")
        print("  CONTENT EXTRACTION SAMPLE")
        print(f"{'─' * 40}")
        print(f"  Pages: {cs.get('pages', 'N/A')}")
        if cs.get("success"):
            ext = cs.get("extracted", {})
            print(f"  Lesson:  {ext.get('lesson_title', 'N/A')}")
            print(f"  Summary: {ext.get('summary', 'N/A')}")
            concepts = ext.get("grammar_concepts", [])
            if concepts:
                print(f"  Concepts: {', '.join(concepts[:8])}")
            examples = ext.get("example_sentences", [])
            if examples:
                print(f"  Example sentences ({len(examples)}):")
                for ex in examples[:4]:
                    if isinstance(ex, dict):
                        print(f"    - {ex.get('text', '')}  [{ex.get('grammar_point', '')}]")
                    else:
                        print(f"    - {ex}")
            vocab = ext.get("vocabulary", [])
            if vocab:
                print(f"  Vocabulary ({len(vocab)}):")
                for v in vocab[:5]:
                    if isinstance(v, dict):
                        print(f"    - {v.get('word', '')} ({v.get('type', '')}) {v.get('note', '')}")
                    else:
                        print(f"    - {v}")
            tables = ext.get("tables", [])
            if tables:
                print(f"  Tables ({len(tables)}):")
                for t in tables[:3]:
                    if isinstance(t, dict):
                        print(f"    - [{t.get('type', '')}] {str(t.get('content', ''))[:120]}")

            # Schema mapping
            print(f"\n  Schema Mapping (-> book_content):")
            sm = cs.get("schema_mapping", {})
            print(f"    chapter_title:  {sm.get('chapter_title')}")
            print(f"    summary:        {(sm.get('summary') or '')[:100]}")
            print(f"    key_concepts:   {sm.get('key_concepts', [])[:5]}")
            print(f"    sections:       {len(sm.get('sections', []))} section(s)")
            print(f"    case_studies:   {len(sm.get('case_studies', []))} mapped vocabulary entries")
        else:
            print(f"  Error: {cs.get('error', 'extraction failed')}")

    # Overall Recommendation
    print(f"\n{'─' * 40}")
    print("  RECOMMENDATION")
    print(f"{'─' * 40}")

    # Determine recommended approach
    good_pct = tq["good_pct"]
    rec_approach = "vision"
    if good_pct >= 80:
        rec_approach = "text"
    elif good_pct >= 50:
        rec_approach = "hybrid"

    # Override with structure comparison if available
    if report.get("structure_comparison"):
        sc_rec = report["structure_comparison"]["recommendation"]
        if sc_rec != rec_approach:
            rec_approach = "hybrid"

    print(f"  Extraction approach: {rec_approach}")
    if rec_approach == "text":
        print("  Text extraction quality is high — use text-based pipeline.")
    elif rec_approach == "vision":
        print("  Text extraction is poor — use vision-based pipeline (page images to Gemini).")
    else:
        print("  Mixed quality — use hybrid (text where good, vision for garbled/image-heavy pages).")

    # Cost estimate
    total_pages = meta["total_pages"]
    if rec_approach == "text":
        api_calls = max(1, total_pages // 30)
    elif rec_approach == "vision":
        api_calls = total_pages  # one call per page
    else:
        api_calls = max(1, total_pages // 2)

    print(f"\n  Estimated Gemini API calls for full ingestion: ~{api_calls}")
    print(f"  (Based on {total_pages} pages, {rec_approach} approach)")

    print("\n" + "=" * 70)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

async def main():
    parser = argparse.ArgumentParser(
        description="Analyze a language-learning PDF and produce a diagnostic report"
    )
    parser.add_argument("pdf_path", help="Path to the PDF file")
    parser.add_argument(
        "--language",
        required=True,
        help="Target language (e.g., french, chinese, spanish)",
    )
    parser.add_argument(
        "--level",
        required=True,
        choices=["a1", "a2", "b1", "b2", "c1", "c2"],
        help="CEFR level",
    )
    parser.add_argument(
        "--sample-pages",
        help="Comma-separated page numbers (1-indexed) for vision analysis (e.g., 5,6,41,42)",
    )
    parser.add_argument(
        "--output-json",
        help="Write full analysis report to JSON file",
    )
    parser.add_argument(
        "--skip-vision",
        action="store_true",
        help="Skip Gemini vision steps (steps 3-5) — useful for quick text-only assessment",
    )

    args = parser.parse_args()

    # Validate PDF
    pdf_path = Path(args.pdf_path)
    if not pdf_path.exists():
        pdf_path = Path(__file__).parent.parent.parent / args.pdf_path
        if not pdf_path.exists():
            print(f"Error: PDF not found: {args.pdf_path}")
            sys.exit(1)
    pdf_path = pdf_path.resolve()

    # Validate API key for vision steps
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key and not args.skip_vision:
        print("Error: GOOGLE_API_KEY must be set (or use --skip-vision)")
        sys.exit(1)

    # Configure Gemini
    model = None
    if api_key:
        genai.configure(api_key=api_key)
        gemini_model = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")
        model = genai.GenerativeModel(gemini_model)
        log(f"Using Gemini model: {gemini_model}")

    log(f"Analyzing: {pdf_path}")
    log(f"Language: {args.language}, Level: {args.level}")

    # ── Step 1: Metadata & TOC ──────────────────────────────────────────
    log("Step 1/5: PDF Metadata & TOC Analysis")
    metadata = analyze_metadata(str(pdf_path))

    # ── Step 2: Text Quality ────────────────────────────────────────────
    log("Step 2/5: Text Extraction Quality Assessment")
    text_quality = assess_text_quality(str(pdf_path))

    report = {
        "pdf_path": str(pdf_path),
        "language": args.language,
        "level": args.level,
        "analyzed_at": datetime.now().isoformat(),
        "metadata": metadata,
        "text_quality": text_quality,
    }

    if args.skip_vision:
        log("Skipping vision steps (--skip-vision)")
        print_report(report)
        if args.output_json:
            with open(args.output_json, "w") as f:
                json.dump(report, f, indent=2, default=str)
            log(f"Report saved to: {args.output_json}")
        return

    # Determine which pages to use for vision analysis
    if args.sample_pages:
        vision_pages = [int(p.strip()) - 1 for p in args.sample_pages.split(",")]
    else:
        # Pick 2-4 pages: one from early, one from middle, one from late
        total = metadata["total_pages"]
        vision_pages = []
        # Skip first few pages (title, TOC)
        early = min(5, total - 1)
        mid = total // 2
        late = min(total - 5, total - 1)
        for pg in [early, mid, late]:
            if 0 <= pg < total and pg not in vision_pages:
                vision_pages.append(pg)
        # Add one more from first quarter if we have space
        q1 = total // 4
        if q1 not in vision_pages and len(vision_pages) < 4:
            vision_pages.insert(1, q1)
        vision_pages.sort()

    doc = fitz.open(str(pdf_path))

    # ── Step 3: Vision Analysis ─────────────────────────────────────────
    log(f"Step 3/5: Vision-Based Sample Extraction (pages {[p+1 for p in vision_pages]})")
    report["vision_analysis"] = await vision_analysis(
        model, doc, vision_pages, args.language, args.level
    )

    # ── Step 4: Structure Comparison ────────────────────────────────────
    # Use a subset of pages (first few content pages)
    structure_pages = vision_pages[:3]
    log(f"Step 4/5: Structure Discovery Comparison (pages {[p+1 for p in structure_pages]})")
    report["structure_comparison"] = await compare_structure_discovery(
        model, doc, structure_pages, args.language, args.level
    )

    # ── Step 5: Content Extraction Sample ───────────────────────────────
    # Pick first 2 vision pages as a "lesson spread"
    lesson_pages = vision_pages[:2]
    log(f"Step 5/5: Content Extraction Sample (pages {[p+1 for p in lesson_pages]})")
    report["content_sample"] = await extract_content_sample(
        model, doc, lesson_pages, args.language, args.level
    )

    doc.close()

    # Print report
    print_report(report)

    # Save JSON
    if args.output_json:
        with open(args.output_json, "w") as f:
            json.dump(report, f, indent=2, default=str)
        log(f"Report saved to: {args.output_json}")


if __name__ == "__main__":
    asyncio.run(main())
