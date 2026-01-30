-- Fix: migrate_guest_to_auth - use simple delete/insert instead of upsert

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
BEGIN
  -- Migrate submissions (simple update)
  UPDATE submissions
  SET user_id = p_auth_id
  WHERE user_id = p_guest_id;
  GET DIAGNOSTICS v_submissions_count = ROW_COUNT;

  -- Migrate skill scores - delete conflicts first, then update
  DELETE FROM skill_scores
  WHERE user_id = p_auth_id
    AND tag IN (SELECT tag FROM skill_scores WHERE user_id = p_guest_id);

  UPDATE skill_scores
  SET user_id = p_auth_id
  WHERE user_id = p_guest_id;
  GET DIAGNOSTICS v_skills_count = ROW_COUNT;

  -- Migrate review queue - delete conflicts first, then update
  DELETE FROM review_queue
  WHERE user_id = p_auth_id
    AND problem_slug IN (SELECT problem_slug FROM review_queue WHERE user_id = p_guest_id);

  UPDATE review_queue
  SET user_id = p_auth_id
  WHERE user_id = p_guest_id;
  GET DIAGNOSTICS v_reviews_count = ROW_COUNT;

  -- Migrate user settings - only if auth user doesn't have settings
  IF NOT EXISTS (SELECT 1 FROM user_settings WHERE user_id = p_auth_id) THEN
    UPDATE user_settings
    SET user_id = p_auth_id
    WHERE user_id = p_guest_id;
    GET DIAGNOSTICS v_settings_count = ROW_COUNT;
  ELSE
    DELETE FROM user_settings WHERE user_id = p_guest_id;
    v_settings_count := 0;
  END IF;

  RETURN json_build_object(
    'success', true,
    'migrated', json_build_object(
      'submissions', v_submissions_count,
      'skill_scores', v_skills_count,
      'review_queue', v_reviews_count,
      'user_settings', v_settings_count
    )
  );
END;
$$;

-- Notify PostgREST to reload schema cache
NOTIFY pgrst, 'reload schema';
