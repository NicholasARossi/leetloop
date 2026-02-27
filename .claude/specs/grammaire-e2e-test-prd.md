# Grammaire Progressive E2E Test Suite — PRD

## Overview
Write a comprehensive pytest test suite that validates the full user journey through the Grammaire Progressive B2 language learning track. Tests should cover: new user onboarding, track selection, daily exercise generation with book content integration, exercise submission with grading, progress tracking, spaced repetition review queue behavior, and dashboard accuracy.

All tests mock Supabase and Gemini (no real API calls). Follow patterns from `api/tests/test_daily_exercises.py`.

## File Location
`api/tests/test_grammaire_e2e.py`

## Test Constants
```python
TEST_USER_ID = UUID("00000000-0000-0000-0000-000000000099")
GRAMMAIRE_TRACK_ID = "5eba8cda-1cbf-4d07-b770-1204a7b54a75"
GRAMMAIRE_TRACK_NAME = "Grammaire Progressive B2"
TODAY = datetime.utcnow().strftime("%Y-%m-%d")
```

## Test Data
Build realistic track data from the actual Grammaire Progressive manifest:
- 27 topics matching the real chapter titles (L'ARTICLE, L'ADJECTIF, ... LA MODALISATION)
- Rubric: `{accuracy: 3, grammar: 3, vocabulary: 2, naturalness: 2}`
- Language: french, Level: b2
- Book content rows with real summaries from the ingested JSON files

## Approach
Use `make_chain()` mock helper and `table_call_counts` sequencing pattern from existing tests. Each test class represents a stage in the user journey. Tests within a class can share mock setup.

---

## Task List (effort-aware)

### Batch 1: Test Infrastructure + Track Discovery (effort: low)
Set up test file scaffolding, constants, mock helpers, and track data fixtures.

- [ ] Create `test_grammaire_e2e.py` with imports, constants, `make_chain()` helper
- [ ] Build `GRAMMAIRE_TRACK_DATA` dict matching the real 27-topic track
- [ ] Build `GRAMMAIRE_BOOK_CONTENT` list with 2-3 sample chapters (Ch.1 L'Article, Ch.5 Le Subjonctif, Ch.21 L'Expression de la Cause) — include realistic summaries and key_concepts from the actual JSON files
- [ ] Write `TestTrackDiscovery`:
  - `test_list_tracks_includes_grammaire` — GET /language/tracks returns Grammaire Progressive B2
  - `test_get_track_details` — GET /language/tracks/{id} returns 27 topics with correct order and key_concepts
- [ ] Validate: `cd api && python -m pytest tests/test_grammaire_e2e.py -v`

### Batch 2: Track Selection + New User Setup (effort: low)
Test that a new user can select the Grammaire track and their settings are persisted.

- [ ] Write `TestTrackSelection`:
  - `test_set_active_track` — PUT /language/{user_id}/active-track with Grammaire track_id → success, returns track name
  - `test_set_active_track_invalid_id` — PUT with nonexistent track_id → 404
  - `test_dashboard_shows_active_track` — GET /language/{user_id}/dashboard reflects the newly selected track
  - `test_new_user_has_zero_progress` — GET /language/tracks/{id}/progress/{user_id} → completed_topics=[], sessions_completed=0, next_topic="L'ARTICLE"
- [ ] Validate: run tests

### Batch 3: Day 1 Exercise Generation (effort: medium)
Test that the first daily exercise batch is generated correctly with book content integration.

- [ ] Write `TestDay1ExerciseGeneration`:
  - `test_first_daily_exercises_generates_batch` — GET /language/{user_id}/daily-exercises on day 1:
    - No existing exercises → triggers generation
    - Calls generate_batch_exercises with language="french", level="b2"
    - Returns 8 exercises with correct tier distribution (3 quick + 2 short + 2 extended + 1 free-form)
    - All exercises have status="pending"
  - `test_exercises_use_book_content` — Verify that book_content is fetched by language_track_id and passed to Gemini as BookContentContext
  - `test_exercises_start_with_first_topics` — New user's exercises should target early topics (L'ARTICLE, L'ADJECTIF, etc.), not random chapters
  - `test_no_review_exercises_on_day_1` — No reviews due yet, so is_review=False for all
  - `test_second_call_returns_cached_batch` — Second GET returns same exercises without re-generating
- [ ] Validate: run tests

### Batch 4: Exercise Submission + Grading (effort: medium)
Test submitting answers and receiving grades, including pass/fail paths.

- [ ] Write `TestExerciseSubmission`:
  - `test_submit_passing_answer` — POST with good answer → score >= 7, verdict="pass", feedback in French
  - `test_submit_failing_answer` — POST with bad answer → score < 7, verdict="fail", corrections provided, missed_concepts populated
  - `test_submit_creates_attempt_record` — Verify language_attempts row is inserted with correct fields
  - `test_passing_score_marks_topic_completed` — Score >= 7 → language_track_progress.completed_topics includes the topic
  - `test_failing_score_adds_to_review_queue` — Score < 7 → language_review_queue entry with interval_days=1, next_review=tomorrow
  - `test_submit_already_completed_returns_cached` — Re-submitting a completed exercise returns the saved grade without re-grading
  - `test_submit_updates_average_score` — After multiple submissions, average_score in track_progress is recalculated
- [ ] Validate: run tests

### Batch 5: Progress Tracking (effort: medium)
Test that progress endpoints reflect the correct state after day 1 activity.

- [ ] Write `TestProgressTracking`:
  - `test_progress_after_mixed_results` — After some passes and fails:
    - completed_topics contains only passed topics
    - completion_percentage = passed_count / 27 * 100
    - next_topic is the first uncompleted topic in order
  - `test_book_progress_shows_chapter_status` — GET /language/tracks/{id}/book-progress/{user_id}:
    - Completed chapters marked is_completed=True
    - First uncompleted chapter marked is_current=True
    - Failed topics marked has_review_due=True
    - Book sections and summaries populated from book_content
  - `test_dashboard_after_day_1` — GET /language/{user_id}/dashboard:
    - exercises_this_week matches completed count
    - reviews_due_count matches failed exercises
    - recent_score is last exercise score
    - next_topic advances past completed topics
- [ ] Validate: run tests

### Batch 6: Spaced Repetition + Day 2 (effort: medium)
Test the review queue behavior on subsequent days.

- [ ] Write `TestSpacedRepetition`:
  - `test_day_2_includes_review_exercises` — On day 2, failed topics from day 1 appear as is_review=True exercises
  - `test_review_success_doubles_interval` — Passing a review (score >= 7) doubles interval_days (1→2)
  - `test_review_failure_resets_interval` — Failing a review resets interval_days to 1
  - `test_review_topics_mixed_with_new` — Day 2 batch has both review exercises and new topic exercises
  - `test_max_interval_is_30_days` — Repeated successes cap at interval_days=30
- [ ] Validate: run tests

### Batch 7: Edge Cases + Regeneration (effort: low)
Test error handling, edge cases, and the regenerate flow.

- [ ] Write `TestEdgeCases`:
  - `test_no_active_track_returns_error` — GET daily-exercises with no track set → appropriate error
  - `test_gemini_failure_fallback` — If generate_batch_exercises fails, exercises still generated (fallback behavior)
  - `test_regenerate_replaces_pending_keeps_completed` — POST /language/{user_id}/daily-exercises/regenerate:
    - Deletes pending exercises
    - Keeps completed exercises intact
    - Generates new exercises to fill remaining slots
  - `test_empty_response_text_rejected` — Submit with empty string → validation error
  - `test_exercise_word_count_tracked` — Word count is computed and stored on submission
- [ ] Validate: run tests

### Batch 8: Full Flow Integration (effort: low)
A single large integration test that traces the complete new-user-to-progress journey.

- [ ] Write `TestFullUserJourney`:
  - `test_complete_day_1_flow` — Single test exercising the full sequence:
    1. List tracks → Grammaire Progressive B2 present
    2. Set active track → success
    3. Get daily exercises → 8 pending exercises generated
    4. Submit 6 exercises (4 pass, 2 fail)
    5. Check progress → 4 completed topics, 2 in review queue
    6. Check dashboard → exercises_this_week=6, reviews_due=2
    7. Verify book_content was used in exercise generation
  - This test validates the table call sequencing end-to-end
- [ ] Validate: run all tests with `python -m pytest tests/test_grammaire_e2e.py -v --tb=short`

## Verification
After each batch:
1. `cd api && python -m pytest tests/test_grammaire_e2e.py -v` — all tests pass
2. No import errors or missing fixtures
3. Each test is self-contained (mocks set up and torn down per test)
4. No real API calls (all Supabase and Gemini mocked)

## Completion Promise
All tests in `api/tests/test_grammaire_e2e.py` pass when run with `cd api && python -m pytest tests/test_grammaire_e2e.py -v`.
