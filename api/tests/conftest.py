"""Pytest fixtures for API testing."""

import pytest
import httpx
from datetime import date, datetime
from unittest.mock import MagicMock, AsyncMock
from uuid import UUID

from app.main import app
from app.db.supabase import get_supabase


# Sample learning path data matching NeetCode 150 structure
SAMPLE_LEARNING_PATH = {
    "id": "11111111-1111-1111-1111-111111111150",
    "name": "NeetCode 150",
    "categories": [
        {
            "name": "Arrays & Hashing",
            "order": 1,
            "problems": [
                {"slug": "contains-duplicate", "title": "Contains Duplicate", "difficulty": "Easy", "order": 1},
                {"slug": "valid-anagram", "title": "Valid Anagram", "difficulty": "Easy", "order": 2},
                {"slug": "two-sum", "title": "Two Sum", "difficulty": "Easy", "order": 3},
            ]
        },
        {
            "name": "Two Pointers",
            "order": 2,
            "problems": [
                {"slug": "valid-palindrome", "title": "Valid Palindrome", "difficulty": "Easy", "order": 1},
                {"slug": "two-sum-ii", "title": "Two Sum II", "difficulty": "Medium", "order": 2},
                {"slug": "3sum", "title": "3Sum", "difficulty": "Medium", "order": 3},
            ]
        },
        {
            "name": "Sliding Window",
            "order": 3,
            "problems": [
                {"slug": "best-time-to-buy-and-sell-stock", "title": "Best Time to Buy and Sell Stock", "difficulty": "Easy", "order": 1},
                {"slug": "longest-substring-without-repeating-characters", "title": "Longest Substring Without Repeating Characters", "difficulty": "Medium", "order": 2},
            ]
        },
    ]
}


@pytest.fixture
def test_user_id():
    """A test user UUID."""
    return UUID("00000000-0000-0000-0000-000000000001")


@pytest.fixture
def mock_supabase():
    """Create a mock Supabase client with common query patterns."""
    mock = MagicMock()

    def create_query_chain(data=None, count=None):
        """Create a chainable query mock that returns data on execute()."""
        query = MagicMock()
        query.select.return_value = query
        query.eq.return_value = query
        query.neq.return_value = query
        query.gte.return_value = query
        query.lte.return_value = query
        query.order.return_value = query
        query.limit.return_value = query
        query.single.return_value = query
        query.insert.return_value = query
        query.update.return_value = query
        query.delete.return_value = query

        result = MagicMock()
        result.data = data
        result.count = count
        query.execute.return_value = result
        return query

    # Default empty responses for all tables
    mock.table.return_value = create_query_chain([])

    return mock, create_query_chain


@pytest.fixture
def mock_supabase_with_data(mock_supabase, test_user_id):
    """Supabase mock with realistic user data."""
    mock, create_query_chain = mock_supabase

    user_id_str = str(test_user_id)
    today = date.today().isoformat()

    # Configure table responses based on table name
    def table_handler(table_name):
        if table_name == "meta_objectives":
            return create_query_chain([{
                "user_id": user_id_str,
                "target_company": "Google",
                "target_role": "Software Engineer",
                "target_deadline": "2027-03-01",
                "weekly_problem_target": 25,
                "status": "active",
            }])
        elif table_name == "user_settings":
            return create_query_chain([{
                "user_id": user_id_str,
                "current_path_id": "11111111-1111-1111-1111-111111111150",
            }])
        elif table_name == "learning_paths":
            return create_query_chain(SAMPLE_LEARNING_PATH)
        elif table_name == "user_path_progress":
            return create_query_chain([{
                "user_id": user_id_str,
                "path_id": "11111111-1111-1111-1111-111111111150",
                "completed_problems": ["contains-duplicate", "valid-anagram"],
                "current_category": "Arrays & Hashing",
            }])
        elif table_name == "submissions":
            return create_query_chain([
                {"problem_slug": "contains-duplicate"},
                {"problem_slug": "valid-anagram"},
            ])
        elif table_name == "skill_scores":
            return create_query_chain([
                {"tag": "Arrays", "score": 75, "total_attempts": 10, "avg_time_seconds": 1200},
                {"tag": "Sliding Window", "score": 45, "total_attempts": 5, "avg_time_seconds": 1800},
            ])
        elif table_name == "review_queue":
            return create_query_chain([])
        elif table_name == "user_streaks":
            return create_query_chain([{
                "user_id": user_id_str,
                "current_streak": 5,
                "last_activity_date": today,
            }])
        elif table_name == "problem_attempt_stats":
            return create_query_chain([])
        elif table_name == "daily_missions":
            return create_query_chain([])
        elif table_name == "mission_problems":
            return create_query_chain([])
        else:
            return create_query_chain([])

    mock.table.side_effect = table_handler
    return mock


@pytest.fixture
def mock_gemini_standard_format():
    """Mock Gemini that returns the expected 'problems' format."""
    mock = MagicMock()
    mock.configured = True

    response = MagicMock()
    response.text = '''```json
{
  "daily_objective": "Master Two Pointer patterns",
  "problems": [
    {
      "problem_id": "two-sum",
      "source": "path",
      "reasoning": "Continue with Arrays & Hashing fundamentals",
      "priority": 1,
      "skills": ["Arrays", "Hash Table"],
      "estimated_difficulty": "easy"
    },
    {
      "problem_id": "valid-palindrome",
      "source": "path",
      "reasoning": "Start Two Pointers section",
      "priority": 2,
      "skills": ["Two Pointers", "String"],
      "estimated_difficulty": "easy"
    },
    {
      "problem_id": "best-time-to-buy-and-sell-stock",
      "source": "gap_fill",
      "reasoning": "Address Sliding Window weakness",
      "priority": 3,
      "skills": ["Sliding Window"],
      "estimated_difficulty": "easy"
    }
  ],
  "balance_explanation": "60% path, 40% gap-filling",
  "pacing_status": "on_track",
  "pacing_note": "You're making good progress"
}
```'''
    mock.model.generate_content.return_value = response
    return mock


@pytest.fixture
def mock_gemini_legacy_format():
    """Mock Gemini that returns 'main_quests' format (the bug we fixed)."""
    mock = MagicMock()
    mock.configured = True

    response = MagicMock()
    response.text = '''```json
{
  "daily_objective": "Strengthen Sliding Window foundations",
  "main_quests": [
    {
      "slug": "two-sum",
      "order": 1,
      "title": "Two Sum",
      "category": "Arrays & Hashing",
      "reasoning": "Continue with Arrays & Hashing fundamentals",
      "difficulty": "easy"
    },
    {
      "slug": "valid-palindrome",
      "order": 2,
      "title": "Valid Palindrome",
      "category": "Two Pointers",
      "reasoning": "Start Two Pointers section",
      "difficulty": "easy"
    },
    {
      "slug": "best-time-to-buy-and-sell-stock",
      "order": 3,
      "title": "Best Time to Buy and Sell Stock",
      "category": "Sliding Window",
      "reasoning": "Address Sliding Window weakness",
      "difficulty": "easy"
    }
  ],
  "side_quests": [
    {
      "slug": "contains-duplicate",
      "title": "Contains Duplicate",
      "reason": "Review this problem",
      "difficulty": "easy",
      "quest_type": "review_due"
    }
  ],
  "balance_explanation": "60% path, 40% gap-filling",
  "pacing_status": "ahead",
  "pacing_note": "You're ahead of schedule"
}
```'''
    mock.model.generate_content.return_value = response
    return mock


@pytest.fixture
def mock_gemini_unconfigured():
    """Mock Gemini that is not configured (uses fallback)."""
    mock = MagicMock()
    mock.configured = False
    return mock


@pytest.fixture
async def client(mock_supabase_with_data):
    """FastAPI async test client with mocked Supabase."""
    app.dependency_overrides[get_supabase] = lambda: mock_supabase_with_data
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as test_client:
        yield test_client
    app.dependency_overrides.clear()
