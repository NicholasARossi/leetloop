"""Book ingestion service for extracting structure and content from PDFs."""

import json
import re
from pathlib import Path
from typing import Optional

import fitz  # PyMuPDF
import google.generativeai as genai

from app.config import get_settings
from app.models.book_schemas import (
    BookStructure,
    CaseStudy,
    ChapterContent,
    ContentExtractionResult,
    PageChunk,
    SectionInfo,
    StructureDiscoveryResult,
)


class BookIngestionService:
    """
    Service for ingesting large PDF books into the system design review system.

    Uses a two-pass approach:
    1. Structure discovery: Quick scan to identify chapters, sections, case studies
    2. Content extraction: Detailed extraction of key concepts and summaries per chapter
    """

    # Chunk sizes for processing
    STRUCTURE_CHUNK_SIZE = 15  # Pages per chunk for structure discovery
    CONTENT_CHUNK_SIZE = 30   # Pages per chunk for content extraction

    def __init__(self):
        settings = get_settings()
        if settings.google_api_key:
            genai.configure(api_key=settings.google_api_key)
            self.model = genai.GenerativeModel(settings.gemini_model)
            self.configured = True
        else:
            self.model = None
            self.configured = False

    def extract_page_range(self, pdf_path: str, start: int, end: int) -> PageChunk:
        """
        Extract text from a range of pages.

        Args:
            pdf_path: Path to PDF file
            start: Start page (0-indexed)
            end: End page (exclusive)

        Returns:
            PageChunk with extracted text
        """
        doc = fitz.open(pdf_path)
        text_parts = []

        end = min(end, len(doc))
        for page_num in range(start, end):
            page = doc.load_page(page_num)
            text = page.get_text()
            text_parts.append(f"\n--- PAGE {page_num + 1} ---\n{text}")

        doc.close()

        return PageChunk(
            start_page=start + 1,  # Convert to 1-indexed
            end_page=end,
            text="\n".join(text_parts),
        )

    def get_total_pages(self, pdf_path: str) -> int:
        """Get total number of pages in PDF."""
        doc = fitz.open(pdf_path)
        total = len(doc)
        doc.close()
        return total

    def discover_structure_from_toc(self, pdf_path: str) -> list[dict]:
        """
        Extract book structure from PDF's built-in table of contents.

        This is faster and more reliable than AI-based discovery.

        Returns:
            List of chapter info dicts: [{title, page_start, page_end, sections}]
        """
        doc = fitz.open(pdf_path)
        toc = doc.get_toc()
        total_pages = len(doc)
        doc.close()

        if not toc:
            return []

        chapters = []
        current_chapter = None

        for entry in toc:
            level, title, page = entry

            # Level 1 entries are chapters (look for numbered chapters)
            if level == 1 and (title[0].isdigit() or title.startswith("Chapter")):
                # Save previous chapter
                if current_chapter:
                    chapters.append(current_chapter)

                current_chapter = {
                    "title": title,
                    "page_start": page,
                    "page_end": None,
                    "sections": [],
                }

            # Level 2+ entries are sections within current chapter
            elif current_chapter and level >= 2:
                current_chapter["sections"].append({
                    "title": title,
                    "page": page,
                    "level": level,
                })

        # Save last chapter
        if current_chapter:
            chapters.append(current_chapter)

        # Set page_end for each chapter (start of next chapter - 1)
        for i, chapter in enumerate(chapters):
            if i < len(chapters) - 1:
                chapter["page_end"] = chapters[i + 1]["page_start"] - 1
            else:
                chapter["page_end"] = total_pages

        return chapters

    async def discover_structure(
        self,
        pdf_path: str,
        progress_callback: Optional[callable] = None,
    ) -> list[dict]:
        """
        Pass 1: Discover book structure.

        First tries to use the PDF's built-in TOC. Falls back to AI-based
        discovery if TOC is not available.

        Args:
            pdf_path: Path to PDF file
            progress_callback: Optional callback for progress updates

        Returns:
            List of chapter info dicts: [{title, page_start, sections}]
        """
        # Try TOC first (faster and more reliable)
        if progress_callback:
            progress_callback("Checking for built-in table of contents...")

        chapters = self.discover_structure_from_toc(pdf_path)

        if chapters:
            if progress_callback:
                progress_callback(f"Found {len(chapters)} chapters from TOC")
            return chapters

        # Fallback to AI-based discovery
        if not self.configured:
            raise RuntimeError("Gemini API key not configured and no TOC available")

        if progress_callback:
            progress_callback("No TOC found, using AI-based structure discovery...")

        total_pages = self.get_total_pages(pdf_path)
        chapters = []
        current_chapter = None

        for start in range(0, total_pages, self.STRUCTURE_CHUNK_SIZE):
            end = min(start + self.STRUCTURE_CHUNK_SIZE, total_pages)

            if progress_callback:
                progress_callback(f"Scanning pages {start + 1}-{end} of {total_pages}...")

            chunk = self.extract_page_range(pdf_path, start, end)
            result = await self._identify_structure_in_chunk(
                chunk,
                [c["title"] for c in chapters],
            )

            # Merge discovered structure
            for ch in result.chapters_found:
                if current_chapter and ch.get("title") != current_chapter.get("title"):
                    # Close previous chapter
                    current_chapter["page_end"] = ch.get("page_start", start + 1) - 1
                    chapters.append(current_chapter)

                current_chapter = {
                    "title": ch.get("title"),
                    "page_start": ch.get("page_start", start + 1),
                    "page_end": None,
                    "sections": [],
                }

            # Add sections to current chapter
            if current_chapter:
                for sec in result.sections_found:
                    current_chapter["sections"].append({
                        "title": sec.get("title"),
                        "page": sec.get("page", start + 1),
                    })

        # Close final chapter
        if current_chapter:
            current_chapter["page_end"] = total_pages
            chapters.append(current_chapter)

        return chapters

    async def _identify_structure_in_chunk(
        self,
        chunk: PageChunk,
        previous_chapters: list[str],
    ) -> StructureDiscoveryResult:
        """Ask Gemini to identify structure in a text chunk."""
        prev_chapters_text = ", ".join(previous_chapters) if previous_chapters else "None found yet"

        prompt = f"""Analyze this section of a technical book about Machine Learning reliability and identify the structure.

Pages {chunk.start_page} to {chunk.end_page}:

{chunk.text[:50000]}  # Limit text size

Previously identified chapters: {prev_chapters_text}

Identify:
1. Any NEW chapter headings (not already listed above) with their page numbers
2. Section headings within chapters
3. Any case studies or real-world examples mentioned

Format your response EXACTLY as JSON:
{{
  "chapters_found": [
    {{"title": "Chapter Name", "page_start": 42}}
  ],
  "sections_found": [
    {{"chapter": "Parent Chapter", "title": "Section Name", "page": 45}}
  ],
  "case_studies_found": ["Case Study 1 name", "Case Study 2 name"]
}}

Only include NEWLY discovered chapters (not repeats). Return empty lists if nothing new found.
"""

        try:
            response = self.model.generate_content(prompt)
            return self._parse_structure_response(response.text)
        except Exception as e:
            print(f"Structure discovery failed for pages {chunk.start_page}-{chunk.end_page}: {e}")
            return StructureDiscoveryResult()

    def _parse_structure_response(self, text: str) -> StructureDiscoveryResult:
        """Parse Gemini's structure discovery response."""
        try:
            json_match = re.search(r'\{[\s\S]*\}', text)
            if not json_match:
                return StructureDiscoveryResult()

            data = json.loads(json_match.group())
            return StructureDiscoveryResult(
                chapters_found=data.get("chapters_found", []),
                sections_found=data.get("sections_found", []),
                case_studies_found=data.get("case_studies_found", []),
            )
        except (json.JSONDecodeError, KeyError) as e:
            print(f"Failed to parse structure response: {e}")
            return StructureDiscoveryResult()

    async def extract_chapter_content(
        self,
        pdf_path: str,
        chapter_info: dict,
        progress_callback: Optional[callable] = None,
    ) -> ChapterContent:
        """
        Pass 2: Extract detailed content from a chapter.

        Args:
            pdf_path: Path to PDF file
            chapter_info: Chapter info from structure discovery
            progress_callback: Optional callback for progress updates

        Returns:
            ChapterContent with summary, key concepts, case studies
        """
        if not self.configured:
            raise RuntimeError("Gemini API key not configured")

        start = chapter_info.get("page_start", 1) - 1  # Convert to 0-indexed
        end = chapter_info.get("page_end", start + 30)

        if progress_callback:
            progress_callback(f"Extracting content from '{chapter_info['title']}'...")

        # Extract chapter text (may need multiple chunks for large chapters)
        all_text = []
        for chunk_start in range(start, end, self.CONTENT_CHUNK_SIZE):
            chunk_end = min(chunk_start + self.CONTENT_CHUNK_SIZE, end)
            chunk = self.extract_page_range(pdf_path, chunk_start, chunk_end)
            all_text.append(chunk.text)

        full_text = "\n".join(all_text)

        # Use Gemini to extract content
        result = await self._extract_content_from_text(
            chapter_info["title"],
            full_text,
            (start + 1, end),
        )

        return ChapterContent(
            chapter_number=chapter_info.get("number", 0),
            title=chapter_info["title"],
            summary=result.summary,
            sections=[
                SectionInfo(
                    title=s.title,
                    summary=s.summary,
                    page_start=s.page_start,
                    page_end=s.page_end,
                    key_points=s.key_points,
                )
                for s in result.sections
            ],
            key_concepts=result.key_concepts,
            case_studies=[
                CaseStudy(
                    name=cs.name,
                    description=cs.description,
                    systems=cs.systems,
                )
                for cs in result.case_studies
            ],
            page_start=start + 1,
            page_end=end,
        )

    async def _extract_content_from_text(
        self,
        chapter_title: str,
        text: str,
        page_range: tuple[int, int],
    ) -> ContentExtractionResult:
        """Ask Gemini to extract detailed content from chapter text."""
        prompt = f"""Analyze this chapter from "Reliable Machine Learning" and extract key information for system design interview preparation.

Chapter: "{chapter_title}"
Pages: {page_range[0]} to {page_range[1]}

Text:
{text[:80000]}  # Limit for context window

Extract the following:
1. A 2-3 sentence summary of the chapter's main message
2. 8-12 key concepts that a senior ML engineer should understand from this chapter
3. Sections with their summaries and key points
4. Case studies or real-world examples with the systems/companies involved

Format your response EXACTLY as JSON:
{{
  "chapter_number": 0,
  "title": "{chapter_title}",
  "summary": "2-3 sentence summary...",
  "key_concepts": ["concept1", "concept2", ...],
  "sections": [
    {{
      "title": "Section Name",
      "summary": "Brief summary",
      "page_start": 10,
      "page_end": 15,
      "key_points": ["point1", "point2"]
    }}
  ],
  "case_studies": [
    {{
      "name": "Case Study Name",
      "description": "What the case study demonstrates",
      "systems": ["Google", "Netflix"]
    }}
  ]
}}

Focus on content relevant to:
- ML system reliability and robustness
- Production ML patterns and anti-patterns
- Failure modes and mitigation strategies
- Monitoring, testing, and validation
- Data quality and feature engineering
"""

        try:
            response = self.model.generate_content(prompt)
            return self._parse_content_response(response.text, chapter_title)
        except Exception as e:
            print(f"Content extraction failed for '{chapter_title}': {e}")
            return ContentExtractionResult(
                chapter_number=0,
                title=chapter_title,
                summary=f"Content extraction failed: {e}",
                key_concepts=[],
            )

    def _parse_content_response(
        self,
        text: str,
        chapter_title: str,
    ) -> ContentExtractionResult:
        """Parse Gemini's content extraction response."""
        try:
            json_match = re.search(r'\{[\s\S]*\}', text)
            if not json_match:
                raise ValueError("No JSON found")

            data = json.loads(json_match.group())

            sections = []
            for s in data.get("sections", []):
                sections.append(SectionInfo(
                    title=s.get("title", ""),
                    summary=s.get("summary"),
                    page_start=s.get("page_start", 0),
                    page_end=s.get("page_end", 0),
                    key_points=s.get("key_points", []),
                ))

            case_studies = []
            for cs in data.get("case_studies", []):
                case_studies.append(CaseStudy(
                    name=cs.get("name", ""),
                    description=cs.get("description", ""),
                    systems=cs.get("systems", []),
                ))

            return ContentExtractionResult(
                chapter_number=data.get("chapter_number", 0),
                title=data.get("title", chapter_title),
                summary=data.get("summary", ""),
                key_concepts=data.get("key_concepts", []),
                sections=sections,
                case_studies=case_studies,
            )
        except (json.JSONDecodeError, KeyError, ValueError) as e:
            print(f"Failed to parse content response: {e}")
            return ContentExtractionResult(
                chapter_number=0,
                title=chapter_title,
                summary="Failed to parse content",
                key_concepts=[],
            )

    async def ingest_book(
        self,
        pdf_path: str,
        progress_callback: Optional[callable] = None,
    ) -> BookStructure:
        """
        Full two-pass ingestion of a PDF book.

        Args:
            pdf_path: Path to PDF file
            progress_callback: Optional callback for progress updates

        Returns:
            Complete BookStructure with all chapters and content
        """
        pdf_path = str(Path(pdf_path).resolve())

        if not Path(pdf_path).exists():
            raise FileNotFoundError(f"PDF not found: {pdf_path}")

        total_pages = self.get_total_pages(pdf_path)

        if progress_callback:
            progress_callback(f"Starting ingestion of {total_pages}-page PDF...")

        # Pass 1: Discover structure
        if progress_callback:
            progress_callback("Pass 1: Discovering book structure...")

        chapters_info = await self.discover_structure(pdf_path, progress_callback)

        if progress_callback:
            progress_callback(f"Found {len(chapters_info)} chapters")

        # Number the chapters
        for i, ch in enumerate(chapters_info):
            ch["number"] = i + 1

        # Pass 2: Extract content from each chapter
        if progress_callback:
            progress_callback("Pass 2: Extracting chapter content...")

        chapters = []
        for ch_info in chapters_info:
            content = await self.extract_chapter_content(
                pdf_path,
                ch_info,
                progress_callback,
            )
            content.chapter_number = ch_info["number"]
            chapters.append(content)

        from datetime import datetime, timezone

        return BookStructure(
            title="Reliable Machine Learning",
            chapters=chapters,
            total_pages=total_pages,
            extracted_at=datetime.now(timezone.utc),
        )


# Singleton instance
_book_ingestion_service: Optional[BookIngestionService] = None


def get_book_ingestion_service() -> BookIngestionService:
    """Get or create the BookIngestionService singleton."""
    global _book_ingestion_service
    if _book_ingestion_service is None:
        _book_ingestion_service = BookIngestionService()
    return _book_ingestion_service
