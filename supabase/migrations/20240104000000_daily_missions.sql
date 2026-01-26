-- Daily Missions Schema
-- Tables for Mission Control dashboard with LLM-generated daily objectives

-- Daily missions - stores pre-generated daily missions per user
CREATE TABLE IF NOT EXISTS daily_missions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL,
  mission_date DATE NOT NULL,
  -- Daily objective
  objective_title TEXT NOT NULL,
  objective_description TEXT,
  objective_skill_tags TEXT[] DEFAULT '{}',
  -- Main quests from learning path
  -- Format: [{slug, title, difficulty, category, order, status}]
  main_quests JSONB NOT NULL DEFAULT '[]',
  -- Side quests targeting weaknesses
  -- Format: [{slug, title, difficulty, reason, source_problem_slug, target_weakness}]
  side_quests JSONB NOT NULL DEFAULT '[]',
  -- Completed problem slugs (tracked separately for daily reset)
  completed_main_quests TEXT[] DEFAULT '{}',
  completed_side_quests TEXT[] DEFAULT '{}',
  -- Regeneration tracking (max 3/day)
  regenerated_count INTEGER DEFAULT 0,
  -- Metadata
  generated_at TIMESTAMPTZ DEFAULT NOW(),
  generation_context JSONB DEFAULT '{}',
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE(user_id, mission_date)
);

CREATE INDEX IF NOT EXISTS idx_daily_missions_user_id ON daily_missions(user_id);
CREATE INDEX IF NOT EXISTS idx_daily_missions_mission_date ON daily_missions(mission_date);
CREATE INDEX IF NOT EXISTS idx_daily_missions_user_date ON daily_missions(user_id, mission_date);

-- Problem attempt stats - tracks per-problem metrics to identify slow solves and struggles
CREATE TABLE IF NOT EXISTS problem_attempt_stats (
  user_id UUID NOT NULL,
  problem_slug TEXT NOT NULL,
  problem_title TEXT,
  difficulty TEXT CHECK (difficulty IN ('Easy', 'Medium', 'Hard')),
  -- Attempt counts
  total_attempts INTEGER DEFAULT 0,
  successful_attempts INTEGER DEFAULT 0,
  failed_attempts INTEGER DEFAULT 0,
  -- Timing
  first_attempt_at TIMESTAMPTZ,
  first_success_at TIMESTAMPTZ,
  last_attempt_at TIMESTAMPTZ,
  time_to_first_success_seconds INTEGER,  -- NULL if never succeeded
  -- Flags for identifying struggle points
  is_slow_solve BOOLEAN DEFAULT FALSE,  -- >5 attempts OR >30 min to first success
  is_struggle BOOLEAN DEFAULT FALSE,     -- Currently failing (2+ failed, no success)
  -- Metadata
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW(),
  PRIMARY KEY (user_id, problem_slug)
);

CREATE INDEX IF NOT EXISTS idx_problem_attempt_stats_user_id ON problem_attempt_stats(user_id);
CREATE INDEX IF NOT EXISTS idx_problem_attempt_stats_slow_solve ON problem_attempt_stats(user_id, is_slow_solve) WHERE is_slow_solve = TRUE;
CREATE INDEX IF NOT EXISTS idx_problem_attempt_stats_struggle ON problem_attempt_stats(user_id, is_struggle) WHERE is_struggle = TRUE;

-- Function to update problem attempt stats on submission
CREATE OR REPLACE FUNCTION update_problem_attempt_stats()
RETURNS TRIGGER AS $$
DECLARE
  v_stats RECORD;
  v_time_to_success INTEGER;
  v_is_slow BOOLEAN;
  v_is_struggle BOOLEAN;
BEGIN
  -- Get existing stats or defaults
  SELECT * INTO v_stats
  FROM problem_attempt_stats
  WHERE user_id = NEW.user_id AND problem_slug = NEW.problem_slug;

  IF NOT FOUND THEN
    -- First attempt on this problem
    v_is_slow := FALSE;
    v_is_struggle := (NEW.status != 'Accepted');

    INSERT INTO problem_attempt_stats (
      user_id, problem_slug, problem_title, difficulty,
      total_attempts, successful_attempts, failed_attempts,
      first_attempt_at, last_attempt_at,
      first_success_at, time_to_first_success_seconds,
      is_slow_solve, is_struggle
    ) VALUES (
      NEW.user_id, NEW.problem_slug, NEW.problem_title, NEW.difficulty,
      1,
      CASE WHEN NEW.status = 'Accepted' THEN 1 ELSE 0 END,
      CASE WHEN NEW.status != 'Accepted' THEN 1 ELSE 0 END,
      NEW.submitted_at, NEW.submitted_at,
      CASE WHEN NEW.status = 'Accepted' THEN NEW.submitted_at ELSE NULL END,
      CASE WHEN NEW.status = 'Accepted' THEN 0 ELSE NULL END,
      FALSE,
      v_is_struggle
    );
  ELSE
    -- Update existing stats
    v_time_to_success := v_stats.time_to_first_success_seconds;

    -- If first success, calculate time to success
    IF NEW.status = 'Accepted' AND v_stats.first_success_at IS NULL THEN
      v_time_to_success := EXTRACT(EPOCH FROM (NEW.submitted_at - v_stats.first_attempt_at))::INTEGER;
    END IF;

    -- Calculate slow solve: >5 attempts OR >30 min to first success
    v_is_slow := (
      (v_stats.total_attempts + 1) > 5 OR
      (v_time_to_success IS NOT NULL AND v_time_to_success > 1800)
    );

    -- Calculate struggle: 2+ failed attempts without any success
    IF NEW.status = 'Accepted' THEN
      v_is_struggle := FALSE;
    ELSE
      v_is_struggle := (
        v_stats.successful_attempts = 0 AND
        (v_stats.failed_attempts + 1) >= 2
      );
    END IF;

    UPDATE problem_attempt_stats
    SET
      total_attempts = total_attempts + 1,
      successful_attempts = successful_attempts + CASE WHEN NEW.status = 'Accepted' THEN 1 ELSE 0 END,
      failed_attempts = failed_attempts + CASE WHEN NEW.status != 'Accepted' THEN 1 ELSE 0 END,
      last_attempt_at = NEW.submitted_at,
      first_success_at = COALESCE(first_success_at, CASE WHEN NEW.status = 'Accepted' THEN NEW.submitted_at ELSE NULL END),
      time_to_first_success_seconds = COALESCE(time_to_first_success_seconds, v_time_to_success),
      is_slow_solve = v_is_slow,
      is_struggle = v_is_struggle,
      updated_at = NOW()
    WHERE user_id = NEW.user_id AND problem_slug = NEW.problem_slug;
  END IF;

  -- Also update daily mission completion if applicable
  UPDATE daily_missions
  SET
    completed_main_quests = CASE
      WHEN NEW.status = 'Accepted' AND NEW.problem_slug = ANY(
        SELECT jsonb_array_elements_text(
          jsonb_path_query_array(main_quests, '$[*].slug')
        )
      )
      THEN array_append(
        array_remove(completed_main_quests, NEW.problem_slug),
        NEW.problem_slug
      )
      ELSE completed_main_quests
    END,
    completed_side_quests = CASE
      WHEN NEW.status = 'Accepted' AND NEW.problem_slug = ANY(
        SELECT jsonb_array_elements_text(
          jsonb_path_query_array(side_quests, '$[*].slug')
        )
      )
      THEN array_append(
        array_remove(completed_side_quests, NEW.problem_slug),
        NEW.problem_slug
      )
      ELSE completed_side_quests
    END,
    updated_at = NOW()
  WHERE user_id = NEW.user_id
    AND mission_date = CURRENT_DATE
    AND NEW.status = 'Accepted';

  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Create trigger on submissions
DROP TRIGGER IF EXISTS trg_update_problem_attempt_stats ON submissions;
CREATE TRIGGER trg_update_problem_attempt_stats
  AFTER INSERT ON submissions
  FOR EACH ROW
  EXECUTE FUNCTION update_problem_attempt_stats();

-- Enable RLS
ALTER TABLE daily_missions ENABLE ROW LEVEL SECURITY;
ALTER TABLE problem_attempt_stats ENABLE ROW LEVEL SECURITY;

-- RLS Policies for daily_missions
CREATE POLICY "Users can view own daily missions"
  ON daily_missions FOR SELECT
  USING (auth.uid() = user_id);

CREATE POLICY "Users can insert own daily missions"
  ON daily_missions FOR INSERT
  WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update own daily missions"
  ON daily_missions FOR UPDATE
  USING (auth.uid() = user_id);

-- RLS Policies for problem_attempt_stats
CREATE POLICY "Users can view own problem stats"
  ON problem_attempt_stats FOR SELECT
  USING (auth.uid() = user_id);

CREATE POLICY "Users can insert own problem stats"
  ON problem_attempt_stats FOR INSERT
  WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update own problem stats"
  ON problem_attempt_stats FOR UPDATE
  USING (auth.uid() = user_id);

-- Service role policies for batch operations
CREATE POLICY "Service role full access to daily_missions"
  ON daily_missions FOR ALL
  USING (auth.role() = 'service_role');

CREATE POLICY "Service role full access to problem_attempt_stats"
  ON problem_attempt_stats FOR ALL
  USING (auth.role() = 'service_role');
