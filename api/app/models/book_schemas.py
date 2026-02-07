"""Pydantic schemas for book content ingestion."""

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field


# ============ Section/Chapter Structure ============


class SectionInfo(BaseModel):
    """A section within a book chapter."""

    title: str
    summary: Optional[str] = None
    page_start: int
    page_end: int
    key_points: list[str] = []


class CaseStudy(BaseModel):
    """A case study extracted from a book."""

    name: str
    description: str
    systems: list[str] = []  # Real-world systems mentioned
    page: Optional[int] = None


class ChapterContent(BaseModel):
    """Extracted content from a book chapter."""

    chapter_number: int
    title: str
    summary: Optional[str] = None
    sections: list[SectionInfo] = []
    key_concepts: list[str] = []
    case_studies: list[CaseStudy] = []
    page_start: int
    page_end: int


class BookStructure(BaseModel):
    """Full structure of an ingested book."""

    title: str
    chapters: list[ChapterContent] = []
    total_pages: int = 0
    extracted_at: Optional[datetime] = None


# ============ Database Models ============


class BookContentRecord(BaseModel):
    """A book content record as stored in the database."""

    id: UUID
    book_title: str
    chapter_number: int
    chapter_title: str
    sections: list[SectionInfo] = []
    key_concepts: list[str] = []
    case_studies: list[CaseStudy] = []
    summary: Optional[str] = None
    page_start: int
    page_end: int
    created_at: datetime
    track_id: Optional[UUID] = None  # Link to created track


# ============ Ingestion Models ============


class PageChunk(BaseModel):
    """A chunk of pages for processing."""

    start_page: int
    end_page: int
    text: str


class StructureDiscoveryResult(BaseModel):
    """Result from structure discovery pass."""

    chapters_found: list[dict] = []  # [{title, page_start, page_end}]
    sections_found: list[dict] = []  # [{chapter, title, page}]
    case_studies_found: list[str] = []


class ContentExtractionResult(BaseModel):
    """Result from content extraction for a chapter."""

    chapter_number: int
    title: str
    summary: str
    key_concepts: list[str] = Field(default=[], max_length=15)
    sections: list[SectionInfo] = []
    case_studies: list[CaseStudy] = []


# ============ Gemini Prompts Context ============


class GeminiStructureContext(BaseModel):
    """Context for Gemini structure discovery."""

    text_chunk: str
    page_range: tuple[int, int]
    previous_chapters: list[str] = []  # Already discovered chapters


class GeminiContentContext(BaseModel):
    """Context for Gemini content extraction."""

    chapter_title: str
    chapter_text: str
    page_range: tuple[int, int]


# ============ Track Creation ============


class CreateTrackFromBookRequest(BaseModel):
    """Request to create a system design track from book content."""

    book_title: str
    track_name: str
    track_type: str = "mle"  # Default to MLE for ML books
    chapters: list[ChapterContent] = []


class TopicFromChapter(BaseModel):
    """A topic derived from a book chapter."""

    name: str  # Chapter title
    order: int  # Chapter number
    difficulty: str = "medium"
    example_systems: list[str] = []  # From case studies
    key_concepts: list[str] = []  # For question generation
    source_chapter: int
