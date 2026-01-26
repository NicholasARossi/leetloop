-- Anonymous Access Policies for Learning Paths
-- Allows guest users to track path progress

-- Drop existing RLS policies for user_path_progress
DROP POLICY IF EXISTS "Users can view own path progress" ON user_path_progress;
DROP POLICY IF EXISTS "Users can insert own path progress" ON user_path_progress;
DROP POLICY IF EXISTS "Users can update own path progress" ON user_path_progress;
DROP POLICY IF EXISTS "Users can delete own path progress" ON user_path_progress;

-- Allow anonymous access on user_path_progress
CREATE POLICY "Allow anonymous insert" ON user_path_progress
  FOR INSERT WITH CHECK (true);

CREATE POLICY "Allow anonymous select" ON user_path_progress
  FOR SELECT USING (true);

CREATE POLICY "Allow anonymous update" ON user_path_progress
  FOR UPDATE USING (true);

CREATE POLICY "Allow anonymous delete" ON user_path_progress
  FOR DELETE USING (true);

-- Drop existing RLS policies for user_streaks
DROP POLICY IF EXISTS "Users can view own streaks" ON user_streaks;
DROP POLICY IF EXISTS "Users can insert own streaks" ON user_streaks;
DROP POLICY IF EXISTS "Users can update own streaks" ON user_streaks;

-- Allow anonymous access on user_streaks
CREATE POLICY "Allow anonymous insert" ON user_streaks
  FOR INSERT WITH CHECK (true);

CREATE POLICY "Allow anonymous select" ON user_streaks
  FOR SELECT USING (true);

CREATE POLICY "Allow anonymous update" ON user_streaks
  FOR UPDATE USING (true);

-- For user_settings (add if not exists)
DROP POLICY IF EXISTS "Users can view own settings" ON user_settings;
DROP POLICY IF EXISTS "Users can insert own settings" ON user_settings;
DROP POLICY IF EXISTS "Users can update own settings" ON user_settings;

CREATE POLICY "Allow anonymous insert" ON user_settings
  FOR INSERT WITH CHECK (true);

CREATE POLICY "Allow anonymous select" ON user_settings
  FOR SELECT USING (true);

CREATE POLICY "Allow anonymous update" ON user_settings
  FOR UPDATE USING (true);
