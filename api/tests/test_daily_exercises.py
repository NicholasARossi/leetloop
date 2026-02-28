"""Tests for the daily exercise endpoints.

Covers:
1. GET /language/{user_id}/daily-exercises - generation, caching, structure
2. POST /language/daily-exercises/{exercise_id}/submit - grading, review queue
3. POST /language/{user_id}/daily-exercises/regenerate - regeneration logic
4. Edge cases - Gemini failures, no active track, etc.
5. Tier distribution - response_format, word_target, tier mix
"""

import json
import pytest
from datetime import datetime
from unittest.mock import MagicMock, patch, AsyncMock
from uuid import UUID, uuid4

import httpx

from app.main import app
from app.db.supabase import get_supabase


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

TEST_USER_ID = UUID("00000000-0000-0000-0000-000000000001")
TEST_TRACK_ID = "22222222-2222-2222-2222-222222222222"
TODAY = datetime.utcnow().strftime("%Y-%m-%d")

SAMPLE_TRACK_DATA = {
    "id": TEST_TRACK_ID,
    "name": "French Verbs",
    "description": "French verb conjugation",
    "language": "french",
    "level": "b1",
    "total_topics": 3,
    "topics": [
        {"name": "Present Tense", "order": 1, "difficulty": "easy", "key_concepts": ["conjugation", "-er verbs"]},
        {"name": "Past Tense", "order": 2, "difficulty": "medium", "key_concepts": ["passé composé", "auxiliaire"]},
        {"name": "Future Tense", "order": 3, "difficulty": "medium", "key_concepts": ["futur simple", "futur proche"]},
    ],
    "rubric": {"accuracy": 3, "grammar": 3, "vocabulary": 2, "naturalness": 2},
}

SAMPLE_GEMINI_BATCH_RESPONSE = json.dumps([
    {
        "topic": "Present Tense",
        "exercise_type": "conjugation",
        "question_text": "Conjuguez le verbe 'parler' au présent pour toutes les personnes.",
        "expected_answer": "je parle, tu parles, il parle, nous parlons, vous parlez, ils parlent",
        "focus_area": "conjugaison régulière -er",
        "key_concepts": ["conjugation", "-er verbs"],
        "is_review": False,
        "response_format": "single_line",
        "word_target": 3,
    },
    {
        "topic": "Past Tense",
        "exercise_type": "fill_blank",
        "question_text": "Hier, nous ___ (aller) au marché.",
        "expected_answer": "sommes allés",
        "focus_area": "passé composé avec être",
        "key_concepts": ["passé composé", "auxiliaire être"],
        "is_review": False,
        "response_format": "single_line",
        "word_target": 3,
    },
    {
        "topic": "Future Tense",
        "exercise_type": "vocabulary",
        "question_text": "Utilisez 'demain' dans une phrase au futur.",
        "expected_answer": "Demain, j'irai au cinéma.",
        "focus_area": "futur simple",
        "key_concepts": ["futur simple", "futur proche"],
        "is_review": False,
        "response_format": "single_line",
        "word_target": 3,
    },
    {
        "topic": "Present Tense",
        "exercise_type": "sentence_construction",
        "question_text": "Construisez une phrase avec le subjonctif et 'il faut que'.",
        "expected_answer": "Il faut que je fasse mes devoirs.",
        "focus_area": "subjonctif présent",
        "key_concepts": ["subjonctif", "expressions de nécessité"],
        "is_review": True,
        "response_format": "short_text",
        "word_target": 20,
    },
    {
        "topic": "Past Tense",
        "exercise_type": "error_correction",
        "question_text": "Corrigez: 'Les fleurs que j'ai acheté sont très belle.'",
        "expected_answer": "Les fleurs que j'ai achetées sont très belles.",
        "focus_area": "accord du participe passé",
        "key_concepts": ["accord", "participe passé"],
        "is_review": False,
        "response_format": "short_text",
        "word_target": 20,
    },
    {
        "topic": "Future Tense",
        "exercise_type": "situational",
        "question_text": "Vous êtes dans un hôtel. Votre chambre a un problème. Expliquez à la réception.",
        "expected_answer": None,
        "focus_area": "conditionnel + politesse",
        "key_concepts": ["conditionnel", "politesse"],
        "is_review": False,
        "response_format": "long_text",
        "word_target": 60,
    },
    {
        "topic": "Present Tense",
        "exercise_type": "reading_comprehension",
        "question_text": "Marie habite à Lyon depuis cinq ans. Chaque matin, elle prend le tramway. Hier, le tramway était en panne. Pourquoi Marie a-t-elle pris le bus ?",
        "expected_answer": None,
        "focus_area": "compréhension écrite",
        "key_concepts": ["compréhension", "passé composé"],
        "is_review": True,
        "response_format": "long_text",
        "word_target": 60,
    },
    {
        "topic": "Past Tense",
        "exercise_type": "journal_entry",
        "question_text": "Racontez un souvenir d'enfance qui vous a marqué. Utilisez l'imparfait et le passé composé.",
        "expected_answer": None,
        "focus_area": "expression écrite libre",
        "key_concepts": ["imparfait", "passé composé", "connecteurs"],
        "is_review": False,
        "response_format": "free_form",
        "word_target": 150,
    },
])

SAMPLE_GRADING_RESPONSE = json.dumps({
    "score": 8.5,
    "verdict": "pass",
    "feedback": "Très bien! Votre conjugaison est correcte.",
    "corrections": None,
    "missed_concepts": [],
})

SAMPLE_GRADING_RESPONSE_FAIL = json.dumps({
    "score": 4.0,
    "verdict": "fail",
    "feedback": "Il y a plusieurs erreurs de conjugaison.",
    "corrections": "je parle, tu parles, il parle",
    "missed_concepts": ["conjugation", "-er verbs"],
})


# ---------------------------------------------------------------------------
# Helper: create mock supabase with chainable queries
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
    topic="Present Tense",
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
):
    """Create a single exercise row dict matching the DB schema."""
    return {
        "id": str(exercise_id or uuid4()),
        "user_id": str(TEST_USER_ID),
        "track_id": TEST_TRACK_ID,
        "generated_date": TODAY,
        "sort_order": sort_order,
        "topic": topic,
        "exercise_type": exercise_type,
        "question_text": f"Question for {topic} ({exercise_type})",
        "expected_answer": f"Expected answer for {topic}",
        "focus_area": f"Focus on {topic}",
        "key_concepts": ["concept1", "concept2"],
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
    }


def build_pending_batch(count=8):
    """Build a list of pending exercise rows with tier-aware types."""
    topics = ["Present Tense", "Past Tense", "Future Tense"]
    # Tier-aware sequence: 3 quick, 2 short, 2 extended, 1 free-form
    types = [
        "conjugation", "fill_blank", "vocabulary",         # quick
        "sentence_construction", "error_correction",        # short
        "situational", "reading_comprehension",             # extended
        "journal_entry",                                    # free-form
    ]
    rows = []
    for i in range(count):
        rows.append(make_exercise_row(
            topic=topics[i % len(topics)],
            exercise_type=types[i % len(types)],
            sort_order=i,
            is_review=(i == 3 or i == 7),
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
    """Base mock Supabase client."""
    return MagicMock()


@pytest.fixture
def mock_language_service():
    """Mock LanguageService with controlled generate_batch_exercises and grade_exercise."""
    service = MagicMock()
    service.configured = True

    # Default batch generation response
    batch_data = json.loads(SAMPLE_GEMINI_BATCH_RESPONSE)
    service.generate_batch_exercises = AsyncMock(return_value=batch_data)

    # Default grading response
    from app.models.language_schemas import LanguageGradingResponse
    service.grade_exercise = AsyncMock(return_value=LanguageGradingResponse(
        score=8.5,
        verdict="pass",
        feedback="Très bien! Votre conjugaison est correcte.",
        corrections=None,
        missed_concepts=[],
    ))

    return service


@pytest.fixture
def mock_language_service_fail_grade():
    """Mock LanguageService that returns a failing grade."""
    service = MagicMock()
    service.configured = True

    from app.models.language_schemas import LanguageGradingResponse
    service.grade_exercise = AsyncMock(return_value=LanguageGradingResponse(
        score=4.0,
        verdict="fail",
        feedback="Il y a plusieurs erreurs.",
        corrections="je parle, tu parles, il parle",
        missed_concepts=["conjugation", "-er verbs"],
    ))

    return service


# ---------------------------------------------------------------------------
# 1. GET /language/{user_id}/daily-exercises
# ---------------------------------------------------------------------------


class TestGetDailyExercises:
    """Tests for GET /language/{user_id}/daily-exercises."""

    @pytest.mark.asyncio
    async def test_get_daily_exercises_generates_on_first_call(self, mock_sb, mock_language_service):
        """When no exercises exist for today, generates a batch and returns it."""
        generated_rows = build_pending_batch(8)

        call_count = {"table": 0, "rpc": 0}
        table_responses = {
            # 1st: check existing exercises for today -> empty
            ("language_daily_exercises", 0): make_chain([]),
            # 2nd: user_language_settings -> has active track
            ("user_language_settings", 0): make_chain([{"active_track_id": TEST_TRACK_ID}]),
            # 3rd: language_tracks -> track data
            ("language_tracks", 0): make_chain(SAMPLE_TRACK_DATA),
            # 4th: language_track_progress -> empty (new user)
            ("language_track_progress", 0): make_chain([]),
            # 5th: language_attempts -> no recent
            ("language_attempts", 0): make_chain([]),
            # 6th: book_content -> none
            ("book_content", 0): make_chain([]),
            # 7th: insert new exercises
            ("language_daily_exercises", 1): make_chain(generated_rows),
            # 8th: fetch all exercises for response
            ("language_daily_exercises", 2): make_chain(generated_rows),
        }

        table_call_counts = {}

        def table_handler(table_name):
            idx = table_call_counts.get(table_name, 0)
            table_call_counts[table_name] = idx + 1
            key = (table_name, idx)
            if key in table_responses:
                return table_responses[key]
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
        assert data["generated_date"] == TODAY
        assert len(data["exercises"]) == 8
        assert data["total_count"] == 8
        assert data["completed_count"] == 0

    @pytest.mark.asyncio
    async def test_get_daily_exercises_returns_cached_on_same_day(self, mock_sb):
        """When exercises already exist for today, returns them without regenerating."""
        existing = build_pending_batch(8)

        mock_sb.table.return_value = make_chain(existing)

        with patch("app.routers.language._daily_exercises_cache", {}):
            app.dependency_overrides[get_supabase] = lambda: mock_sb
            transport = httpx.ASGITransport(app=app)
            async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.get(f"/api/language/{TEST_USER_ID}/daily-exercises")

            app.dependency_overrides.clear()

        assert response.status_code == 200
        data = response.json()
        assert len(data["exercises"]) == 8

    @pytest.mark.asyncio
    async def test_get_daily_exercises_includes_reviews(self, mock_sb, mock_language_service):
        """When review queue has due items, they appear as is_review=True exercises."""
        # Batch response includes review exercises
        batch_with_reviews = json.loads(SAMPLE_GEMINI_BATCH_RESPONSE)
        # Ensure at least one has is_review=True
        batch_with_reviews[0]["is_review"] = True
        mock_language_service.generate_batch_exercises = AsyncMock(return_value=batch_with_reviews)

        # Build rows that reflect the generated batch
        rows_with_reviews = []
        for i, ex in enumerate(batch_with_reviews):
            rows_with_reviews.append(make_exercise_row(
                topic=ex["topic"],
                exercise_type=ex["exercise_type"],
                sort_order=i,
                is_review=ex.get("is_review", False),
            ))

        table_call_counts = {}

        def table_handler(table_name):
            idx = table_call_counts.get(table_name, 0)
            table_call_counts[table_name] = idx + 1

            if table_name == "language_daily_exercises" and idx == 0:
                return make_chain([])  # No existing exercises
            if table_name == "user_language_settings":
                return make_chain([{"active_track_id": TEST_TRACK_ID}])
            if table_name == "language_tracks":
                return make_chain(SAMPLE_TRACK_DATA)
            if table_name == "language_track_progress":
                return make_chain([])
            if table_name == "language_attempts":
                return make_chain([])
            if table_name == "book_content":
                return make_chain([])
            if table_name == "language_daily_exercises" and idx == 1:
                return make_chain(rows_with_reviews)  # insert
            if table_name == "language_daily_exercises" and idx == 2:
                return make_chain(rows_with_reviews)  # fetch all
            return make_chain([])

        mock_sb.table.side_effect = table_handler

        # Reviews due from RPC
        review_data = [{
            "id": str(uuid4()),
            "user_id": str(TEST_USER_ID),
            "track_id": TEST_TRACK_ID,
            "topic": "Present Tense",
            "reason": "Weak area from conjugation exercise",
            "priority": 1,
            "next_review": datetime.utcnow().isoformat(),
            "interval_days": 1,
            "review_count": 2,
            "last_reviewed": None,
            "source_attempt_id": None,
            "created_at": datetime.utcnow().isoformat(),
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

    @pytest.mark.asyncio
    async def test_get_daily_exercises_correct_structure(self, mock_sb):
        """Each exercise has all required fields including response_format and word_target."""
        existing = build_pending_batch(3)

        mock_sb.table.return_value = make_chain(existing)

        with patch("app.routers.language._daily_exercises_cache", {}):
            app.dependency_overrides[get_supabase] = lambda: mock_sb
            transport = httpx.ASGITransport(app=app)
            async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.get(f"/api/language/{TEST_USER_ID}/daily-exercises")
            app.dependency_overrides.clear()

        assert response.status_code == 200
        data = response.json()

        required_fields = [
            "id", "topic", "exercise_type", "question_text",
            "status", "sort_order", "is_review", "key_concepts",
            "response_format", "word_target",
        ]
        for exercise in data["exercises"]:
            for field in required_fields:
                assert field in exercise, f"Missing field: {field}"

        # Batch-level fields
        assert "generated_date" in data
        assert "completed_count" in data
        assert "total_count" in data

    @pytest.mark.asyncio
    async def test_get_daily_exercises_mixed_types(self, mock_sb):
        """Batch contains a mix of exercise types (not all the same)."""
        existing = build_pending_batch(8)
        mock_sb.table.return_value = make_chain(existing)

        with patch("app.routers.language._daily_exercises_cache", {}):
            app.dependency_overrides[get_supabase] = lambda: mock_sb
            transport = httpx.ASGITransport(app=app)
            async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.get(f"/api/language/{TEST_USER_ID}/daily-exercises")
            app.dependency_overrides.clear()

        data = response.json()
        types = {e["exercise_type"] for e in data["exercises"]}
        assert len(types) >= 2, f"Expected mixed types, got: {types}"

    @pytest.mark.asyncio
    async def test_get_daily_exercises_count(self, mock_sb):
        """Returns exercises within expected range (5-10)."""
        existing = build_pending_batch(8)
        mock_sb.table.return_value = make_chain(existing)

        with patch("app.routers.language._daily_exercises_cache", {}):
            app.dependency_overrides[get_supabase] = lambda: mock_sb
            transport = httpx.ASGITransport(app=app)
            async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.get(f"/api/language/{TEST_USER_ID}/daily-exercises")
            app.dependency_overrides.clear()

        data = response.json()
        count = len(data["exercises"])
        assert 5 <= count <= 10, f"Expected 5-10 exercises, got {count}"

    @pytest.mark.asyncio
    async def test_get_daily_exercises_no_active_track(self, mock_sb):
        """Returns 400 error when user has no active track."""
        table_call_counts = {}

        def table_handler(table_name):
            idx = table_call_counts.get(table_name, 0)
            table_call_counts[table_name] = idx + 1

            if table_name == "language_daily_exercises":
                return make_chain([])  # No exercises for today
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
    async def test_get_daily_exercises_batch_stats(self, mock_sb):
        """Response includes correct completed_count, total_count, average_score."""
        exercises = [
            make_exercise_row(sort_order=0, status="completed", score=8.0, verdict="pass", feedback="Good",
                              response_text="Answer 1", completed_at=datetime.utcnow().isoformat()),
            make_exercise_row(sort_order=1, status="completed", score=6.0, verdict="borderline", feedback="OK",
                              response_text="Answer 2", completed_at=datetime.utcnow().isoformat()),
            make_exercise_row(sort_order=2, status="pending"),
            make_exercise_row(sort_order=3, status="pending"),
        ]

        mock_sb.table.return_value = make_chain(exercises)

        with patch("app.routers.language._daily_exercises_cache", {}):
            app.dependency_overrides[get_supabase] = lambda: mock_sb
            transport = httpx.ASGITransport(app=app)
            async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.get(f"/api/language/{TEST_USER_ID}/daily-exercises")
            app.dependency_overrides.clear()

        data = response.json()
        assert data["completed_count"] == 2
        assert data["total_count"] == 4
        assert data["average_score"] == 7.0  # (8.0 + 6.0) / 2

    @pytest.mark.asyncio
    async def test_get_daily_exercises_response_format_and_word_target(self, mock_sb):
        """Each exercise has correct response_format and word_target based on exercise_type."""
        existing = build_pending_batch(8)
        mock_sb.table.return_value = make_chain(existing)

        with patch("app.routers.language._daily_exercises_cache", {}):
            app.dependency_overrides[get_supabase] = lambda: mock_sb
            transport = httpx.ASGITransport(app=app)
            async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.get(f"/api/language/{TEST_USER_ID}/daily-exercises")
            app.dependency_overrides.clear()

        data = response.json()
        valid_formats = {"single_line", "short_text", "long_text", "free_form"}

        for exercise in data["exercises"]:
            assert exercise["response_format"] in valid_formats, \
                f"Invalid response_format: {exercise['response_format']}"
            assert isinstance(exercise["word_target"], int), \
                f"word_target should be int, got {type(exercise['word_target'])}"
            assert exercise["word_target"] > 0, \
                f"word_target should be positive, got {exercise['word_target']}"

    @pytest.mark.asyncio
    async def test_get_daily_exercises_tier_distribution(self, mock_sb):
        """Batch of 8 exercises has correct tier distribution: 3 quick, 2 short, 2 extended, 1 free-form."""
        existing = build_pending_batch(8)
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
            fmt = ex["response_format"]
            format_counts[fmt] = format_counts.get(fmt, 0) + 1

        assert format_counts.get("single_line", 0) == 3, f"Expected 3 quick, got {format_counts}"
        assert format_counts.get("short_text", 0) == 2, f"Expected 2 short, got {format_counts}"
        assert format_counts.get("long_text", 0) == 2, f"Expected 2 extended, got {format_counts}"
        assert format_counts.get("free_form", 0) == 1, f"Expected 1 free-form, got {format_counts}"


# ---------------------------------------------------------------------------
# 2. POST /language/daily-exercises/{exercise_id}/submit
# ---------------------------------------------------------------------------


class TestSubmitDailyExercise:
    """Tests for POST /language/daily-exercises/{exercise_id}/submit."""

    @pytest.mark.asyncio
    async def test_submit_exercise_grades_correctly(self, mock_sb, mock_language_service, exercise_id):
        """Submitting a response returns score, verdict, feedback."""
        exercise_row = make_exercise_row(exercise_id=exercise_id, status="pending")
        exercise_row["language_tracks"] = SAMPLE_TRACK_DATA

        # First call: select exercise -> returns exercise row
        # Then: update, insert attempt, etc.
        table_call_counts = {}

        def table_handler(table_name):
            idx = table_call_counts.get(table_name, 0)
            table_call_counts[table_name] = idx + 1

            if table_name == "language_daily_exercises" and idx == 0:
                chain = make_chain(exercise_row)
                return chain
            return make_chain([])

        mock_sb.table.side_effect = table_handler

        with patch("app.routers.language.get_language_service", return_value=mock_language_service), \
             patch("app.routers.language._daily_exercises_cache", {}):
            app.dependency_overrides[get_supabase] = lambda: mock_sb
            transport = httpx.ASGITransport(app=app)
            async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.post(
                    f"/api/language/daily-exercises/{exercise_id}/submit",
                    json={"response_text": "je parle, tu parles, il parle"},
                )
            app.dependency_overrides.clear()

        assert response.status_code == 200
        data = response.json()
        assert "score" in data
        assert "verdict" in data
        assert "feedback" in data
        assert data["score"] == 8.5
        assert data["verdict"] == "pass"

    @pytest.mark.asyncio
    async def test_submit_exercise_updates_status(self, mock_sb, mock_language_service, exercise_id):
        """Exercise status changes from 'pending' to 'completed' via update call."""
        exercise_row = make_exercise_row(exercise_id=exercise_id, status="pending")
        exercise_row["language_tracks"] = SAMPLE_TRACK_DATA

        update_chain = make_chain([])
        table_call_counts = {}

        def table_handler(table_name):
            idx = table_call_counts.get(table_name, 0)
            table_call_counts[table_name] = idx + 1

            if table_name == "language_daily_exercises" and idx == 0:
                return make_chain(exercise_row)
            if table_name == "language_daily_exercises" and idx == 1:
                return update_chain
            return make_chain([])

        mock_sb.table.side_effect = table_handler

        with patch("app.routers.language.get_language_service", return_value=mock_language_service), \
             patch("app.routers.language._daily_exercises_cache", {}):
            app.dependency_overrides[get_supabase] = lambda: mock_sb
            transport = httpx.ASGITransport(app=app)
            async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.post(
                    f"/api/language/daily-exercises/{exercise_id}/submit",
                    json={"response_text": "je parle"},
                )
            app.dependency_overrides.clear()

        assert response.status_code == 200
        # Verify the update was called with status="completed"
        update_chain.update.assert_called_once()
        update_args = update_chain.update.call_args[0][0]
        assert update_args["status"] == "completed"

    @pytest.mark.asyncio
    async def test_submit_exercise_adds_to_review_queue(self, mock_sb, mock_language_service_fail_grade, exercise_id):
        """Score < 7 triggers upsert to language_review_queue."""
        exercise_row = make_exercise_row(exercise_id=exercise_id, status="pending")
        exercise_row["language_tracks"] = SAMPLE_TRACK_DATA

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

        with patch("app.routers.language.get_language_service", return_value=mock_language_service_fail_grade), \
             patch("app.routers.language._daily_exercises_cache", {}):
            app.dependency_overrides[get_supabase] = lambda: mock_sb
            transport = httpx.ASGITransport(app=app)
            async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.post(
                    f"/api/language/daily-exercises/{exercise_id}/submit",
                    json={"response_text": "je parle mal"},
                )
            app.dependency_overrides.clear()

        assert response.status_code == 200
        assert response.json()["score"] == 4.0
        # Verify review queue upsert was called
        review_chain.upsert.assert_called_once()

    @pytest.mark.asyncio
    async def test_submit_exercise_no_review_on_pass(self, mock_sb, mock_language_service, exercise_id):
        """Score >= 7 does NOT add to review queue."""
        exercise_row = make_exercise_row(exercise_id=exercise_id, status="pending")
        exercise_row["language_tracks"] = SAMPLE_TRACK_DATA

        review_upsert_called = {"called": False}
        table_call_counts = {}

        def table_handler(table_name):
            idx = table_call_counts.get(table_name, 0)
            table_call_counts[table_name] = idx + 1

            if table_name == "language_daily_exercises" and idx == 0:
                return make_chain(exercise_row)
            if table_name == "language_review_queue":
                review_upsert_called["called"] = True
                return make_chain([])
            return make_chain([])

        mock_sb.table.side_effect = table_handler

        with patch("app.routers.language.get_language_service", return_value=mock_language_service), \
             patch("app.routers.language._daily_exercises_cache", {}):
            app.dependency_overrides[get_supabase] = lambda: mock_sb
            transport = httpx.ASGITransport(app=app)
            async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.post(
                    f"/api/language/daily-exercises/{exercise_id}/submit",
                    json={"response_text": "je parle, tu parles, il parle"},
                )
            app.dependency_overrides.clear()

        assert response.status_code == 200
        assert response.json()["score"] == 8.5
        assert not review_upsert_called["called"], "Review queue should not be updated for passing score"

    @pytest.mark.asyncio
    async def test_submit_exercise_updates_track_progress(self, mock_sb, mock_language_service, exercise_id):
        """Updates language_track_progress after submission."""
        exercise_row = make_exercise_row(exercise_id=exercise_id, status="pending")
        exercise_row["language_tracks"] = SAMPLE_TRACK_DATA

        progress_chain = make_chain([{
            "id": str(uuid4()),
            "user_id": str(TEST_USER_ID),
            "track_id": TEST_TRACK_ID,
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
                    json={"response_text": "je parle"},
                )
            app.dependency_overrides.clear()

        assert response.status_code == 200
        # Verify track progress was updated
        progress_update_chain.update.assert_called_once()

    @pytest.mark.asyncio
    async def test_submit_exercise_returns_grade(self, mock_sb, mock_language_service, exercise_id):
        """Response matches DailyExerciseGrade schema."""
        exercise_row = make_exercise_row(exercise_id=exercise_id, status="pending")
        exercise_row["language_tracks"] = SAMPLE_TRACK_DATA

        mock_sb.table.return_value = make_chain(exercise_row)

        with patch("app.routers.language.get_language_service", return_value=mock_language_service), \
             patch("app.routers.language._daily_exercises_cache", {}):
            app.dependency_overrides[get_supabase] = lambda: mock_sb
            transport = httpx.ASGITransport(app=app)
            async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.post(
                    f"/api/language/daily-exercises/{exercise_id}/submit",
                    json={"response_text": "je parle"},
                )
            app.dependency_overrides.clear()

        assert response.status_code == 200
        data = response.json()

        # DailyExerciseGrade fields
        assert isinstance(data["score"], (int, float))
        assert data["verdict"] in ("pass", "fail", "borderline")
        assert isinstance(data["feedback"], str)
        assert "missed_concepts" in data

    @pytest.mark.asyncio
    async def test_submit_exercise_not_found(self, mock_sb, exercise_id):
        """Returns 404 for non-existent exercise_id."""
        mock_sb.table.return_value = make_chain(None)

        # Need to make single().execute() return empty
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
                    f"/api/language/daily-exercises/{exercise_id}/submit",
                    json={"response_text": "test answer"},
                )
            app.dependency_overrides.clear()

        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_submit_already_completed(self, mock_sb, exercise_id):
        """Returns existing grade if exercise was already submitted."""
        exercise_row = make_exercise_row(
            exercise_id=exercise_id,
            status="completed",
            score=9.0,
            verdict="pass",
            feedback="Excellent!",
            corrections=None,
            missed_concepts=[],
            response_text="je parle",
            completed_at=datetime.utcnow().isoformat(),
        )
        exercise_row["language_tracks"] = SAMPLE_TRACK_DATA

        mock_sb.table.return_value = make_chain(exercise_row)

        with patch("app.routers.language._daily_exercises_cache", {}):
            app.dependency_overrides[get_supabase] = lambda: mock_sb
            transport = httpx.ASGITransport(app=app)
            async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.post(
                    f"/api/language/daily-exercises/{exercise_id}/submit",
                    json={"response_text": "je parle encore"},
                )
            app.dependency_overrides.clear()

        assert response.status_code == 200
        data = response.json()
        assert data["score"] == 9.0
        assert data["verdict"] == "pass"
        assert data["feedback"] == "Excellent!"


# ---------------------------------------------------------------------------
# 3. POST /language/{user_id}/daily-exercises/regenerate
# ---------------------------------------------------------------------------


class TestRegenerateDailyExercises:
    """Tests for POST /language/{user_id}/daily-exercises/regenerate."""

    @pytest.mark.asyncio
    async def test_regenerate_replaces_pending(self, mock_sb, mock_language_service):
        """Pending exercises are deleted, new ones generated."""
        new_rows = build_pending_batch(8)

        table_call_counts = {}

        def table_handler(table_name):
            idx = table_call_counts.get(table_name, 0)
            table_call_counts[table_name] = idx + 1

            if table_name == "language_daily_exercises" and idx == 0:
                # Delete pending
                return make_chain([])
            if table_name == "language_daily_exercises" and idx == 1:
                # Get remaining completed -> none
                return make_chain([])
            if table_name == "user_language_settings":
                return make_chain([{"active_track_id": TEST_TRACK_ID}])
            if table_name == "language_tracks":
                return make_chain(SAMPLE_TRACK_DATA)
            if table_name == "language_track_progress":
                return make_chain([])
            if table_name == "language_attempts":
                return make_chain([])
            if table_name == "book_content":
                return make_chain([])
            if table_name == "language_daily_exercises" and idx == 2:
                # insert
                return make_chain(new_rows)
            if table_name == "language_daily_exercises" and idx == 3:
                # fetch all
                return make_chain(new_rows)
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
        assert len(data["exercises"]) == 8

    @pytest.mark.asyncio
    async def test_regenerate_keeps_completed(self, mock_sb, mock_language_service):
        """Completed exercises are preserved during regeneration."""
        completed_exercises = [
            make_exercise_row(
                sort_order=0, status="completed", score=8.0, verdict="pass",
                feedback="Good", response_text="Answer", completed_at=datetime.utcnow().isoformat(),
                topic="Present Tense", exercise_type="conjugation",
            ),
            make_exercise_row(
                sort_order=1, status="completed", score=7.0, verdict="pass",
                feedback="OK", response_text="Answer 2", completed_at=datetime.utcnow().isoformat(),
                topic="Past Tense", exercise_type="fill_blank",
            ),
        ]

        # New exercises to fill remaining slots
        new_exercises = build_pending_batch(6)
        for i, ex in enumerate(new_exercises):
            ex["sort_order"] = len(completed_exercises) + i

        all_exercises = completed_exercises + new_exercises

        table_call_counts = {}

        def table_handler(table_name):
            idx = table_call_counts.get(table_name, 0)
            table_call_counts[table_name] = idx + 1

            if table_name == "language_daily_exercises" and idx == 0:
                # Delete pending
                return make_chain([])
            if table_name == "language_daily_exercises" and idx == 1:
                # Get remaining completed
                return make_chain(completed_exercises)
            if table_name == "user_language_settings":
                return make_chain([{"active_track_id": TEST_TRACK_ID}])
            if table_name == "language_tracks":
                return make_chain(SAMPLE_TRACK_DATA)
            if table_name == "language_track_progress":
                return make_chain([])
            if table_name == "language_attempts":
                return make_chain([])
            if table_name == "book_content":
                return make_chain([])
            if table_name == "language_daily_exercises" and idx == 2:
                return make_chain(new_exercises)
            if table_name == "language_daily_exercises" and idx == 3:
                return make_chain(all_exercises)
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
        assert data["total_count"] == 8
        assert data["completed_count"] == 2

        # Completed exercises should be at the beginning
        completed_in_response = [e for e in data["exercises"] if e["status"] == "completed"]
        assert len(completed_in_response) == 2

    @pytest.mark.asyncio
    async def test_regenerate_fills_remaining_slots(self, mock_sb, mock_language_service):
        """New exercises fill up to target total (8)."""
        # 3 completed already
        completed = [
            make_exercise_row(
                sort_order=i, status="completed", score=8.0, verdict="pass",
                feedback="Good", response_text=f"Answer {i}", completed_at=datetime.utcnow().isoformat(),
            )
            for i in range(3)
        ]

        # 5 new ones should be generated
        new_ex = build_pending_batch(5)
        for i, ex in enumerate(new_ex):
            ex["sort_order"] = 3 + i

        all_ex = completed + new_ex

        # Mock should generate exactly 5 exercises
        batch_5 = json.loads(SAMPLE_GEMINI_BATCH_RESPONSE)[:5]
        mock_language_service.generate_batch_exercises = AsyncMock(return_value=batch_5)

        table_call_counts = {}

        def table_handler(table_name):
            idx = table_call_counts.get(table_name, 0)
            table_call_counts[table_name] = idx + 1

            if table_name == "language_daily_exercises" and idx == 0:
                return make_chain([])  # Delete pending
            if table_name == "language_daily_exercises" and idx == 1:
                return make_chain(completed)  # Remaining completed
            if table_name == "user_language_settings":
                return make_chain([{"active_track_id": TEST_TRACK_ID}])
            if table_name == "language_tracks":
                return make_chain(SAMPLE_TRACK_DATA)
            if table_name == "language_track_progress":
                return make_chain([])
            if table_name == "language_attempts":
                return make_chain([])
            if table_name == "book_content":
                return make_chain([])
            if table_name == "language_daily_exercises" and idx == 2:
                return make_chain(new_ex)  # Insert
            if table_name == "language_daily_exercises" and idx == 3:
                return make_chain(all_ex)  # Fetch all
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
        assert data["total_count"] == 8
        assert data["completed_count"] == 3


# ---------------------------------------------------------------------------
# 4. Edge Cases
# ---------------------------------------------------------------------------


class TestEdgeCases:
    """Edge case tests for daily exercise endpoints."""

    @pytest.mark.asyncio
    async def test_gemini_failure_fallback(self, mock_sb):
        """When Gemini fails, exercises are still generated (fallback)."""
        # Use a language service that is NOT configured (simulates Gemini failure)
        with patch("app.routers.language.get_language_service") as mock_get_service:
            service = MagicMock()
            service.configured = False

            # Fallback batch generates exercises without Gemini
            fallback_exercises = [
                {
                    "topic": "Present Tense",
                    "exercise_type": "vocabulary",
                    "question_text": "Utilisez le mot 'cependant' dans une phrase complète.",
                    "expected_answer": "Il fait beau, cependant il fait froid.",
                    "focus_area": "connecteurs logiques",
                    "key_concepts": ["cependant", "opposition"],
                    "is_review": False,
                    "response_format": "single_line",
                    "word_target": 3,
                },
            ]
            service.generate_batch_exercises = AsyncMock(return_value=fallback_exercises)
            mock_get_service.return_value = service

            # Build DB rows from fallback
            fallback_rows = [make_exercise_row(
                topic=ex["topic"], exercise_type=ex["exercise_type"], sort_order=i,
            ) for i, ex in enumerate(fallback_exercises)]

            table_call_counts = {}

            def table_handler(table_name):
                idx = table_call_counts.get(table_name, 0)
                table_call_counts[table_name] = idx + 1

                if table_name == "language_daily_exercises" and idx == 0:
                    return make_chain([])  # No existing
                if table_name == "user_language_settings":
                    return make_chain([{"active_track_id": TEST_TRACK_ID}])
                if table_name == "language_tracks":
                    return make_chain(SAMPLE_TRACK_DATA)
                if table_name == "language_track_progress":
                    return make_chain([])
                if table_name == "language_attempts":
                    return make_chain([])
                if table_name == "book_content":
                    return make_chain([])
                if table_name == "language_daily_exercises" and idx == 1:
                    return make_chain(fallback_rows)
                if table_name == "language_daily_exercises" and idx == 2:
                    return make_chain(fallback_rows)
                return make_chain([])

            mock_sb.table.side_effect = table_handler
            mock_sb.rpc.return_value = make_chain([])

            with patch("app.routers.language._daily_exercises_cache", {}):
                app.dependency_overrides[get_supabase] = lambda: mock_sb
                transport = httpx.ASGITransport(app=app)
                async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
                    response = await client.get(f"/api/language/{TEST_USER_ID}/daily-exercises")
                app.dependency_overrides.clear()

        assert response.status_code == 200
        data = response.json()
        assert len(data["exercises"]) >= 1
        # Exercises were generated even without Gemini
        assert data["exercises"][0]["question_text"] is not None
