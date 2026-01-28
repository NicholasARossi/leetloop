-- Meta Objectives Schema
-- Tables for career goal tracking and pace management

-- =============================================================================
-- Objective Templates - Pre-built company targets
-- =============================================================================
CREATE TABLE IF NOT EXISTS objective_templates (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name TEXT NOT NULL UNIQUE,              -- "Google L5 SWE"
  company TEXT NOT NULL,
  role TEXT NOT NULL,
  level TEXT,
  description TEXT,

  -- Skill targets based on interview patterns
  required_skills JSONB NOT NULL DEFAULT '{}',
  recommended_path_ids UUID[] DEFAULT '{}',
  difficulty_distribution JSONB DEFAULT '{"Easy": 0.2, "Medium": 0.6, "Hard": 0.2}',
  estimated_weeks INTEGER DEFAULT 12,

  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- =============================================================================
-- Meta Objectives - User's active career goal
-- =============================================================================
CREATE TABLE IF NOT EXISTS meta_objectives (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL UNIQUE,  -- One active objective per user

  -- Goal definition
  title TEXT NOT NULL,                    -- "Google ML Engineer L5"
  target_company TEXT NOT NULL,           -- "Google"
  target_role TEXT NOT NULL,              -- "ML Engineer"
  target_level TEXT,                      -- "L5"

  -- Timeline (required)
  target_deadline DATE NOT NULL,
  started_at TIMESTAMPTZ DEFAULT NOW(),

  -- Volume targets
  weekly_problem_target INTEGER DEFAULT 25,
  daily_problem_minimum INTEGER DEFAULT 4,

  -- Skill requirements (domain -> target score)
  required_skills JSONB NOT NULL DEFAULT '{}',

  -- Associated learning paths
  path_ids UUID[] DEFAULT '{}',

  -- Template reference (optional)
  template_id UUID REFERENCES objective_templates(id),

  status TEXT DEFAULT 'active' CHECK (status IN ('active', 'paused', 'completed')),
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- =============================================================================
-- Objective Progress - Daily progress tracking
-- =============================================================================
CREATE TABLE IF NOT EXISTS objective_progress (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL,
  objective_id UUID NOT NULL REFERENCES meta_objectives(id) ON DELETE CASCADE,
  progress_date DATE NOT NULL,

  -- Daily metrics
  problems_completed INTEGER DEFAULT 0,
  problems_attempted INTEGER DEFAULT 0,

  -- Cumulative tracking
  cumulative_problems INTEGER DEFAULT 0,
  target_cumulative INTEGER DEFAULT 0,
  pace_status TEXT DEFAULT 'on_track' CHECK (pace_status IN ('ahead', 'on_track', 'behind', 'critical')),

  created_at TIMESTAMPTZ DEFAULT NOW(),

  UNIQUE(user_id, objective_id, progress_date)
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_meta_objectives_user_id ON meta_objectives(user_id);
CREATE INDEX IF NOT EXISTS idx_meta_objectives_status ON meta_objectives(status);
CREATE INDEX IF NOT EXISTS idx_objective_progress_user_id ON objective_progress(user_id);
CREATE INDEX IF NOT EXISTS idx_objective_progress_objective_id ON objective_progress(objective_id);
CREATE INDEX IF NOT EXISTS idx_objective_progress_date ON objective_progress(progress_date);

-- =============================================================================
-- Row Level Security
-- =============================================================================
ALTER TABLE objective_templates ENABLE ROW LEVEL SECURITY;
ALTER TABLE meta_objectives ENABLE ROW LEVEL SECURITY;
ALTER TABLE objective_progress ENABLE ROW LEVEL SECURITY;

-- Templates are readable by everyone
CREATE POLICY "Anyone can view objective templates"
  ON objective_templates FOR SELECT
  USING (true);

-- Meta objectives policies
CREATE POLICY "Users can view own objectives"
  ON meta_objectives FOR SELECT
  USING (auth.uid() = user_id);

CREATE POLICY "Users can insert own objectives"
  ON meta_objectives FOR INSERT
  WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update own objectives"
  ON meta_objectives FOR UPDATE
  USING (auth.uid() = user_id);

CREATE POLICY "Users can delete own objectives"
  ON meta_objectives FOR DELETE
  USING (auth.uid() = user_id);

-- Objective progress policies
CREATE POLICY "Users can view own progress"
  ON objective_progress FOR SELECT
  USING (auth.uid() = user_id);

CREATE POLICY "Users can insert own progress"
  ON objective_progress FOR INSERT
  WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update own progress"
  ON objective_progress FOR UPDATE
  USING (auth.uid() = user_id);

-- =============================================================================
-- Seed Data - Company Templates
-- =============================================================================
INSERT INTO objective_templates (name, company, role, level, description, required_skills, estimated_weeks) VALUES
(
  'Google L5 SWE',
  'Google',
  'Software Engineer',
  'L5',
  'Senior Software Engineer at Google. Requires strong fundamentals across all DSA domains with emphasis on system design thinking.',
  '{"Dynamic Programming": 85, "Graphs": 85, "Trees": 90, "Binary Search": 85, "Arrays & Hashing": 90}',
  16
),
(
  'Google L4 SWE',
  'Google',
  'Software Engineer',
  'L4',
  'Software Engineer at Google. Solid foundation in core algorithms with good problem-solving speed.',
  '{"Dynamic Programming": 75, "Graphs": 75, "Trees": 80, "Binary Search": 80, "Arrays & Hashing": 85}',
  12
),
(
  'Meta E5 SWE',
  'Meta',
  'Software Engineer',
  'E5',
  'Senior Software Engineer at Meta. Strong emphasis on tree/graph problems and behavioral rounds.',
  '{"Dynamic Programming": 85, "Trees": 85, "Graphs": 80, "Arrays & Hashing": 85, "Sliding Window": 80}',
  14
),
(
  'Amazon SDE2',
  'Amazon',
  'Software Development Engineer',
  'SDE2',
  'SDE II at Amazon. Leadership principles matter as much as coding. Focus on clean, working solutions.',
  '{"Arrays & Hashing": 85, "Trees": 80, "Dynamic Programming": 75, "Graphs": 75, "Heap": 80}',
  12
),
(
  'Microsoft L63 SWE',
  'Microsoft',
  'Software Engineer',
  'L63',
  'Senior Software Engineer at Microsoft. Balanced preparation across domains with focus on communication.',
  '{"Arrays & Hashing": 80, "Trees": 80, "Dynamic Programming": 75, "Graphs": 75, "Binary Search": 80}',
  10
),
(
  'Apple ICT4 SWE',
  'Apple',
  'Software Engineer',
  'ICT4',
  'Software Engineer at Apple. Deep understanding of data structures and algorithm tradeoffs.',
  '{"Arrays & Hashing": 85, "Trees": 85, "Linked Lists": 80, "Stacks": 80, "Binary Search": 80}',
  12
)
ON CONFLICT (name) DO NOTHING;

-- =============================================================================
-- Function to update objective progress on submission
-- =============================================================================
CREATE OR REPLACE FUNCTION update_objective_progress_on_submission()
RETURNS TRIGGER AS $$
DECLARE
  v_objective RECORD;
  v_today DATE := CURRENT_DATE;
  v_problems_today INTEGER;
  v_cumulative INTEGER;
  v_days_elapsed INTEGER;
  v_days_total INTEGER;
  v_expected_problems INTEGER;
  v_pace TEXT;
BEGIN
  -- Only process accepted submissions
  IF NEW.status != 'Accepted' THEN
    RETURN NEW;
  END IF;

  -- Find user's active objective
  SELECT * INTO v_objective
  FROM meta_objectives
  WHERE user_id = NEW.user_id AND status = 'active'
  LIMIT 1;

  IF NOT FOUND THEN
    RETURN NEW;
  END IF;

  -- Count problems completed today (unique problem slugs with accepted status)
  SELECT COUNT(DISTINCT problem_slug) INTO v_problems_today
  FROM submissions
  WHERE user_id = NEW.user_id
    AND status = 'Accepted'
    AND DATE(submitted_at) = v_today;

  -- Count cumulative unique problems solved since objective started
  SELECT COUNT(DISTINCT problem_slug) INTO v_cumulative
  FROM submissions
  WHERE user_id = NEW.user_id
    AND status = 'Accepted'
    AND submitted_at >= v_objective.started_at;

  -- Calculate pace status
  v_days_elapsed := GREATEST(1, v_today - DATE(v_objective.started_at));
  v_days_total := GREATEST(1, v_objective.target_deadline - DATE(v_objective.started_at));
  v_expected_problems := CEIL((v_days_elapsed::FLOAT / v_days_total) * (v_objective.weekly_problem_target * (v_days_total / 7.0)));

  IF v_cumulative >= v_expected_problems * 1.1 THEN
    v_pace := 'ahead';
  ELSIF v_cumulative >= v_expected_problems * 0.9 THEN
    v_pace := 'on_track';
  ELSIF v_cumulative >= v_expected_problems * 0.7 THEN
    v_pace := 'behind';
  ELSE
    v_pace := 'critical';
  END IF;

  -- Upsert progress record
  INSERT INTO objective_progress (
    user_id,
    objective_id,
    progress_date,
    problems_completed,
    problems_attempted,
    cumulative_problems,
    target_cumulative,
    pace_status
  ) VALUES (
    NEW.user_id,
    v_objective.id,
    v_today,
    v_problems_today,
    v_problems_today, -- We'll count attempts properly later
    v_cumulative,
    v_expected_problems,
    v_pace
  )
  ON CONFLICT (user_id, objective_id, progress_date) DO UPDATE SET
    problems_completed = EXCLUDED.problems_completed,
    cumulative_problems = EXCLUDED.cumulative_problems,
    target_cumulative = EXCLUDED.target_cumulative,
    pace_status = EXCLUDED.pace_status;

  RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Create trigger on submissions table
DROP TRIGGER IF EXISTS on_submission_update_objective ON submissions;
CREATE TRIGGER on_submission_update_objective
AFTER INSERT ON submissions
FOR EACH ROW EXECUTE FUNCTION update_objective_progress_on_submission();
