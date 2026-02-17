"""Tests for the epub ingestion pipeline.

Covers:
1. Unit tests for EpubIngestionService (read, extract, unicode, errors)
2. Integration test for ingest_book output format (mocked Gemini)
3. Content extraction with mocked Gemini responses
"""

import json
import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch, AsyncMock

from app.services.epub_ingestion_service import EpubIngestionService


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

EPUB_PATH = next(
    Path(__file__).resolve().parent.parent.parent.glob("*.epub"), None
)


@pytest.fixture
def epub_path():
    """Path to the real epub file at the repo root."""
    assert EPUB_PATH is not None, "No .epub file found at repo root"
    return str(EPUB_PATH)


@pytest.fixture
def service():
    """EpubIngestionService with Gemini disabled (no API key needed)."""
    with patch("app.services.epub_ingestion_service.get_settings") as mock_settings:
        settings = MagicMock()
        settings.google_api_key = None
        settings.gemini_model = "gemini-3-flash-preview"
        mock_settings.return_value = settings
        svc = EpubIngestionService()
    assert not svc.configured  # Gemini should be off
    return svc


@pytest.fixture
def configured_service():
    """EpubIngestionService with a mocked Gemini model."""
    with patch("app.services.epub_ingestion_service.get_settings") as mock_settings, \
         patch("app.services.epub_ingestion_service.genai") as mock_genai:
        settings = MagicMock()
        settings.google_api_key = "fake-key"
        settings.gemini_model = "gemini-3-flash-preview"
        mock_settings.return_value = settings
        svc = EpubIngestionService()
    assert svc.configured
    return svc


@pytest.fixture
def gemini_chapter_response():
    """A valid Gemini JSON response for chapter content extraction."""
    return json.dumps({
        "title": "1 The present tense of regular verbs",
        "summary": "This chapter covers the conjugation of regular French verbs in the present tense across three groups: -er, -ir, and -re verbs.",
        "key_concepts": [
            "Present tense conjugation of -er verbs",
            "Present tense conjugation of -ir verbs",
            "Present tense conjugation of -re verbs",
            "Subject pronouns (je, tu, il/elle, nous, vous, ils/elles)",
            "Verb stems and endings",
            "Élision with je → j'",
        ],
        "sections": [
            {
                "title": "Regular -er verbs",
                "summary": "Conjugation patterns for the largest group of French verbs.",
                "page_start": 0,
                "page_end": 0,
                "key_points": [
                    "Drop -er, add: -e, -es, -e, -ons, -ez, -ent",
                    "Examples: parler, aimer, travailler",
                ],
            },
            {
                "title": "Regular -ir verbs",
                "summary": "Conjugation patterns for -ir verbs like finir.",
                "page_start": 0,
                "page_end": 0,
                "key_points": [
                    "Drop -ir, add: -is, -is, -it, -issons, -issez, -issent",
                ],
            },
        ],
        "case_studies": [],
    })


# ---------------------------------------------------------------------------
# 1. Unit tests for EpubIngestionService
# ---------------------------------------------------------------------------

class TestReadEpub:
    """Test epub file reading."""

    def test_read_epub_opens_file(self, service, epub_path):
        """Can open the real epub file and return an EpubBook."""
        from ebooklib.epub import EpubBook

        book = service._read_epub(epub_path)
        assert isinstance(book, EpubBook)

    def test_missing_epub_raises(self, service):
        """FileNotFoundError for a non-existent epub."""
        with pytest.raises(Exception):
            service._read_epub("/nonexistent/fake_book.epub")


class TestExtractChapters:
    """Test chapter extraction from the epub TOC."""

    def test_extract_chapters_returns_chapters(self, service, epub_path):
        """Returns a non-empty list of chapter dicts."""
        chapters = service.extract_chapters(epub_path)
        assert isinstance(chapters, list)
        assert len(chapters) > 0

    def test_chapter_has_required_fields(self, service, epub_path):
        """Each chapter has chapter_number, title, and text."""
        chapters = service.extract_chapters(epub_path)
        for ch in chapters:
            assert "chapter_number" in ch, f"Missing chapter_number in {ch.get('title')}"
            assert "title" in ch, f"Missing title in chapter {ch.get('chapter_number')}"
            assert "text" in ch, f"Missing text in chapter {ch.get('chapter_number')}"
            assert isinstance(ch["chapter_number"], int)
            assert isinstance(ch["title"], str)
            assert len(ch["title"]) > 0

    def test_chapters_have_text_content(self, service, epub_path):
        """At least some chapters contain extracted text."""
        chapters = service.extract_chapters(epub_path)
        chapters_with_text = [ch for ch in chapters if ch.get("text")]
        assert len(chapters_with_text) > 0, "No chapters have text content"

    def test_french_unicode_preserved(self, service, epub_path):
        """French accents (é, è, ê, ç, etc.) are preserved in extracted text."""
        chapters = service.extract_chapters(epub_path)
        all_text = " ".join(ch.get("text", "") for ch in chapters)

        # The French verb book must contain accented characters
        french_chars = set("éèêëàâçôùûüïî")
        found = {c for c in all_text if c in french_chars}
        assert len(found) >= 3, (
            f"Expected several French accent characters, found only: {found}"
        )


class TestExtractTextFromHtml:
    """Test HTML to plain-text conversion."""

    def test_extract_text_from_html(self, service):
        """HTML content is properly converted to clean text."""
        html = b"<html><body><h1>Chapitre 1</h1><p>Les verbes r\xc3\xa9guliers</p></body></html>"
        text = service._extract_text_from_html(html)
        assert "Chapitre 1" in text
        assert "Les verbes réguliers" in text
        # No HTML tags in output
        assert "<" not in text
        assert ">" not in text

    def test_extract_text_preserves_unicode(self, service):
        """Unicode characters survive HTML extraction."""
        html = "être, français, garçon, naïf, Noël".encode("utf-8")
        html_wrapped = b"<p>" + html + b"</p>"
        text = service._extract_text_from_html(html_wrapped)
        assert "être" in text
        assert "français" in text
        assert "garçon" in text
        assert "naïf" in text
        assert "Noël" in text


# ---------------------------------------------------------------------------
# 2. Content extraction with mocked Gemini
# ---------------------------------------------------------------------------

class TestExtractChapterContent:
    """Test Gemini-based content extraction (mocked)."""

    @pytest.mark.asyncio
    async def test_extract_chapter_content_parses_response(
        self, configured_service, gemini_chapter_response
    ):
        """Properly parses a valid Gemini JSON response."""
        mock_response = MagicMock()
        mock_response.text = gemini_chapter_response
        configured_service.model.generate_content = MagicMock(return_value=mock_response)

        result = await configured_service.extract_chapter_content(
            chapter_text="Sample chapter text about regular verbs.",
            chapter_title="1 The present tense of regular verbs",
        )

        assert result["title"] == "1 The present tense of regular verbs"
        assert "conjugation" in result["summary"].lower() or "present tense" in result["summary"].lower()
        assert isinstance(result["key_concepts"], list)
        assert len(result["key_concepts"]) >= 3
        assert isinstance(result["sections"], list)
        assert len(result["sections"]) == 2
        assert result["sections"][0]["title"] == "Regular -er verbs"
        assert isinstance(result["case_studies"], list)

    @pytest.mark.asyncio
    async def test_extract_chapter_content_handles_bad_json(self, configured_service):
        """Falls back gracefully when Gemini returns invalid JSON."""
        mock_response = MagicMock()
        mock_response.text = "This is not valid JSON at all!"
        configured_service.model.generate_content = MagicMock(return_value=mock_response)

        result = await configured_service.extract_chapter_content(
            chapter_text="Sample text",
            chapter_title="Bad Chapter",
        )

        # Should return fallback dict, not raise
        assert result["title"] == "Bad Chapter"
        assert isinstance(result["key_concepts"], list)
        assert isinstance(result["sections"], list)

    @pytest.mark.asyncio
    async def test_extract_chapter_content_handles_exception(self, configured_service):
        """Falls back gracefully when Gemini raises an exception."""
        configured_service.model.generate_content = MagicMock(
            side_effect=RuntimeError("API quota exceeded")
        )

        result = await configured_service.extract_chapter_content(
            chapter_text="Sample text",
            chapter_title="Error Chapter",
        )

        assert result["title"] == "Error Chapter"
        assert "failed" in result["summary"].lower() or "error" in result["summary"].lower() or "quota" in result["summary"].lower()

    @pytest.mark.asyncio
    async def test_unconfigured_service_raises(self, service):
        """RuntimeError when Gemini is not configured."""
        with pytest.raises(RuntimeError, match="not configured"):
            await service.extract_chapter_content("text", "title")


# ---------------------------------------------------------------------------
# 3. Integration test for ingest_book output format
# ---------------------------------------------------------------------------

class TestIngestBookOutput:
    """Test that ingest_book returns dict compatible with DB save functions."""

    @pytest.mark.asyncio
    async def test_ingest_book_returns_compatible_dict(
        self, configured_service, epub_path, gemini_chapter_response
    ):
        """Mock Gemini, verify the returned dict has the right structure."""
        mock_response = MagicMock()
        mock_response.text = gemini_chapter_response
        configured_service.model.generate_content = MagicMock(return_value=mock_response)

        result = await configured_service.ingest_book(epub_path)

        # Top-level keys required by create_language_track_from_book()
        assert "title" in result
        assert "chapters" in result
        assert "total_pages" in result
        assert isinstance(result["title"], str)
        assert len(result["title"]) > 0
        assert isinstance(result["chapters"], list)
        assert len(result["chapters"]) > 0

        # Each chapter must have fields used by save_book_content()
        for ch in result["chapters"]:
            assert "chapter_number" in ch
            assert "title" in ch
            assert "summary" in ch
            assert "sections" in ch
            assert "key_concepts" in ch
            assert "case_studies" in ch
            assert "page_start" in ch
            assert "page_end" in ch

            assert isinstance(ch["chapter_number"], int)
            assert isinstance(ch["title"], str)
            assert isinstance(ch["sections"], list)
            assert isinstance(ch["key_concepts"], list)
            assert isinstance(ch["case_studies"], list)

    @pytest.mark.asyncio
    async def test_ingest_book_missing_file_raises(self, configured_service):
        """FileNotFoundError for a non-existent epub."""
        with pytest.raises(FileNotFoundError, match="EPUB not found"):
            await configured_service.ingest_book("/nonexistent/book.epub")

    @pytest.mark.asyncio
    async def test_ingest_book_calls_progress_callback(
        self, configured_service, epub_path, gemini_chapter_response
    ):
        """Progress callback is invoked during ingestion."""
        mock_response = MagicMock()
        mock_response.text = gemini_chapter_response
        configured_service.model.generate_content = MagicMock(return_value=mock_response)

        messages = []
        await configured_service.ingest_book(epub_path, progress_callback=messages.append)

        assert len(messages) > 0
        assert any("chapter" in m.lower() for m in messages)


class TestParseContentResponse:
    """Test the internal _parse_content_response helper."""

    def test_parses_valid_json(self, service):
        """Extracts structured data from valid JSON text."""
        text = json.dumps({
            "title": "Test Chapter",
            "summary": "A summary",
            "key_concepts": ["concept1"],
            "sections": [
                {"title": "Sec 1", "summary": "s", "page_start": 0, "page_end": 0, "key_points": ["p1"]}
            ],
            "case_studies": [],
        })
        result = service._parse_content_response(text, "Test Chapter")
        assert result["title"] == "Test Chapter"
        assert result["summary"] == "A summary"
        assert result["key_concepts"] == ["concept1"]
        assert len(result["sections"]) == 1

    def test_parses_json_with_markdown_wrapper(self, service):
        """Handles JSON wrapped in markdown code fences."""
        text = '```json\n{"title": "Ch", "summary": "s", "key_concepts": [], "sections": [], "case_studies": []}\n```'
        result = service._parse_content_response(text, "Ch")
        assert result["title"] == "Ch"

    def test_returns_fallback_on_invalid_json(self, service):
        """Returns fallback dict when JSON is unparseable."""
        result = service._parse_content_response("not json", "Fallback")
        assert result["title"] == "Fallback"
        assert result["key_concepts"] == []
        assert result["sections"] == []
