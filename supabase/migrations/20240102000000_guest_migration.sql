-- Guest to Auth Migration Function
-- Migrates data from a guest UUID to an authenticated user's auth.uid()

-- Function to migrate guest data to authenticated user
CREATE OR REPLACE FUNCTION migrate_guest_to_auth(
  p_guest_id UUID,
  p_auth_id UUID
) RETURNS JSON
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
  v_submissions_count INTEGER;
  v_skills_count INTEGER;
  v_reviews_count INTEGER;
  v_settings_count INTEGER;
  v_notes_count INTEGER;
BEGIN
  -- Migrate submissions
  UPDATE submissions
  SET user_id = p_auth_id
  WHERE user_id = p_guest_id;
  GET DIAGNOSTICS v_submissions_count = ROW_COUNT;

  -- Migrate skill scores
  -- Handle potential conflicts by updating existing or inserting new
  INSERT INTO skill_scores (user_id, tag, score, total_attempts, success_rate, avg_time_seconds, last_practiced, updated_at)
  SELECT p_auth_id, tag, score, total_attempts, success_rate, avg_time_seconds, last_practiced, NOW()
  FROM skill_scores
  WHERE user_id = p_guest_id
  ON CONFLICT (user_id, tag)
  DO UPDATE SET
    score = EXCLUDED.score,
    total_attempts = skill_scores.total_attempts + EXCLUDED.total_attempts,
    success_rate = EXCLUDED.success_rate,
    avg_time_seconds = EXCLUDED.avg_time_seconds,
    last_practiced = GREATEST(skill_scores.last_practiced, EXCLUDED.last_practiced),
    updated_at = NOW();

  -- Delete original guest skill scores
  DELETE FROM skill_scores WHERE user_id = p_guest_id;
  GET DIAGNOSTICS v_skills_count = ROW_COUNT;

  -- Migrate review queue
  -- Handle potential conflicts by keeping the one with earliest next_review
  INSERT INTO review_queue (user_id, problem_slug, problem_title, reason, priority, next_review, interval_days, review_count, last_reviewed, created_at)
  SELECT p_auth_id, problem_slug, problem_title, reason, priority, next_review, interval_days, review_count, last_reviewed, created_at
  FROM review_queue
  WHERE user_id = p_guest_id
  ON CONFLICT (user_id, problem_slug)
  DO UPDATE SET
    next_review = LEAST(review_queue.next_review, EXCLUDED.next_review),
    priority = GREATEST(review_queue.priority, EXCLUDED.priority),
    updated_at = NOW()
  WHERE review_queue.next_review > EXCLUDED.next_review;

  -- Delete original guest review items
  DELETE FROM review_queue WHERE user_id = p_guest_id;
  GET DIAGNOSTICS v_reviews_count = ROW_COUNT;

  -- Migrate user settings (only if auth user doesn't have settings)
  INSERT INTO user_settings (user_id, telegram_chat_id, daily_goal, notification_enabled, timezone, created_at, updated_at)
  SELECT p_auth_id, telegram_chat_id, daily_goal, notification_enabled, timezone, created_at, NOW()
  FROM user_settings
  WHERE user_id = p_guest_id
  ON CONFLICT (user_id) DO NOTHING;

  -- Delete guest settings
  DELETE FROM user_settings WHERE user_id = p_guest_id;
  GET DIAGNOSTICS v_settings_count = ROW_COUNT;

  -- Migrate submission notes (submission_id foreign key should still be valid after submission migration)
  UPDATE submission_notes
  SET user_id = p_auth_id
  WHERE user_id = p_guest_id;
  GET DIAGNOSTICS v_notes_count = ROW_COUNT;

  RETURN json_build_object(
    'success', true,
    'migrated', json_build_object(
      'submissions', v_submissions_count,
      'skill_scores', v_skills_count,
      'review_queue', v_reviews_count,
      'user_settings', v_settings_count,
      'submission_notes', v_notes_count
    )
  );
END;
$$;

-- Add unique constraint for review_queue if not exists (needed for ON CONFLICT)
DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_constraint
    WHERE conname = 'review_queue_user_problem_unique'
  ) THEN
    ALTER TABLE review_queue
    ADD CONSTRAINT review_queue_user_problem_unique
    UNIQUE (user_id, problem_slug);
  END IF;
END $$;

-- Grant execute permission to authenticated users
GRANT EXECUTE ON FUNCTION migrate_guest_to_auth TO authenticated;
