-- Daily Missions v2 Schema
-- Enhanced for Gemini-driven mission generation with detailed reasoning

-- =============================================================================
-- Add new columns to daily_missions for Gemini outputs
-- =============================================================================
ALTER TABLE daily_missions
  ADD COLUMN IF NOT EXISTS daily_objective TEXT,
  ADD COLUMN IF NOT EXISTS balance_explanation TEXT,
  ADD COLUMN IF NOT EXISTS pacing_status TEXT CHECK (pacing_status IN ('ahead', 'on_track', 'behind', 'critical')),
  ADD COLUMN IF NOT EXISTS pacing_note TEXT,
  ADD COLUMN IF NOT EXISTS gemini_response JSONB;

-- =============================================================================
-- Mission Problems - Individual problems in a mission with reasoning
-- =============================================================================
CREATE TABLE IF NOT EXISTS mission_problems (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  mission_id UUID NOT NULL REFERENCES daily_missions(id) ON DELETE CASCADE,
  problem_id TEXT NOT NULL,           -- LeetCode problem slug

  -- Problem metadata (denormalized for display)
  problem_title TEXT,
  difficulty TEXT CHECK (difficulty IN ('Easy', 'Medium', 'Hard')),

  -- Gemini's selection rationale
  source TEXT NOT NULL CHECK (source IN ('path', 'gap_fill', 'review', 'reinforcement')),
  reasoning TEXT NOT NULL,            -- WHY this problem was chosen
  priority INTEGER NOT NULL,          -- 1 = most important
  skills TEXT[] DEFAULT '{}',         -- Skills this problem targets
  estimated_difficulty TEXT CHECK (estimated_difficulty IN ('easy', 'medium', 'hard')),

  -- Completion tracking
  completed BOOLEAN DEFAULT FALSE,
  completed_at TIMESTAMPTZ,

  created_at TIMESTAMPTZ DEFAULT NOW(),

  UNIQUE(mission_id, problem_id)
);

-- Indexes for mission_problems
CREATE INDEX IF NOT EXISTS idx_mission_problems_mission_id ON mission_problems(mission_id);
CREATE INDEX IF NOT EXISTS idx_mission_problems_source ON mission_problems(source);
CREATE INDEX IF NOT EXISTS idx_mission_problems_priority ON mission_problems(mission_id, priority);
CREATE INDEX IF NOT EXISTS idx_mission_problems_completed ON mission_problems(mission_id, completed);

-- =============================================================================
-- Row Level Security for mission_problems
-- =============================================================================
ALTER TABLE mission_problems ENABLE ROW LEVEL SECURITY;

-- Users can view problems for their missions
CREATE POLICY "Users can view own mission problems"
  ON mission_problems FOR SELECT
  USING (
    EXISTS (
      SELECT 1 FROM daily_missions dm
      WHERE dm.id = mission_problems.mission_id
      AND dm.user_id = auth.uid()
    )
  );

-- Users can insert problems for their missions
CREATE POLICY "Users can insert own mission problems"
  ON mission_problems FOR INSERT
  WITH CHECK (
    EXISTS (
      SELECT 1 FROM daily_missions dm
      WHERE dm.id = mission_problems.mission_id
      AND dm.user_id = auth.uid()
    )
  );

-- Users can update problems for their missions
CREATE POLICY "Users can update own mission problems"
  ON mission_problems FOR UPDATE
  USING (
    EXISTS (
      SELECT 1 FROM daily_missions dm
      WHERE dm.id = mission_problems.mission_id
      AND dm.user_id = auth.uid()
    )
  );

-- Service role full access
CREATE POLICY "Service role full access to mission_problems"
  ON mission_problems FOR ALL
  USING (auth.role() = 'service_role');

-- =============================================================================
-- Function to mark mission problem complete on submission
-- =============================================================================
CREATE OR REPLACE FUNCTION update_mission_problem_on_submission()
RETURNS TRIGGER AS $$
BEGIN
  -- Only process accepted submissions
  IF NEW.status != 'Accepted' THEN
    RETURN NEW;
  END IF;

  -- Update mission_problems if this problem is in today's mission
  UPDATE mission_problems mp
  SET
    completed = TRUE,
    completed_at = NEW.submitted_at
  FROM daily_missions dm
  WHERE mp.mission_id = dm.id
    AND dm.user_id = NEW.user_id
    AND dm.mission_date = CURRENT_DATE
    AND mp.problem_id = NEW.problem_slug
    AND mp.completed = FALSE;

  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger to auto-complete mission problems
DROP TRIGGER IF EXISTS trg_update_mission_problem ON submissions;
CREATE TRIGGER trg_update_mission_problem
  AFTER INSERT ON submissions
  FOR EACH ROW
  EXECUTE FUNCTION update_mission_problem_on_submission();
