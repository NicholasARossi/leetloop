-- Learning Paths Schema
-- Tables for curriculum tracking (NeetCode 150, Blind 75, etc.)

-- Available learning paths (NeetCode 150, Blind 75, etc.)
CREATE TABLE IF NOT EXISTS learning_paths (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name TEXT NOT NULL UNIQUE,
  description TEXT,
  total_problems INTEGER NOT NULL DEFAULT 0,
  categories JSONB NOT NULL DEFAULT '[]',
  -- categories format: [{"name": "Arrays & Hashing", "order": 1, "problems": [...]}]
  -- problems format: [{"slug": "two-sum", "title": "Two Sum", "difficulty": "Easy", "order": 1}]
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- User progress on a specific learning path
CREATE TABLE IF NOT EXISTS user_path_progress (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL,
  path_id UUID NOT NULL REFERENCES learning_paths(id) ON DELETE CASCADE,
  completed_problems TEXT[] DEFAULT '{}',  -- Array of problem slugs
  current_category TEXT,
  started_at TIMESTAMPTZ DEFAULT NOW(),
  last_activity_at TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE(user_id, path_id)
);

CREATE INDEX IF NOT EXISTS idx_user_path_progress_user_id ON user_path_progress(user_id);
CREATE INDEX IF NOT EXISTS idx_user_path_progress_path_id ON user_path_progress(path_id);

-- User streaks tracking
CREATE TABLE IF NOT EXISTS user_streaks (
  user_id UUID PRIMARY KEY,
  current_streak INTEGER DEFAULT 0,
  longest_streak INTEGER DEFAULT 0,
  last_activity_date DATE,
  streak_history JSONB DEFAULT '[]',  -- [{date, problems_completed}]
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Add current_path_id to user_settings
ALTER TABLE user_settings
ADD COLUMN IF NOT EXISTS current_path_id UUID REFERENCES learning_paths(id);

-- Enable RLS on new tables
ALTER TABLE learning_paths ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_path_progress ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_streaks ENABLE ROW LEVEL SECURITY;

-- Learning paths policies (everyone can read, only system can write)
CREATE POLICY "Anyone can view learning paths"
  ON learning_paths FOR SELECT
  USING (true);

-- User path progress policies
CREATE POLICY "Users can view own path progress"
  ON user_path_progress FOR SELECT
  USING (auth.uid() = user_id);

CREATE POLICY "Users can insert own path progress"
  ON user_path_progress FOR INSERT
  WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update own path progress"
  ON user_path_progress FOR UPDATE
  USING (auth.uid() = user_id);

CREATE POLICY "Users can delete own path progress"
  ON user_path_progress FOR DELETE
  USING (auth.uid() = user_id);

-- User streaks policies
CREATE POLICY "Users can view own streaks"
  ON user_streaks FOR SELECT
  USING (auth.uid() = user_id);

CREATE POLICY "Users can insert own streaks"
  ON user_streaks FOR INSERT
  WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update own streaks"
  ON user_streaks FOR UPDATE
  USING (auth.uid() = user_id);

-- Function to update streak on activity
CREATE OR REPLACE FUNCTION update_user_streak(p_user_id UUID)
RETURNS void AS $$
DECLARE
  v_last_date DATE;
  v_today DATE := CURRENT_DATE;
  v_current_streak INTEGER;
  v_longest_streak INTEGER;
BEGIN
  -- Get current streak info
  SELECT last_activity_date, current_streak, longest_streak
  INTO v_last_date, v_current_streak, v_longest_streak
  FROM user_streaks
  WHERE user_id = p_user_id;

  IF NOT FOUND THEN
    -- First activity ever
    INSERT INTO user_streaks (user_id, current_streak, longest_streak, last_activity_date)
    VALUES (p_user_id, 1, 1, v_today);
  ELSIF v_last_date = v_today THEN
    -- Already recorded today, do nothing
    NULL;
  ELSIF v_last_date = v_today - 1 THEN
    -- Consecutive day, increment streak
    v_current_streak := v_current_streak + 1;
    v_longest_streak := GREATEST(v_longest_streak, v_current_streak);
    UPDATE user_streaks
    SET current_streak = v_current_streak,
        longest_streak = v_longest_streak,
        last_activity_date = v_today,
        updated_at = NOW()
    WHERE user_id = p_user_id;
  ELSE
    -- Streak broken, reset to 1
    UPDATE user_streaks
    SET current_streak = 1,
        last_activity_date = v_today,
        updated_at = NOW()
    WHERE user_id = p_user_id;
  END IF;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;
