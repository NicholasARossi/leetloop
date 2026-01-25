-- Fix ambiguous column reference in update_skill_scores function
-- The variable 'tag' conflicts with the column name

CREATE OR REPLACE FUNCTION update_skill_scores()
RETURNS TRIGGER AS $$
DECLARE
  current_tag TEXT;
  current_score REAL;
  new_score REAL;
  is_success BOOLEAN;
BEGIN
  -- Check if submission was successful
  is_success := NEW.status = 'Accepted';

  -- Update skill score for each tag
  IF NEW.tags IS NOT NULL THEN
    FOREACH current_tag IN ARRAY NEW.tags
    LOOP
      -- Get current score or use default
      SELECT score INTO current_score
      FROM skill_scores
      WHERE user_id = NEW.user_id AND skill_scores.tag = current_tag;

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
        current_tag,
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
