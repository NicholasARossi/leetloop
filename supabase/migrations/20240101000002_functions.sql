-- Database Functions
-- Utility functions for LeetLoop

-- Function to update skill scores after a submission
CREATE OR REPLACE FUNCTION update_skill_scores()
RETURNS TRIGGER AS $$
DECLARE
  tag TEXT;
  current_score REAL;
  new_score REAL;
  is_success BOOLEAN;
BEGIN
  -- Check if submission was successful
  is_success := NEW.status = 'Accepted';

  -- Update skill score for each tag
  IF NEW.tags IS NOT NULL THEN
    FOREACH tag IN ARRAY NEW.tags
    LOOP
      -- Get current score or use default
      SELECT score INTO current_score
      FROM skill_scores
      WHERE user_id = NEW.user_id AND skill_scores.tag = tag;

      IF current_score IS NULL THEN
        current_score := 50.0;
      END IF;

      -- Calculate new score (simple ELO-like adjustment)
      IF is_success THEN
        new_score := LEAST(current_score + 2.0, 100.0);
      ELSE
        new_score := GREATEST(current_score - 1.0, 0.0);
      END IF;

      -- Upsert skill score
      INSERT INTO skill_scores (user_id, tag, score, total_attempts, success_rate, last_practiced, updated_at)
      VALUES (
        NEW.user_id,
        tag,
        new_score,
        1,
        CASE WHEN is_success THEN 1.0 ELSE 0.0 END,
        NOW(),
        NOW()
      )
      ON CONFLICT (user_id, tag) DO UPDATE SET
        score = new_score,
        total_attempts = skill_scores.total_attempts + 1,
        success_rate = (
          (skill_scores.success_rate * skill_scores.total_attempts + (CASE WHEN is_success THEN 1 ELSE 0 END))
          / (skill_scores.total_attempts + 1)
        ),
        last_practiced = NOW(),
        updated_at = NOW();
    END LOOP;
  END IF;

  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger to update skill scores on new submission
DROP TRIGGER IF EXISTS trigger_update_skill_scores ON submissions;
CREATE TRIGGER trigger_update_skill_scores
  AFTER INSERT ON submissions
  FOR EACH ROW
  EXECUTE FUNCTION update_skill_scores();

-- Function to add problem to review queue on failure
CREATE OR REPLACE FUNCTION add_to_review_queue()
RETURNS TRIGGER AS $$
BEGIN
  -- Only add to review queue on failure
  IF NEW.status != 'Accepted' THEN
    -- Insert or update review queue item
    INSERT INTO review_queue (user_id, problem_slug, problem_title, reason, next_review, interval_days)
    VALUES (
      NEW.user_id,
      NEW.problem_slug,
      NEW.problem_title,
      NEW.status,
      NOW() + INTERVAL '1 day',
      1
    )
    ON CONFLICT DO NOTHING;
  END IF;

  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger to add failed submissions to review queue
DROP TRIGGER IF EXISTS trigger_add_to_review_queue ON submissions;
CREATE TRIGGER trigger_add_to_review_queue
  AFTER INSERT ON submissions
  FOR EACH ROW
  EXECUTE FUNCTION add_to_review_queue();

-- Function to get user statistics
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
BEGIN
  RETURN QUERY
  SELECT
    COUNT(*)::BIGINT as total_submissions,
    COUNT(*) FILTER (WHERE status = 'Accepted')::BIGINT as accepted_count,
    COUNT(*) FILTER (WHERE status != 'Accepted')::BIGINT as failed_count,
    (COUNT(*) FILTER (WHERE status = 'Accepted')::REAL / NULLIF(COUNT(*)::REAL, 0)) as success_rate,
    COUNT(DISTINCT problem_slug) FILTER (WHERE status = 'Accepted')::BIGINT as problems_solved,
    COUNT(DISTINCT problem_slug)::BIGINT as problems_attempted,
    0 as streak_days  -- TODO: Calculate streak
  FROM submissions
  WHERE user_id = p_user_id;
END;
$$ LANGUAGE plpgsql;

-- Function to get due reviews
CREATE OR REPLACE FUNCTION get_due_reviews(p_user_id UUID, p_limit INTEGER DEFAULT 10)
RETURNS TABLE (
  id UUID,
  problem_slug TEXT,
  problem_title TEXT,
  reason TEXT,
  interval_days INTEGER,
  review_count INTEGER
) AS $$
BEGIN
  RETURN QUERY
  SELECT
    rq.id,
    rq.problem_slug,
    rq.problem_title,
    rq.reason,
    rq.interval_days,
    rq.review_count
  FROM review_queue rq
  WHERE rq.user_id = p_user_id
    AND rq.next_review <= NOW()
  ORDER BY rq.priority DESC, rq.next_review ASC
  LIMIT p_limit;
END;
$$ LANGUAGE plpgsql;

-- Function to complete a review (spaced repetition update)
CREATE OR REPLACE FUNCTION complete_review(p_review_id UUID, p_success BOOLEAN)
RETURNS VOID AS $$
DECLARE
  new_interval INTEGER;
BEGIN
  -- Get current interval and calculate new one
  SELECT
    CASE
      WHEN p_success THEN LEAST(interval_days * 2, 30)  -- Double interval, max 30 days
      ELSE 1  -- Reset to 1 day on failure
    END INTO new_interval
  FROM review_queue
  WHERE id = p_review_id;

  -- Update review queue item
  UPDATE review_queue
  SET
    interval_days = new_interval,
    next_review = NOW() + (new_interval || ' days')::INTERVAL,
    review_count = review_count + 1,
    last_reviewed = NOW()
  WHERE id = p_review_id;
END;
$$ LANGUAGE plpgsql;
