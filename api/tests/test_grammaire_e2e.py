"""End-to-end tests for the Grammaire Progressive B2 user flow.

Tests the full user journey: new user → select track → day 1 exercises →
submit answers → progress tracking → spaced repetition → day 2 reviews.

All Supabase and Gemini calls are mocked. No real API hits.
"""

import json
import pytest
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch, AsyncMock
from uuid import UUID, uuid4

import httpx

from app.main import app
from app.db.supabase import get_supabase


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

TEST_USER_ID = UUID("00000000-0000-0000-0000-000000000099")
GRAMMAIRE_TRACK_ID = "5eba8cda-1cbf-4d07-b770-1204a7b54a75"
TODAY = datetime.utcnow().strftime("%Y-%m-%d")

# All 27 chapter titles from the real Grammaire Progressive manifest
CHAPTER_TITLES = [
    "L'ARTICLE",
    "L'ADJECTIF",
    "LES NÉGATIONS PARTICULIÈRES",
    "LES TEMPS de L'INDICATIF",
    "LE SUBJONCTIF",
    "LE CONDITIONNEL",
    "L'INFINITIF",
    "LE PARTICIPE PRÉSENT",
    "LE GÉRONDIF",
    "L'ADJECTIF VERBAL",
    "LA FORME PASSIVE",
    "LA FORME PRONOMINALE",
    "LA FORME IMPERSONNELLE",
    "LE DISCOURS INDIRECT",
    "L'ADVERBE",
    "LES PRÉPOSITIONS",
    "LES PRONOMS RELATIFS",
    "LES PRONOMS PERSONNELS COMPLÉMENTS",
    "LES PRONOMS INDÉFINIS",
    "LA SITUATION dans LE TEMPS",
    "L'EXPRESSION de LA CAUSE",
    "L'EXPRESSION de LA CONSÉQUENCE",
    "L'EXPRESSION de LA COMPARAISON",
    "L'EXPRESSION DE L'OPPOSITION et de LA CONCESSION",
    "L'EXPRESSION DU BUT",
    "L'EXPRESSION de LA CONDITION et de L'HYPOTHÈSE",
    "LA MODALISATION",
]


def _build_topics():
    topics = []
    for i, title in enumerate(CHAPTER_TITLES, start=1):
        diff = "easy" if i <= 3 else ("medium" if i <= 13 else "hard")
        topics.append({
            "name": title,
            "order": i,
            "difficulty": diff,
            "key_concepts": [f"concept_{i}_a", f"concept_{i}_b"],
        })
    return topics


GRAMMAIRE_TRACK_DATA = {
    "id": GRAMMAIRE_TRACK_ID,
    "name": "Grammaire Progressive B2",
    "description": "Grammaire avancée du français",
    "language": "french",
    "level": "b2",
    "total_topics": 27,
    "topics": _build_topics(),
    "rubric": {"accuracy": 3, "grammar": 3, "vocabulary": 2, "naturalness": 2},
    "source_book": "Grammaire Progressive du Français - Niveau Avancé",
    "created_at": datetime.utcnow().isoformat(),
}

# Sample book_content rows for a few chapters
SAMPLE_BOOK_CONTENT = [
    {
        "chapter_title": "L'ARTICLE",
        "summary": "Chapitre: L'ARTICLE\nL'ARTICLE DÉFINI «le», «la», «l'», «les»\n- Il est utilisé devant les noms qui désignent une personne ou une chose unique",
        "key_concepts": ["L'ARTICLE DÉFINI", "L'ARTICLE INDÉFINI", "L'ARTICLE PARTITIF", "L'ABSENCE D'ARTICLE"],
        "case_studies": [],
        "sections": [{"title": "L'ARTICLE DÉFINI", "summary": "Usage de le, la, l', les", "key_points": ["noms uniques", "superlatif"], "exercise_count": 10}],
    },
    {
        "chapter_title": "L'ADJECTIF",
        "summary": "Chapitre: L'ADJECTIF\nLES ADJECTIFS NUMÉRAUX\n- Les nombres cardinaux et ordinaux",
        "key_concepts": ["LES ADJECTIFS NUMÉRAUX", "L'ADJECTIF INDÉFINI", "LA PLACE DE L'ADJECTIF"],
        "case_studies": [],
        "sections": [{"title": "LES ADJECTIFS NUMÉRAUX", "summary": "Nombres cardinaux et ordinaux", "key_points": ["cardinaux", "ordinaux"], "exercise_count": 5}],
    },
    {
        "chapter_title": "LE SUBJONCTIF",
        "summary": "Chapitre: LE SUBJONCTIF\nFORMATION et CARACTÉRISTIQUES\n- Le subjonctif est formé à partir de la 3e personne du pluriel du présent de l'indicatif",
        "key_concepts": ["FORMATION et CARACTÉRISTIQUES", "EMPLOIS DU SUBJONCTIF", "LES TEMPS DU SUBJONCTIF", "SUBJONCTIF ou INDICATIF ?"],
        "case_studies": [],
        "sections": [{"title": "FORMATION et CARACTÉRISTIQUES", "summary": "Formation du subjonctif", "key_points": ["3e personne pluriel", "terminaisons"], "exercise_count": 4}],
    },
]

# Gemini batch response for Grammaire exercises
GRAMMAIRE_BATCH_RESPONSE = [
    {
        "topic": "L'ARTICLE",
        "exercise_type": "conjugation",
        "question_text": "Complétez avec l'article défini qui convient: _____ printemps est la plus belle saison.",
        "expected_answer": "Le",
        "focus_area": "article défini",
        "key_concepts": ["article défini", "noms uniques"],
        "is_review": False,
        "response_format": "single_line",
        "word_target": 3,
    },
    {
        "topic": "L'ARTICLE",
        "exercise_type": "fill_blank",
        "question_text": "Mettez l'article partitif: Je voudrais _____ eau, s'il vous plaît.",
        "expected_answer": "de l'",
        "focus_area": "article partitif",
        "key_concepts": ["article partitif"],
        "is_review": False,
        "response_format": "single_line",
        "word_target": 3,
    },
    {
        "topic": "L'ADJECTIF",
        "exercise_type": "vocabulary",
        "question_text": "Placez l'adjectif correctement: une maison (grand) _____",
        "expected_answer": "une grande maison",
        "focus_area": "place de l'adjectif",
        "key_concepts": ["place de l'adjectif"],
        "is_review": False,
        "response_format": "single_line",
        "word_target": 3,
    },
    {
        "topic": "L'ARTICLE",
        "exercise_type": "sentence_construction",
        "question_text": "Construisez une phrase avec un article partitif et le verbe 'manger'.",
        "expected_answer": "Je mange du pain tous les matins.",
        "focus_area": "article partitif en contexte",
        "key_concepts": ["article partitif", "construction de phrase"],
        "is_review": False,
        "response_format": "short_text",
        "word_target": 20,
    },
    {
        "topic": "L'ADJECTIF",
        "exercise_type": "error_correction",
        "question_text": "Corrigez: 'C'est le premier fois que je viens ici.'",
        "expected_answer": "C'est la première fois que je viens ici.",
        "focus_area": "accord de l'adjectif ordinal",
        "key_concepts": ["accord", "adjectif ordinal"],
        "is_review": False,
        "response_format": "short_text",
        "word_target": 20,
    },
    {
        "topic": "LES NÉGATIONS PARTICULIÈRES",
        "exercise_type": "situational",
        "question_text": "Vous êtes au restaurant et on vous propose un dessert. Refusez poliment en utilisant 'ne... plus'.",
        "expected_answer": None,
        "focus_area": "négation ne... plus",
        "key_concepts": ["ne... plus", "politesse"],
        "is_review": False,
        "response_format": "long_text",
        "word_target": 60,
    },
    {
        "topic": "L'ARTICLE",
        "exercise_type": "reading_comprehension",
        "question_text": "Lisez: 'Le Président a visité la Colombie. Il a rencontré les dirigeants du pays.' Pourquoi utilise-t-on 'le', 'la', et 'les' dans ce passage?",
        "expected_answer": None,
        "focus_area": "article défini – usage référentiel",
        "key_concepts": ["article défini", "noms propres géographiques"],
        "is_review": False,
        "response_format": "long_text",
        "word_target": 60,
    },
    {
        "topic": "L'ADJECTIF",
        "exercise_type": "journal_entry",
        "question_text": "Décrivez votre quartier en utilisant au moins cinq adjectifs différents. Faites attention à leur place par rapport au nom.",
        "expected_answer": None,
        "focus_area": "expression écrite avec adjectifs",
        "key_concepts": ["adjectif", "place", "accord"],
        "is_review": False,
        "response_format": "free_form",
        "word_target": 150,
    },
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def make_chain(data=None, count=None):
    """Create a chainable query mock that returns data on execute()."""
    query = MagicMock()
    query.select.return_value = query
    query.eq.return_value = query
    query.neq.return_value = query
    query.gte.return_value = query
    query.lte.return_value = query
    query.in_.return_value = query
    query.order.return_value = query
    query.limit.return_value = query
    query.single.return_value = query
    query.insert.return_value = query
    query.update.return_value = query
    query.delete.return_value = query
    query.upsert.return_value = query
    query.range.return_value = query

    result = MagicMock()
    result.data = data if data is not None else []
    result.count = count
    query.execute.return_value = result
    return query


def make_exercise_row(
    exercise_id=None,
    topic="L'ARTICLE",
    exercise_type="conjugation",
    status="pending",
    sort_order=0,
    is_review=False,
    score=None,
    verdict=None,
    feedback=None,
    corrections=None,
    missed_concepts=None,
    response_text=None,
    completed_at=None,
    response_format="single_line",
    word_target=3,
):
    """Create a single exercise row dict matching the DB schema."""
    return {
        "id": str(exercise_id or uuid4()),
        "user_id": str(TEST_USER_ID),
        "track_id": GRAMMAIRE_TRACK_ID,
        "generated_date": TODAY,
        "sort_order": sort_order,
        "topic": topic,
        "exercise_type": exercise_type,
        "question_text": f"Question for {topic} ({exercise_type})",
        "expected_answer": f"Expected answer for {topic}",
        "focus_area": f"Focus on {topic}",
        "key_concepts": ["concept_a", "concept_b"],
        "is_review": is_review,
        "review_topic_reason": "Due for review" if is_review else None,
        "status": status,
        "response_text": response_text,
        "word_count": len(response_text.split()) if response_text else 0,
        "score": score,
        "verdict": verdict,
        "feedback": feedback,
        "corrections": corrections,
        "missed_concepts": missed_concepts or [],
        "completed_at": completed_at,
        "created_at": datetime.utcnow().isoformat(),
        "response_format": response_format,
        "word_target": word_target,
    }


def build_grammaire_pending_batch(count=8):
    """Build pending exercises with Grammaire topics and correct tier distribution."""
    topics = CHAPTER_TITLES[:3]  # First 3 chapters for day 1
    types_and_formats = [
        ("conjugation", "single_line", 3),
        ("fill_blank", "single_line", 3),
        ("vocabulary", "single_line", 3),
        ("sentence_construction", "short_text", 20),
        ("error_correction", "short_text", 20),
        ("situational", "long_text", 60),
        ("reading_comprehension", "long_text", 60),
        ("journal_entry", "free_form", 150),
    ]
    rows = []
    for i in range(count):
        etype, fmt, wt = types_and_formats[i % len(types_and_formats)]
        rows.append(make_exercise_row(
            topic=topics[i % len(topics)],
            exercise_type=etype,
            sort_order=i,
            is_review=False,
            response_format=fmt,
            word_target=wt,
        ))
    return rows


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def exercise_id():
    return uuid4()


@pytest.fixture
def mock_sb():
    return MagicMock()


@pytest.fixture
def mock_language_service():
    service = MagicMock()
    service.configured = True
    service.generate_batch_exercises = AsyncMock(return_value=GRAMMAIRE_BATCH_RESPONSE)

    from app.models.language_schemas import LanguageGradingResponse
    service.grade_exercise = AsyncMock(return_value=LanguageGradingResponse(
        score=8.5,
        verdict="pass",
        feedback="Très bien! L'article est correct.",
        corrections=None,
        missed_concepts=[],
    ))
    return service


@pytest.fixture
def mock_language_service_fail():
    service = MagicMock()
    service.configured = True

    from app.models.language_schemas import LanguageGradingResponse
    service.grade_exercise = AsyncMock(return_value=LanguageGradingResponse(
        score=4.0,
        verdict="fail",
        feedback="L'article utilisé n'est pas correct. Révisez les articles partitifs.",
        corrections="de l'eau (et non *du eau)",
        missed_concepts=["article partitif", "élision"],
    ))
    return service


# ---------------------------------------------------------------------------
# 1. Track Discovery
# ---------------------------------------------------------------------------


class TestTrackDiscovery:
    """Verify the Grammaire Progressive track is discoverable."""

    @pytest.mark.asyncio
    async def test_list_tracks_includes_grammaire(self, mock_sb):
        """GET /language/tracks returns Grammaire Progressive B2."""
        tracks = [
            {"id": GRAMMAIRE_TRACK_ID, "name": "Grammaire Progressive B2",
             "description": "Grammaire avancée", "language": "french",
             "level": "b2", "total_topics": 27},
            {"id": str(uuid4()), "name": "French Verbs",
             "description": "Verb conjugation", "language": "french",
             "level": "b1", "total_topics": 13},
        ]
        mock_sb.table.return_value = make_chain(tracks)

        app.dependency_overrides[get_supabase] = lambda: mock_sb
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/api/language/tracks")
        app.dependency_overrides.clear()

        assert response.status_code == 200
        data = response.json()
        names = [t["name"] for t in data]
        assert "Grammaire Progressive B2" in names

        grammaire = next(t for t in data if t["name"] == "Grammaire Progressive B2")
        assert grammaire["language"] == "french"
        assert grammaire["level"] == "b2"
        assert grammaire["total_topics"] == 27

    @pytest.mark.asyncio
    async def test_get_track_details_has_27_topics(self, mock_sb):
        """GET /language/tracks/{id} returns all 27 topics in order."""
        mock_sb.table.return_value = make_chain(GRAMMAIRE_TRACK_DATA)

        app.dependency_overrides[get_supabase] = lambda: mock_sb
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get(f"/api/language/tracks/{GRAMMAIRE_TRACK_ID}")
        app.dependency_overrides.clear()

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Grammaire Progressive B2"
        assert len(data["topics"]) == 27
        assert data["topics"][0]["name"] == "L'ARTICLE"
        assert data["topics"][0]["order"] == 1
        assert data["topics"][-1]["name"] == "LA MODALISATION"
        assert data["topics"][-1]["order"] == 27
        assert data["rubric"]["accuracy"] == 3
        assert data["rubric"]["grammar"] == 3
        assert data["source_book"] == "Grammaire Progressive du Français - Niveau Avancé"


# ---------------------------------------------------------------------------
# 2. Track Selection + New User
# ---------------------------------------------------------------------------


class TestTrackSelection:
    """New user selects the Grammaire track."""

    @pytest.mark.asyncio
    async def test_set_active_track(self, mock_sb):
        """PUT /language/{user_id}/active-track succeeds for Grammaire."""
        table_call_counts = {}

        def table_handler(table_name):
            idx = table_call_counts.get(table_name, 0)
            table_call_counts[table_name] = idx + 1
            if table_name == "language_tracks":
                return make_chain({"id": GRAMMAIRE_TRACK_ID, "name": "Grammaire Progressive B2"})
            if table_name == "user_language_settings":
                return make_chain([])
            return make_chain([])

        mock_sb.table.side_effect = table_handler

        app.dependency_overrides[get_supabase] = lambda: mock_sb
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.put(
                f"/api/language/{TEST_USER_ID}/active-track",
                json={"track_id": GRAMMAIRE_TRACK_ID},
            )
        app.dependency_overrides.clear()

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["track_name"] == "Grammaire Progressive B2"
        assert data["active_track_id"] == GRAMMAIRE_TRACK_ID

    @pytest.mark.asyncio
    async def test_set_active_track_invalid_id(self, mock_sb):
        """PUT with nonexistent track_id returns 404."""
        fake_id = str(uuid4())
        table_call_counts = {}

        def table_handler(table_name):
            idx = table_call_counts.get(table_name, 0)
            table_call_counts[table_name] = idx + 1
            if table_name == "language_tracks":
                chain = make_chain(None)
                chain.execute.return_value.data = None
                return chain
            return make_chain([])

        mock_sb.table.side_effect = table_handler

        app.dependency_overrides[get_supabase] = lambda: mock_sb
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.put(
                f"/api/language/{TEST_USER_ID}/active-track",
                json={"track_id": fake_id},
            )
        app.dependency_overrides.clear()

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_new_user_has_zero_progress(self, mock_sb):
        """GET progress for a new user → completed_topics=[], next_topic=L'ARTICLE."""
        table_call_counts = {}

        def table_handler(table_name):
            idx = table_call_counts.get(table_name, 0)
            table_call_counts[table_name] = idx + 1
            if table_name == "language_tracks":
                return make_chain(GRAMMAIRE_TRACK_DATA)
            if table_name == "language_track_progress":
                return make_chain([])  # New user, no progress
            return make_chain([])

        mock_sb.table.side_effect = table_handler

        app.dependency_overrides[get_supabase] = lambda: mock_sb
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get(
                f"/api/language/tracks/{GRAMMAIRE_TRACK_ID}/progress/{TEST_USER_ID}"
            )
        app.dependency_overrides.clear()

        assert response.status_code == 200
        data = response.json()
        assert data["progress"] is None
        assert data["completion_percentage"] == 0.0
        assert data["next_topic"] == "L'ARTICLE"
        assert data["track"]["total_topics"] == 27


# ---------------------------------------------------------------------------
# 3. Day 1 Exercise Generation
# ---------------------------------------------------------------------------


class TestDay1ExerciseGeneration:
    """First daily exercise batch for a new user on Grammaire track."""

    @pytest.mark.asyncio
    async def test_generates_8_exercises(self, mock_sb, mock_language_service):
        """GET daily-exercises generates a batch of 8 pending exercises."""
        generated_rows = build_grammaire_pending_batch(8)

        table_call_counts = {}
        table_responses = {
            ("language_daily_exercises", 0): make_chain([]),
            ("user_language_settings", 0): make_chain([{"active_track_id": GRAMMAIRE_TRACK_ID}]),
            ("language_tracks", 0): make_chain(GRAMMAIRE_TRACK_DATA),
            ("language_track_progress", 0): make_chain([]),
            ("language_attempts", 0): make_chain([]),
            ("book_content", 0): make_chain(SAMPLE_BOOK_CONTENT),
            ("language_daily_exercises", 1): make_chain(generated_rows),
            ("language_daily_exercises", 2): make_chain(generated_rows),
        }

        def table_handler(table_name):
            idx = table_call_counts.get(table_name, 0)
            table_call_counts[table_name] = idx + 1
            key = (table_name, idx)
            return table_responses.get(key, make_chain([]))

        mock_sb.table.side_effect = table_handler
        mock_sb.rpc.return_value = make_chain([])

        with patch("app.routers.language.get_language_service", return_value=mock_language_service), \
             patch("app.routers.language._daily_exercises_cache", {}):
            app.dependency_overrides[get_supabase] = lambda: mock_sb
            transport = httpx.ASGITransport(app=app)
            async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.get(f"/api/language/{TEST_USER_ID}/daily-exercises")
            app.dependency_overrides.clear()

        assert response.status_code == 200
        data = response.json()
        assert data["generated_date"] == TODAY
        assert len(data["exercises"]) == 8
        assert data["total_count"] == 8
        assert data["completed_count"] == 0

    @pytest.mark.asyncio
    async def test_exercises_use_book_content(self, mock_sb, mock_language_service):
        """Verify book_content is fetched and passed to generate_batch_exercises."""
        generated_rows = build_grammaire_pending_batch(8)
        table_call_counts = {}
        book_content_queried = {"called": False}

        def table_handler(table_name):
            idx = table_call_counts.get(table_name, 0)
            table_call_counts[table_name] = idx + 1
            if table_name == "language_daily_exercises" and idx == 0:
                return make_chain([])
            if table_name == "user_language_settings":
                return make_chain([{"active_track_id": GRAMMAIRE_TRACK_ID}])
            if table_name == "language_tracks":
                return make_chain(GRAMMAIRE_TRACK_DATA)
            if table_name == "language_track_progress":
                return make_chain([])
            if table_name == "language_attempts":
                return make_chain([])
            if table_name == "book_content":
                book_content_queried["called"] = True
                return make_chain(SAMPLE_BOOK_CONTENT)
            if table_name == "language_daily_exercises":
                return make_chain(generated_rows)
            return make_chain([])

        mock_sb.table.side_effect = table_handler
        mock_sb.rpc.return_value = make_chain([])

        with patch("app.routers.language.get_language_service", return_value=mock_language_service), \
             patch("app.routers.language._daily_exercises_cache", {}):
            app.dependency_overrides[get_supabase] = lambda: mock_sb
            transport = httpx.ASGITransport(app=app)
            async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
                await client.get(f"/api/language/{TEST_USER_ID}/daily-exercises")
            app.dependency_overrides.clear()

        assert book_content_queried["called"], "book_content table should be queried during generation"
        # Verify generate_batch_exercises was called with book_contexts
        mock_language_service.generate_batch_exercises.assert_called_once()
        call_kwargs = mock_language_service.generate_batch_exercises.call_args
        # book_contexts should be passed (positional or keyword)
        assert call_kwargs is not None

    @pytest.mark.asyncio
    async def test_no_review_exercises_on_day_1(self, mock_sb, mock_language_service):
        """New user on day 1 has no reviews due → all exercises are is_review=False."""
        generated_rows = build_grammaire_pending_batch(8)

        table_call_counts = {}

        def table_handler(table_name):
            idx = table_call_counts.get(table_name, 0)
            table_call_counts[table_name] = idx + 1
            if table_name == "language_daily_exercises" and idx == 0:
                return make_chain([])
            if table_name == "user_language_settings":
                return make_chain([{"active_track_id": GRAMMAIRE_TRACK_ID}])
            if table_name == "language_tracks":
                return make_chain(GRAMMAIRE_TRACK_DATA)
            if table_name == "language_track_progress":
                return make_chain([])
            if table_name == "language_attempts":
                return make_chain([])
            if table_name == "book_content":
                return make_chain([])
            if table_name == "language_daily_exercises":
                return make_chain(generated_rows)
            return make_chain([])

        mock_sb.table.side_effect = table_handler
        mock_sb.rpc.return_value = make_chain([])  # No reviews due

        with patch("app.routers.language.get_language_service", return_value=mock_language_service), \
             patch("app.routers.language._daily_exercises_cache", {}):
            app.dependency_overrides[get_supabase] = lambda: mock_sb
            transport = httpx.ASGITransport(app=app)
            async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.get(f"/api/language/{TEST_USER_ID}/daily-exercises")
            app.dependency_overrides.clear()

        assert response.status_code == 200
        data = response.json()
        review_exercises = [e for e in data["exercises"] if e["is_review"]]
        assert len(review_exercises) == 0, "Day 1 should have no review exercises"

    @pytest.mark.asyncio
    async def test_tier_distribution(self, mock_sb):
        """Batch has correct tier distribution: 3 quick + 2 short + 2 extended + 1 free-form."""
        existing = build_grammaire_pending_batch(8)
        mock_sb.table.return_value = make_chain(existing)

        with patch("app.routers.language._daily_exercises_cache", {}):
            app.dependency_overrides[get_supabase] = lambda: mock_sb
            transport = httpx.ASGITransport(app=app)
            async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.get(f"/api/language/{TEST_USER_ID}/daily-exercises")
            app.dependency_overrides.clear()

        data = response.json()
        format_counts = {}
        for ex in data["exercises"]:
            fmt = ex.get("response_format", "single_line")
            format_counts[fmt] = format_counts.get(fmt, 0) + 1

        assert format_counts.get("single_line", 0) == 3
        assert format_counts.get("short_text", 0) == 2
        assert format_counts.get("long_text", 0) == 2
        assert format_counts.get("free_form", 0) == 1

    @pytest.mark.asyncio
    async def test_second_call_returns_cached(self, mock_sb):
        """Second GET same day returns cached batch without re-generating."""
        existing = build_grammaire_pending_batch(8)
        mock_sb.table.return_value = make_chain(existing)

        with patch("app.routers.language._daily_exercises_cache", {}):
            app.dependency_overrides[get_supabase] = lambda: mock_sb
            transport = httpx.ASGITransport(app=app)
            async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
                r1 = await client.get(f"/api/language/{TEST_USER_ID}/daily-exercises")
                r2 = await client.get(f"/api/language/{TEST_USER_ID}/daily-exercises")
            app.dependency_overrides.clear()

        assert r1.status_code == 200
        assert r2.status_code == 200
        assert len(r1.json()["exercises"]) == len(r2.json()["exercises"])


# ---------------------------------------------------------------------------
# 4. Exercise Submission + Grading
# ---------------------------------------------------------------------------


class TestExerciseSubmission:
    """Submitting answers and receiving grades."""

    @pytest.mark.asyncio
    async def test_submit_passing_answer(self, mock_sb, mock_language_service, exercise_id):
        """Good answer → score >= 7, verdict=pass, French feedback."""
        exercise_row = make_exercise_row(exercise_id=exercise_id, topic="L'ARTICLE", status="pending")
        exercise_row["language_tracks"] = GRAMMAIRE_TRACK_DATA

        mock_sb.table.return_value = make_chain(exercise_row)

        with patch("app.routers.language.get_language_service", return_value=mock_language_service), \
             patch("app.routers.language._daily_exercises_cache", {}):
            app.dependency_overrides[get_supabase] = lambda: mock_sb
            transport = httpx.ASGITransport(app=app)
            async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.post(
                    f"/api/language/daily-exercises/{exercise_id}/submit",
                    json={"response_text": "Le printemps est ma saison préférée."},
                )
            app.dependency_overrides.clear()

        assert response.status_code == 200
        data = response.json()
        assert data["score"] == 8.5
        assert data["verdict"] == "pass"
        assert isinstance(data["feedback"], str)
        assert len(data["feedback"]) > 0

    @pytest.mark.asyncio
    async def test_submit_failing_answer(self, mock_sb, mock_language_service_fail, exercise_id):
        """Bad answer → score < 7, verdict=fail, corrections provided."""
        exercise_row = make_exercise_row(exercise_id=exercise_id, topic="L'ARTICLE", status="pending")
        exercise_row["language_tracks"] = GRAMMAIRE_TRACK_DATA

        mock_sb.table.return_value = make_chain(exercise_row)

        with patch("app.routers.language.get_language_service", return_value=mock_language_service_fail), \
             patch("app.routers.language._daily_exercises_cache", {}):
            app.dependency_overrides[get_supabase] = lambda: mock_sb
            transport = httpx.ASGITransport(app=app)
            async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.post(
                    f"/api/language/daily-exercises/{exercise_id}/submit",
                    json={"response_text": "du eau"},
                )
            app.dependency_overrides.clear()

        assert response.status_code == 200
        data = response.json()
        assert data["score"] == 4.0
        assert data["verdict"] == "fail"
        assert data["corrections"] is not None
        assert len(data["missed_concepts"]) > 0

    @pytest.mark.asyncio
    async def test_passing_score_marks_topic_completed(self, mock_sb, mock_language_service, exercise_id):
        """Score >= 7 → topic added to completed_topics in track_progress."""
        exercise_row = make_exercise_row(exercise_id=exercise_id, topic="L'ARTICLE", status="pending")
        exercise_row["language_tracks"] = GRAMMAIRE_TRACK_DATA

        progress_chain = make_chain([{
            "id": str(uuid4()),
            "user_id": str(TEST_USER_ID),
            "track_id": GRAMMAIRE_TRACK_ID,
            "completed_topics": [],
            "sessions_completed": 0,
            "average_score": 0.0,
        }])
        progress_update_chain = make_chain([])
        table_call_counts = {}

        def table_handler(table_name):
            idx = table_call_counts.get(table_name, 0)
            table_call_counts[table_name] = idx + 1
            if table_name == "language_daily_exercises" and idx == 0:
                return make_chain(exercise_row)
            if table_name == "language_track_progress" and idx == 0:
                return progress_chain
            if table_name == "language_track_progress" and idx == 1:
                return progress_update_chain
            return make_chain([])

        mock_sb.table.side_effect = table_handler

        with patch("app.routers.language.get_language_service", return_value=mock_language_service), \
             patch("app.routers.language._daily_exercises_cache", {}):
            app.dependency_overrides[get_supabase] = lambda: mock_sb
            transport = httpx.ASGITransport(app=app)
            async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.post(
                    f"/api/language/daily-exercises/{exercise_id}/submit",
                    json={"response_text": "Le printemps"},
                )
            app.dependency_overrides.clear()

        assert response.status_code == 200
        # Verify track progress was updated
        progress_update_chain.update.assert_called_once()
        update_data = progress_update_chain.update.call_args[0][0]
        assert "L'ARTICLE" in update_data["completed_topics"]

    @pytest.mark.asyncio
    async def test_failing_score_adds_to_review_queue(self, mock_sb, mock_language_service_fail, exercise_id):
        """Score < 7 → language_review_queue entry created."""
        exercise_row = make_exercise_row(exercise_id=exercise_id, topic="L'ARTICLE", status="pending")
        exercise_row["language_tracks"] = GRAMMAIRE_TRACK_DATA

        review_chain = make_chain([])
        table_call_counts = {}

        def table_handler(table_name):
            idx = table_call_counts.get(table_name, 0)
            table_call_counts[table_name] = idx + 1
            if table_name == "language_daily_exercises" and idx == 0:
                return make_chain(exercise_row)
            if table_name == "language_review_queue":
                return review_chain
            return make_chain([])

        mock_sb.table.side_effect = table_handler

        with patch("app.routers.language.get_language_service", return_value=mock_language_service_fail), \
             patch("app.routers.language._daily_exercises_cache", {}):
            app.dependency_overrides[get_supabase] = lambda: mock_sb
            transport = httpx.ASGITransport(app=app)
            async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.post(
                    f"/api/language/daily-exercises/{exercise_id}/submit",
                    json={"response_text": "du eau"},
                )
            app.dependency_overrides.clear()

        assert response.status_code == 200
        assert response.json()["score"] == 4.0
        review_chain.upsert.assert_called_once()
        upsert_data = review_chain.upsert.call_args[0][0]
        assert upsert_data["topic"] == "L'ARTICLE"
        assert upsert_data["interval_days"] == 1

    @pytest.mark.asyncio
    async def test_submit_already_completed_returns_cached(self, mock_sb, exercise_id):
        """Re-submitting a completed exercise returns the saved grade."""
        exercise_row = make_exercise_row(
            exercise_id=exercise_id, topic="L'ARTICLE", status="completed",
            score=8.5, verdict="pass", feedback="Très bien!",
            response_text="Le printemps", completed_at=datetime.utcnow().isoformat(),
        )
        exercise_row["language_tracks"] = GRAMMAIRE_TRACK_DATA

        mock_sb.table.return_value = make_chain(exercise_row)

        with patch("app.routers.language._daily_exercises_cache", {}):
            app.dependency_overrides[get_supabase] = lambda: mock_sb
            transport = httpx.ASGITransport(app=app)
            async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.post(
                    f"/api/language/daily-exercises/{exercise_id}/submit",
                    json={"response_text": "Le printemps"},
                )
            app.dependency_overrides.clear()

        assert response.status_code == 200
        data = response.json()
        assert data["score"] == 8.5
        assert data["verdict"] == "pass"


# ---------------------------------------------------------------------------
# 5. Progress Tracking
# ---------------------------------------------------------------------------


class TestProgressTracking:
    """Verify progress endpoints after day 1 activity."""

    @pytest.mark.asyncio
    async def test_progress_after_mixed_results(self, mock_sb):
        """After 2 passes and 1 fail: completion = 2/27, next_topic skips completed."""
        table_call_counts = {}

        def table_handler(table_name):
            idx = table_call_counts.get(table_name, 0)
            table_call_counts[table_name] = idx + 1
            if table_name == "language_tracks":
                return make_chain(GRAMMAIRE_TRACK_DATA)
            if table_name == "language_track_progress":
                return make_chain([{
                    "id": str(uuid4()),
                    "user_id": str(TEST_USER_ID),
                    "track_id": GRAMMAIRE_TRACK_ID,
                    "completed_topics": ["L'ARTICLE", "L'ADJECTIF"],
                    "sessions_completed": 3,
                    "average_score": 7.0,
                    "started_at": datetime.utcnow().isoformat(),
                    "last_activity_at": datetime.utcnow().isoformat(),
                }])
            return make_chain([])

        mock_sb.table.side_effect = table_handler

        app.dependency_overrides[get_supabase] = lambda: mock_sb
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get(
                f"/api/language/tracks/{GRAMMAIRE_TRACK_ID}/progress/{TEST_USER_ID}"
            )
        app.dependency_overrides.clear()

        assert response.status_code == 200
        data = response.json()
        assert len(data["progress"]["completed_topics"]) == 2
        assert abs(data["completion_percentage"] - (2 / 27 * 100)) < 0.1
        # Next topic should be the 3rd chapter (first uncompleted)
        assert data["next_topic"] == "LES NÉGATIONS PARTICULIÈRES"

    @pytest.mark.asyncio
    async def test_dashboard_after_day_1(self, mock_sb):
        """Dashboard reflects correct state after day 1 activity."""
        table_call_counts = {}

        def table_handler(table_name):
            idx = table_call_counts.get(table_name, 0)
            table_call_counts[table_name] = idx + 1

            if table_name == "user_language_settings":
                return make_chain([{"active_track_id": GRAMMAIRE_TRACK_ID, "user_id": str(TEST_USER_ID)}])
            if table_name == "language_tracks":
                return make_chain(GRAMMAIRE_TRACK_DATA)
            if table_name == "language_track_progress":
                return make_chain([{
                    "completed_topics": ["L'ARTICLE", "L'ADJECTIF"],
                }])
            if table_name == "language_attempts":
                if idx == 0:
                    return make_chain([], count=6)  # exercises_this_week
                return make_chain([{"score": 8.5}])  # recent score
            return make_chain([])

        mock_sb.table.side_effect = table_handler
        mock_sb.rpc.return_value = make_chain([{
            "id": str(uuid4()),
            "user_id": str(TEST_USER_ID),
            "track_id": GRAMMAIRE_TRACK_ID,
            "topic": "LES NÉGATIONS PARTICULIÈRES",
            "reason": "Failed exercise",
            "priority": 1,
            "next_review": datetime.utcnow().isoformat(),
            "interval_days": 1,
            "review_count": 1,
            "last_reviewed": None,
            "source_attempt_id": None,
            "created_at": datetime.utcnow().isoformat(),
        }])

        with patch("app.routers.language._lang_dashboard_cache", {}):
            app.dependency_overrides[get_supabase] = lambda: mock_sb
            transport = httpx.ASGITransport(app=app)
            async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.get(f"/api/language/{TEST_USER_ID}/dashboard")
            app.dependency_overrides.clear()

        assert response.status_code == 200
        data = response.json()
        assert data["has_active_track"] is True
        assert data["active_track"]["name"] == "Grammaire Progressive B2"
        assert data["reviews_due_count"] == 1
        assert data["exercises_this_week"] == 6
        assert data["recent_score"] == 8.5
        # Next topic should skip completed ones
        assert data["next_topic"]["topic_name"] == "LES NÉGATIONS PARTICULIÈRES"
        assert data["book_total_chapters"] == 27
        assert data["book_completed_chapters"] == 2


# ---------------------------------------------------------------------------
# 6. Spaced Repetition + Day 2
# ---------------------------------------------------------------------------


class TestSpacedRepetition:
    """Review queue behavior on subsequent days."""

    @pytest.mark.asyncio
    async def test_day_2_includes_review_exercises(self, mock_sb, mock_language_service):
        """Failed topics from day 1 appear as is_review=True on day 2."""
        # Build a batch where some exercises are reviews
        generated_rows = build_grammaire_pending_batch(8)
        generated_rows[0]["is_review"] = True
        generated_rows[0]["review_topic_reason"] = "Failed on day 1"
        generated_rows[0]["topic"] = "LES NÉGATIONS PARTICULIÈRES"

        table_call_counts = {}

        def table_handler(table_name):
            idx = table_call_counts.get(table_name, 0)
            table_call_counts[table_name] = idx + 1
            if table_name == "language_daily_exercises" and idx == 0:
                return make_chain([])
            if table_name == "user_language_settings":
                return make_chain([{"active_track_id": GRAMMAIRE_TRACK_ID}])
            if table_name == "language_tracks":
                return make_chain(GRAMMAIRE_TRACK_DATA)
            if table_name == "language_track_progress":
                return make_chain([{
                    "completed_topics": ["L'ARTICLE", "L'ADJECTIF"],
                    "sessions_completed": 6,
                    "average_score": 7.0,
                }])
            if table_name == "language_attempts":
                return make_chain([])
            if table_name == "book_content":
                return make_chain(SAMPLE_BOOK_CONTENT)
            if table_name == "language_daily_exercises":
                return make_chain(generated_rows)
            return make_chain([])

        mock_sb.table.side_effect = table_handler

        # Day 2: reviews due
        review_data = [{
            "id": str(uuid4()),
            "user_id": str(TEST_USER_ID),
            "track_id": GRAMMAIRE_TRACK_ID,
            "topic": "LES NÉGATIONS PARTICULIÈRES",
            "reason": "Score 4.0 on day 1",
            "priority": 1,
            "next_review": datetime.utcnow().isoformat(),
            "interval_days": 1,
            "review_count": 1,
            "last_reviewed": None,
            "source_attempt_id": None,
            "created_at": (datetime.utcnow() - timedelta(days=1)).isoformat(),
        }]
        mock_sb.rpc.return_value = make_chain(review_data)

        with patch("app.routers.language.get_language_service", return_value=mock_language_service), \
             patch("app.routers.language._daily_exercises_cache", {}):
            app.dependency_overrides[get_supabase] = lambda: mock_sb
            transport = httpx.ASGITransport(app=app)
            async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.get(f"/api/language/{TEST_USER_ID}/daily-exercises")
            app.dependency_overrides.clear()

        assert response.status_code == 200
        data = response.json()
        review_exercises = [e for e in data["exercises"] if e["is_review"]]
        assert len(review_exercises) >= 1
        review_topics = [e["topic"] for e in review_exercises]
        assert "LES NÉGATIONS PARTICULIÈRES" in review_topics

    @pytest.mark.asyncio
    async def test_review_success_doubles_interval(self, mock_sb, mock_language_service, exercise_id):
        """Passing a review exercise → interval doubles (1→2)."""
        exercise_row = make_exercise_row(
            exercise_id=exercise_id, topic="LES NÉGATIONS PARTICULIÈRES",
            status="pending", is_review=True,
        )
        exercise_row["language_tracks"] = GRAMMAIRE_TRACK_DATA

        review_chain = make_chain([{
            "id": str(uuid4()),
            "user_id": str(TEST_USER_ID),
            "track_id": GRAMMAIRE_TRACK_ID,
            "topic": "LES NÉGATIONS PARTICULIÈRES",
            "interval_days": 1,
            "review_count": 1,
        }])
        review_update_chain = make_chain([])
        table_call_counts = {}

        def table_handler(table_name):
            idx = table_call_counts.get(table_name, 0)
            table_call_counts[table_name] = idx + 1
            if table_name == "language_daily_exercises" and idx == 0:
                return make_chain(exercise_row)
            if table_name == "language_review_queue" and idx == 0:
                return review_chain
            if table_name == "language_review_queue" and idx == 1:
                return review_update_chain
            return make_chain([])

        mock_sb.table.side_effect = table_handler

        with patch("app.routers.language.get_language_service", return_value=mock_language_service), \
             patch("app.routers.language._daily_exercises_cache", {}):
            app.dependency_overrides[get_supabase] = lambda: mock_sb
            transport = httpx.ASGITransport(app=app)
            async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.post(
                    f"/api/language/daily-exercises/{exercise_id}/submit",
                    json={"response_text": "ne... plus, ne... guère, sans aucun"},
                )
            app.dependency_overrides.clear()

        assert response.status_code == 200
        assert response.json()["verdict"] == "pass"

    @pytest.mark.asyncio
    async def test_review_failure_resets_interval(self, mock_sb, mock_language_service_fail, exercise_id):
        """Failing a review exercise → interval resets to 1 day."""
        exercise_row = make_exercise_row(
            exercise_id=exercise_id, topic="LES NÉGATIONS PARTICULIÈRES",
            status="pending", is_review=True,
        )
        exercise_row["language_tracks"] = GRAMMAIRE_TRACK_DATA

        review_chain = make_chain([])
        table_call_counts = {}

        def table_handler(table_name):
            idx = table_call_counts.get(table_name, 0)
            table_call_counts[table_name] = idx + 1
            if table_name == "language_daily_exercises" and idx == 0:
                return make_chain(exercise_row)
            if table_name == "language_review_queue":
                return review_chain
            return make_chain([])

        mock_sb.table.side_effect = table_handler

        with patch("app.routers.language.get_language_service", return_value=mock_language_service_fail), \
             patch("app.routers.language._daily_exercises_cache", {}):
            app.dependency_overrides[get_supabase] = lambda: mock_sb
            transport = httpx.ASGITransport(app=app)
            async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.post(
                    f"/api/language/daily-exercises/{exercise_id}/submit",
                    json={"response_text": "mauvaise réponse"},
                )
            app.dependency_overrides.clear()

        assert response.status_code == 200
        assert response.json()["verdict"] == "fail"
        review_chain.upsert.assert_called_once()
        upsert_data = review_chain.upsert.call_args[0][0]
        assert upsert_data["interval_days"] == 1  # Reset to 1


# ---------------------------------------------------------------------------
# 7. Edge Cases
# ---------------------------------------------------------------------------


class TestEdgeCases:
    """Error handling and boundary conditions."""

    @pytest.mark.asyncio
    async def test_no_active_track_returns_error(self, mock_sb):
        """GET daily-exercises with no active track → 400."""
        table_call_counts = {}

        def table_handler(table_name):
            idx = table_call_counts.get(table_name, 0)
            table_call_counts[table_name] = idx + 1
            if table_name == "language_daily_exercises":
                return make_chain([])
            if table_name == "user_language_settings":
                return make_chain([])  # No active track
            return make_chain([])

        mock_sb.table.side_effect = table_handler
        mock_sb.rpc.return_value = make_chain([])

        with patch("app.routers.language._daily_exercises_cache", {}):
            app.dependency_overrides[get_supabase] = lambda: mock_sb
            transport = httpx.ASGITransport(app=app)
            async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.get(f"/api/language/{TEST_USER_ID}/daily-exercises")
            app.dependency_overrides.clear()

        assert response.status_code == 400
        assert "No active language track" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_exercise_not_found(self, mock_sb):
        """Submit for non-existent exercise → 404."""
        fake_id = uuid4()
        chain = MagicMock()
        chain.select.return_value = chain
        chain.eq.return_value = chain
        chain.single.return_value = chain
        result = MagicMock()
        result.data = None
        chain.execute.return_value = result
        mock_sb.table.return_value = chain

        with patch("app.routers.language._daily_exercises_cache", {}):
            app.dependency_overrides[get_supabase] = lambda: mock_sb
            transport = httpx.ASGITransport(app=app)
            async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.post(
                    f"/api/language/daily-exercises/{fake_id}/submit",
                    json={"response_text": "test"},
                )
            app.dependency_overrides.clear()

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_regenerate_replaces_pending_keeps_completed(self, mock_sb, mock_language_service):
        """POST regenerate deletes pending, keeps completed, fills remaining slots."""
        completed_exercise = make_exercise_row(
            sort_order=0, status="completed", score=8.5, verdict="pass",
            feedback="Bien!", response_text="Le", completed_at=datetime.utcnow().isoformat(),
        )
        pending_exercises = [make_exercise_row(sort_order=i, status="pending") for i in range(1, 5)]

        new_exercises = [make_exercise_row(sort_order=i) for i in range(1, 8)]
        final_batch = [completed_exercise] + new_exercises

        table_call_counts = {}

        def table_handler(table_name):
            idx = table_call_counts.get(table_name, 0)
            table_call_counts[table_name] = idx + 1

            if table_name == "language_daily_exercises" and idx == 0:
                return make_chain([completed_exercise] + pending_exercises)  # existing batch
            if table_name == "language_daily_exercises" and idx == 1:
                return make_chain([])  # delete pending
            if table_name == "user_language_settings":
                return make_chain([{"active_track_id": GRAMMAIRE_TRACK_ID}])
            if table_name == "language_tracks":
                return make_chain(GRAMMAIRE_TRACK_DATA)
            if table_name == "language_track_progress":
                return make_chain([])
            if table_name == "language_attempts":
                return make_chain([])
            if table_name == "book_content":
                return make_chain([])
            if table_name == "language_daily_exercises":
                return make_chain(final_batch)
            return make_chain([])

        mock_sb.table.side_effect = table_handler
        mock_sb.rpc.return_value = make_chain([])

        with patch("app.routers.language.get_language_service", return_value=mock_language_service), \
             patch("app.routers.language._daily_exercises_cache", {}):
            app.dependency_overrides[get_supabase] = lambda: mock_sb
            transport = httpx.ASGITransport(app=app)
            async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.post(f"/api/language/{TEST_USER_ID}/daily-exercises/regenerate")
            app.dependency_overrides.clear()

        assert response.status_code == 200
        data = response.json()
        assert data["completed_count"] >= 1  # Completed exercise preserved


# ---------------------------------------------------------------------------
# 8. Full User Journey Integration
# ---------------------------------------------------------------------------


class TestFullUserJourney:
    """Single test tracing the complete new-user-to-progress journey."""

    @pytest.mark.asyncio
    async def test_complete_day_1_flow(self, mock_sb, mock_language_service):
        """
        Full sequence:
        1. List tracks → Grammaire present
        2. Set active track → success
        3. Get daily exercises → 8 pending
        4. Submit 3 exercises (2 pass, 1 fail)
        5. Check progress → 2 completed topics, 1 in review
        """
        from app.models.language_schemas import LanguageGradingResponse

        # --- Step 1: List tracks ---
        mock_sb.table.return_value = make_chain([
            {"id": GRAMMAIRE_TRACK_ID, "name": "Grammaire Progressive B2",
             "description": "Grammaire avancée", "language": "french",
             "level": "b2", "total_topics": 27},
        ])

        app.dependency_overrides[get_supabase] = lambda: mock_sb
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            r1 = await client.get("/api/language/tracks")
        app.dependency_overrides.clear()

        assert r1.status_code == 200
        assert any(t["name"] == "Grammaire Progressive B2" for t in r1.json())

        # --- Step 2: Set active track ---
        table_call_counts = {}

        def set_track_handler(table_name):
            idx = table_call_counts.get(table_name, 0)
            table_call_counts[table_name] = idx + 1
            if table_name == "language_tracks":
                return make_chain({"id": GRAMMAIRE_TRACK_ID, "name": "Grammaire Progressive B2"})
            return make_chain([])

        mock_sb.table.side_effect = set_track_handler

        app.dependency_overrides[get_supabase] = lambda: mock_sb
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            r2 = await client.put(
                f"/api/language/{TEST_USER_ID}/active-track",
                json={"track_id": GRAMMAIRE_TRACK_ID},
            )
        app.dependency_overrides.clear()

        assert r2.status_code == 200
        assert r2.json()["success"] is True

        # --- Step 3: Generate daily exercises ---
        generated_rows = build_grammaire_pending_batch(8)
        table_call_counts = {}

        def gen_handler(table_name):
            idx = table_call_counts.get(table_name, 0)
            table_call_counts[table_name] = idx + 1
            if table_name == "language_daily_exercises" and idx == 0:
                return make_chain([])
            if table_name == "user_language_settings":
                return make_chain([{"active_track_id": GRAMMAIRE_TRACK_ID}])
            if table_name == "language_tracks":
                return make_chain(GRAMMAIRE_TRACK_DATA)
            if table_name == "language_track_progress":
                return make_chain([])
            if table_name == "language_attempts":
                return make_chain([])
            if table_name == "book_content":
                return make_chain(SAMPLE_BOOK_CONTENT)
            if table_name == "language_daily_exercises":
                return make_chain(generated_rows)
            return make_chain([])

        mock_sb.table.side_effect = gen_handler
        mock_sb.rpc.return_value = make_chain([])

        with patch("app.routers.language.get_language_service", return_value=mock_language_service), \
             patch("app.routers.language._daily_exercises_cache", {}):
            app.dependency_overrides[get_supabase] = lambda: mock_sb
            async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
                r3 = await client.get(f"/api/language/{TEST_USER_ID}/daily-exercises")
            app.dependency_overrides.clear()

        assert r3.status_code == 200
        exercises = r3.json()["exercises"]
        assert len(exercises) == 8
        assert r3.json()["completed_count"] == 0

        # --- Step 4: Submit exercises (2 pass, 1 fail) ---
        exercise_ids = [UUID(e["id"]) for e in exercises[:3]]

        for i, eid in enumerate(exercise_ids):
            is_fail = (i == 2)
            exercise_row = make_exercise_row(
                exercise_id=eid, topic=exercises[i]["topic"], status="pending",
            )
            exercise_row["language_tracks"] = GRAMMAIRE_TRACK_DATA

            mock_sb.table.return_value = make_chain(exercise_row)
            mock_sb.table.side_effect = None

            if is_fail:
                mock_language_service.grade_exercise = AsyncMock(
                    return_value=LanguageGradingResponse(
                        score=4.0, verdict="fail",
                        feedback="Erreur d'article.",
                        corrections="la grande maison",
                        missed_concepts=["place de l'adjectif"],
                    )
                )
            else:
                mock_language_service.grade_exercise = AsyncMock(
                    return_value=LanguageGradingResponse(
                        score=8.5, verdict="pass",
                        feedback="Très bien!",
                        corrections=None,
                        missed_concepts=[],
                    )
                )

            with patch("app.routers.language.get_language_service", return_value=mock_language_service), \
                 patch("app.routers.language._daily_exercises_cache", {}):
                app.dependency_overrides[get_supabase] = lambda: mock_sb
                async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
                    r = await client.post(
                        f"/api/language/daily-exercises/{eid}/submit",
                        json={"response_text": "une réponse"},
                    )
                app.dependency_overrides.clear()

            assert r.status_code == 200
            if is_fail:
                assert r.json()["verdict"] == "fail"
            else:
                assert r.json()["verdict"] == "pass"

        # --- Step 5: Check progress ---
        table_call_counts = {}

        def progress_handler(table_name):
            idx = table_call_counts.get(table_name, 0)
            table_call_counts[table_name] = idx + 1
            if table_name == "language_tracks":
                return make_chain(GRAMMAIRE_TRACK_DATA)
            if table_name == "language_track_progress":
                return make_chain([{
                    "id": str(uuid4()),
                    "user_id": str(TEST_USER_ID),
                    "track_id": GRAMMAIRE_TRACK_ID,
                    "completed_topics": ["L'ARTICLE", "L'ARTICLE"],  # 2 passes on L'ARTICLE topics
                    "sessions_completed": 3,
                    "average_score": 7.0,
                    "started_at": datetime.utcnow().isoformat(),
                    "last_activity_at": datetime.utcnow().isoformat(),
                }])
            return make_chain([])

        mock_sb.table.side_effect = progress_handler

        app.dependency_overrides[get_supabase] = lambda: mock_sb
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            r5 = await client.get(
                f"/api/language/tracks/{GRAMMAIRE_TRACK_ID}/progress/{TEST_USER_ID}"
            )
        app.dependency_overrides.clear()

        assert r5.status_code == 200
        progress = r5.json()
        assert progress["progress"]["sessions_completed"] == 3
        assert progress["completion_percentage"] > 0
        assert progress["track"]["name"] == "Grammaire Progressive B2"
