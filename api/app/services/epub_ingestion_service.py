"""Epub ingestion service for extracting structure and content from epub files."""

import asyncio
import json
import re
from pathlib import Path
from typing import Optional

import ebooklib
from bs4 import BeautifulSoup
from ebooklib import epub

import google.generativeai as genai

from app.config import get_settings
from app.models.book_schemas import (
    BookStructure,
    CaseStudy,
    ChapterContent,
    ContentExtractionResult,
    SectionInfo,
)


class EpubIngestionService:
    """
    Service for ingesting epub books into the language learning system.

    Uses a two-pass approach:
    1. Structure discovery: Extract TOC/spine to identify chapters
    2. Content extraction: Use Gemini to analyze chapter text for grammar topics
    """

    # Max characters per Gemini request
    MAX_CONTENT_LENGTH = 80000

    def __init__(self):
        settings = get_settings()
        if settings.google_api_key:
            genai.configure(api_key=settings.google_api_key)
            self.model = genai.GenerativeModel(settings.gemini_model)
            self.configured = True
        else:
            self.model = None
            self.configured = False

    def _read_epub(self, epub_path: str) -> epub.EpubBook:
        """Read and return an epub book object."""
        return epub.read_epub(epub_path)

    def _extract_text_from_html(self, html_content: bytes) -> str:
        """Extract clean text from HTML content, preserving French unicode."""
        soup = BeautifulSoup(html_content, "html.parser")
        return soup.get_text(separator="\n", strip=True)

    def _get_item_by_href(self, book: epub.EpubBook, href: str) -> Optional[ebooklib.epub.EpubItem]:
        """Find an epub item by its href, ignoring fragment anchors."""
        # Strip fragment (e.g., part0005.html#lev001 -> part0005.html)
        base_href = href.split("#")[0]
        for item in book.get_items_of_type(ebooklib.ITEM_DOCUMENT):
            if item.get_name().endswith(base_href) or item.get_name() == base_href:
                return item
        return None

    def extract_chapters(self, epub_path: str) -> list[dict]:
        """
        Extract chapter structure from epub TOC.

        Returns list of chapter dicts with title, href, subsections, and text.
        """
        book = self._read_epub(epub_path)
        toc = book.toc
        chapters = []

        for item in toc:
            if isinstance(item, tuple):
                # Section with children: (Link, [children])
                section_link, children = item
                title = section_link.title
                href = section_link.href

                # Only include numbered chapters (skip Footnotes etc.)
                chapter_match = re.match(r"^(\d+)\s+", title)
                if not chapter_match:
                    continue

                chapter_num = int(chapter_match.group(1))

                # Extract subsections
                subsections = []
                for child in children:
                    if isinstance(child, tuple):
                        sub_link, _ = child
                        subsections.append({"title": sub_link.title, "href": sub_link.href})
                    else:
                        subsections.append({"title": child.title, "href": child.href})

                # Get chapter text
                doc_item = self._get_item_by_href(book, href)
                text = ""
                if doc_item:
                    text = self._extract_text_from_html(doc_item.get_content())

                chapters.append({
                    "chapter_number": chapter_num,
                    "title": title,
                    "href": href,
                    "subsections": subsections,
                    "text": text,
                    "text_length": len(text),
                })
            else:
                # Standalone link - check if it's a numbered chapter
                title = item.title
                chapter_match = re.match(r"^(\d+)\s+", title)
                if not chapter_match:
                    # Also check for Appendix
                    if title.lower().startswith("appendix"):
                        doc_item = self._get_item_by_href(book, item.href)
                        text = ""
                        if doc_item:
                            text = self._extract_text_from_html(doc_item.get_content())
                        chapters.append({
                            "chapter_number": len(chapters) + 1,
                            "title": title,
                            "href": item.href,
                            "subsections": [],
                            "text": text,
                            "text_length": len(text),
                        })
                    continue

                chapter_num = int(chapter_match.group(1))
                doc_item = self._get_item_by_href(book, item.href)
                text = ""
                if doc_item:
                    text = self._extract_text_from_html(doc_item.get_content())

                chapters.append({
                    "chapter_number": chapter_num,
                    "title": title,
                    "href": item.href,
                    "subsections": [],
                    "text": text,
                    "text_length": len(text),
                })

        return chapters

    async def extract_chapter_content(
        self,
        chapter_text: str,
        chapter_title: str,
    ) -> dict:
        """
        Use Gemini to analyze chapter content for language learning.

        Returns dict with summary, sections, key_concepts, case_studies.
        """
        if not self.configured:
            raise RuntimeError("Gemini API key not configured")

        # Truncate if needed
        text = chapter_text[: self.MAX_CONTENT_LENGTH]

        prompt = f"""Analyze this chapter from a French verb textbook and extract key information for language learning.

Chapter: "{chapter_title}"

Text:
{text}

Extract the following:
1. A 2-3 sentence summary of what this chapter covers (grammar topics, verb forms, etc.)
2. 8-12 key concepts that a French language learner should master from this chapter (verb tenses, conjugation patterns, grammar rules, key vocabulary)
3. Sections with their summaries and key points (focus on grammar rules and verb patterns)
4. Any important verb conjugation tables or patterns mentioned

IMPORTANT: Preserve all French text with proper accents and special characters (é, è, ê, ë, à, â, ç, ô, ù, û, ü, ï, î, etc.)

Format your response EXACTLY as JSON:
{{
  "title": "{chapter_title}",
  "summary": "2-3 sentence summary...",
  "key_concepts": ["concept1", "concept2", ...],
  "sections": [
    {{
      "title": "Section Name",
      "summary": "Brief summary of what this section teaches",
      "page_start": 0,
      "page_end": 0,
      "key_points": ["grammar rule 1", "conjugation pattern 1", ...]
    }}
  ],
  "case_studies": []
}}

Focus on content relevant to:
- French verb conjugation patterns
- Grammar rules and exceptions
- Tense usage and formation
- Common irregular verbs
- Practice exercise types covered
"""

        try:
            response = await asyncio.to_thread(self.model.generate_content, prompt)
            return self._parse_content_response(response.text, chapter_title)
        except Exception as e:
            print(f"Content extraction failed for '{chapter_title}': {e}")
            return {
                "title": chapter_title,
                "summary": f"Content extraction failed: {e}",
                "key_concepts": [],
                "sections": [],
                "case_studies": [],
            }

    def _parse_content_response(self, text: str, chapter_title: str) -> dict:
        """Parse Gemini's content extraction response."""
        try:
            json_match = re.search(r"\{[\s\S]*\}", text)
            if not json_match:
                raise ValueError("No JSON found in response")

            data = json.loads(json_match.group())

            # Normalize sections
            sections = []
            for s in data.get("sections", []):
                sections.append({
                    "title": s.get("title", ""),
                    "summary": s.get("summary"),
                    "page_start": s.get("page_start", 0),
                    "page_end": s.get("page_end", 0),
                    "key_points": s.get("key_points", []),
                })

            return {
                "title": data.get("title", chapter_title),
                "summary": data.get("summary", ""),
                "key_concepts": data.get("key_concepts", []),
                "sections": sections,
                "case_studies": data.get("case_studies", []),
            }
        except (json.JSONDecodeError, KeyError, ValueError) as e:
            print(f"Failed to parse content response for '{chapter_title}': {e}")
            return {
                "title": chapter_title,
                "summary": "Failed to parse content",
                "key_concepts": [],
                "sections": [],
                "case_studies": [],
            }

    async def ingest_book(
        self,
        epub_path: str,
        progress_callback: Optional[callable] = None,
    ) -> dict:
        """
        Full ingestion of an epub book.

        Returns a dict compatible with create_language_track_from_book()
        and save_book_content() in ingest_book.py:

        {
            "title": "...",
            "chapters": [{
                "chapter_number": 1,
                "title": "...",
                "summary": "...",
                "sections": [{"title", "key_points", "page_start", "page_end"}],
                "key_concepts": [...],
                "case_studies": [],
                "page_start": 0,
                "page_end": 0,
            }],
            "total_pages": 0,
        }
        """
        epub_path = str(Path(epub_path).resolve())

        if not Path(epub_path).exists():
            raise FileNotFoundError(f"EPUB not found: {epub_path}")

        if progress_callback:
            progress_callback("Starting epub ingestion...")

        # Pass 1: Extract structure from TOC
        if progress_callback:
            progress_callback("Pass 1: Extracting chapter structure from TOC...")

        chapters_info = self.extract_chapters(epub_path)

        if progress_callback:
            progress_callback(f"Found {len(chapters_info)} chapters")

        # Pass 2: Extract content from each chapter using Gemini
        if progress_callback:
            progress_callback("Pass 2: Extracting chapter content with AI...")

        chapters = []
        for i, ch_info in enumerate(chapters_info):
            if progress_callback:
                progress_callback(
                    f"Processing chapter {i + 1}/{len(chapters_info)}: {ch_info['title']}"
                )

            if ch_info.get("text"):
                content = await self.extract_chapter_content(
                    ch_info["text"],
                    ch_info["title"],
                )
            else:
                content = {
                    "title": ch_info["title"],
                    "summary": "No text content found for this chapter.",
                    "key_concepts": [],
                    "sections": [],
                    "case_studies": [],
                }

            chapters.append({
                "chapter_number": ch_info["chapter_number"],
                "title": content.get("title", ch_info["title"]),
                "summary": content.get("summary", ""),
                "sections": content.get("sections", []),
                "key_concepts": content.get("key_concepts", []),
                "case_studies": content.get("case_studies", []),
                "page_start": 0,
                "page_end": 0,
            })

        # Get book title from metadata
        book = self._read_epub(epub_path)
        title_meta = book.get_metadata("DC", "title")
        book_title = "The Ultimate French Verb Review and Practice"
        if title_meta:
            book_title = title_meta[0][0]

        result = {
            "title": book_title,
            "chapters": chapters,
            "total_pages": 0,  # Epubs don't have page numbers
        }

        if progress_callback:
            progress_callback(f"Ingestion complete: {len(chapters)} chapters extracted")

        return result


# Singleton instance
_epub_ingestion_service: Optional[EpubIngestionService] = None


def get_epub_ingestion_service() -> EpubIngestionService:
    """Get or create the EpubIngestionService singleton."""
    global _epub_ingestion_service
    if _epub_ingestion_service is None:
        _epub_ingestion_service = EpubIngestionService()
    return _epub_ingestion_service
