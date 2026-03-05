-- Remove runtime percentile from optimality check
-- Accepted = optimal. Gemini complexity analysis can downgrade later.

CREATE OR REPLACE FUNCTION match_submission_to_feed()
RETURNS TRIGGER AS $$
DECLARE
  v_feed_item RECORD;
  v_is_optimal BOOLEAN;
BEGIN
  IF NEW.status NOT IN ('Accepted', 'Wrong Answer', 'Time Limit Exceeded',
                         'Memory Limit Exceeded', 'Runtime Error') THEN
    RETURN NEW;
  END IF;

  SELECT df.*
  INTO v_feed_item
  FROM daily_problem_feed df
  WHERE df.user_id = NEW.user_id
    AND df.feed_date = CURRENT_DATE
    AND df.problem_slug = NEW.problem_slug
    AND df.status = 'pending'
  LIMIT 1;

  IF NOT FOUND THEN
    RETURN NEW;
  END IF;

  v_is_optimal := (NEW.status = 'Accepted');

  UPDATE daily_problem_feed SET
    status = 'completed',
    completed_at = NEW.submitted_at,
    submission_id = NEW.id,
    was_accepted = (NEW.status = 'Accepted'),
    was_optimal = v_is_optimal,
    runtime_percentile = NEW.runtime_percentile
  WHERE id = v_feed_item.id;

  IF v_feed_item.feed_type = 'metric' THEN
    INSERT INTO metric_attempts (
      user_id, problem_slug, difficulty, submission_id, feed_item_id,
      accepted, runtime_percentile, optimal, final_optimal, attempted_at
    ) VALUES (
      NEW.user_id, NEW.problem_slug, v_feed_item.difficulty, NEW.id, v_feed_item.id,
      (NEW.status = 'Accepted'), NEW.runtime_percentile, v_is_optimal, v_is_optimal,
      NEW.submitted_at
    );
  END IF;

  RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Fix existing metric attempts: accepted = optimal
UPDATE metric_attempts SET optimal = TRUE, final_optimal = TRUE WHERE accepted = TRUE;
UPDATE daily_problem_feed SET was_optimal = TRUE WHERE was_accepted = TRUE;
