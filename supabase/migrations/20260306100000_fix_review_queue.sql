-- Fix review queue: deduplicate entries, auto-complete on accepted submission, graduation
--
-- Problems fixed:
-- 1. Unique constraint was dropped, allowing duplicate (user_id, problem_slug) entries
-- 2. Accepted submissions never updated/closed review queue entries
-- 3. No graduation mechanism — problems cycled forever (max 30-day interval)

-- 1. Deduplicate: keep the best entry per (user_id, problem_slug)
--    Best = highest interval_days, then highest review_count
DELETE FROM review_queue
WHERE id NOT IN (
  SELECT DISTINCT ON (user_id, problem_slug) id
  FROM review_queue
  ORDER BY user_id, problem_slug, interval_days DESC, review_count DESC, created_at ASC
);

-- 2. Re-add unique constraint
ALTER TABLE review_queue
ADD CONSTRAINT review_queue_user_problem_unique
UNIQUE (user_id, problem_slug);

-- 3. Update trigger to handle BOTH accepted and failed submissions
CREATE OR REPLACE FUNCTION add_to_review_queue()
RETURNS TRIGGER AS $$
BEGIN
  IF NEW.status = 'Accepted' THEN
    -- Successful submission: check if problem should graduate from review queue
    IF EXISTS (
      SELECT 1 FROM review_queue
      WHERE user_id = NEW.user_id
        AND problem_slug = NEW.problem_slug
        AND interval_days >= 16
        AND review_count >= 3
    ) THEN
      -- Graduate: remove from queue entirely
      DELETE FROM review_queue
      WHERE user_id = NEW.user_id AND problem_slug = NEW.problem_slug;
    ELSE
      -- Advance spaced repetition interval (treat accepted submission as successful review)
      UPDATE review_queue
      SET
        interval_days = LEAST(interval_days * 2, 30),
        next_review = NOW() + (LEAST(interval_days * 2, 30) || ' days')::INTERVAL,
        review_count = review_count + 1,
        last_reviewed = NOW()
      WHERE user_id = NEW.user_id
        AND problem_slug = NEW.problem_slug;
    END IF;
  ELSE
    -- Failed submission: add to review queue or reset interval if already there
    INSERT INTO review_queue (user_id, problem_slug, problem_title, reason, next_review, interval_days)
    VALUES (
      NEW.user_id,
      NEW.problem_slug,
      NEW.problem_title,
      NEW.status,
      NOW() + INTERVAL '1 day',
      1
    )
    ON CONFLICT (user_id, problem_slug) DO UPDATE SET
      reason = EXCLUDED.reason,
      interval_days = 1,
      next_review = NOW() + INTERVAL '1 day';
  END IF;

  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- 4. Update complete_review with graduation logic
CREATE OR REPLACE FUNCTION complete_review(p_review_id UUID, p_success BOOLEAN)
RETURNS VOID AS $$
DECLARE
  current_interval INTEGER;
  current_count INTEGER;
  new_interval INTEGER;
BEGIN
  SELECT interval_days, review_count
  INTO current_interval, current_count
  FROM review_queue
  WHERE id = p_review_id;

  IF NOT FOUND THEN
    RETURN;
  END IF;

  IF p_success THEN
    -- Graduate if at high interval and reviewed enough times
    IF current_interval >= 16 AND current_count >= 3 THEN
      DELETE FROM review_queue WHERE id = p_review_id;
      RETURN;
    END IF;

    new_interval := LEAST(current_interval * 2, 30);
  ELSE
    new_interval := 1;
  END IF;

  UPDATE review_queue
  SET
    interval_days = new_interval,
    next_review = NOW() + (new_interval || ' days')::INTERVAL,
    review_count = review_count + 1,
    last_reviewed = NOW()
  WHERE id = p_review_id;
END;
$$ LANGUAGE plpgsql;
