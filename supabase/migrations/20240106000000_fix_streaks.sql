-- Fix Streak System
-- 1. Add trigger to update streak when submissions are created
-- 2. Fix get_user_stats to return actual streak value

-- Trigger function to update streak on accepted submissions
CREATE OR REPLACE FUNCTION update_streak_on_submission()
RETURNS TRIGGER AS $$
BEGIN
  -- Only update streak for accepted submissions
  IF NEW.status = 'Accepted' THEN
    PERFORM update_user_streak(NEW.user_id);
  END IF;
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Create trigger on submissions table
DROP TRIGGER IF EXISTS trg_update_streak_on_submission ON submissions;
CREATE TRIGGER trg_update_streak_on_submission
  AFTER INSERT ON submissions
  FOR EACH ROW
  EXECUTE FUNCTION update_streak_on_submission();

-- Fix get_user_stats to properly return streak_days from user_streaks table
CREATE OR REPLACE FUNCTION get_user_stats(p_user_id UUID)
RETURNS TABLE (
  total_submissions BIGINT,
  accepted_count BIGINT,
  failed_count BIGINT,
  success_rate REAL,
  problems_solved BIGINT,
  problems_attempted BIGINT,
  streak_days INTEGER
) AS $$
DECLARE
  v_streak INTEGER := 0;
  v_last_date DATE;
  v_current_streak INTEGER;
BEGIN
  -- Get streak from user_streaks table
  SELECT us.current_streak, us.last_activity_date
  INTO v_current_streak, v_last_date
  FROM user_streaks us
  WHERE us.user_id = p_user_id;

  -- Only count streak if activity was today or yesterday
  IF v_last_date IS NOT NULL AND (CURRENT_DATE - v_last_date) <= 1 THEN
    v_streak := COALESCE(v_current_streak, 0);
  END IF;

  RETURN QUERY
  SELECT
    COUNT(*)::BIGINT as total_submissions,
    COUNT(*) FILTER (WHERE s.status = 'Accepted')::BIGINT as accepted_count,
    COUNT(*) FILTER (WHERE s.status != 'Accepted')::BIGINT as failed_count,
    (COUNT(*) FILTER (WHERE s.status = 'Accepted')::REAL / NULLIF(COUNT(*)::REAL, 0)) as success_rate,
    COUNT(DISTINCT s.problem_slug) FILTER (WHERE s.status = 'Accepted')::BIGINT as problems_solved,
    COUNT(DISTINCT s.problem_slug)::BIGINT as problems_attempted,
    v_streak as streak_days
  FROM submissions s
  WHERE s.user_id = p_user_id;
END;
$$ LANGUAGE plpgsql;
