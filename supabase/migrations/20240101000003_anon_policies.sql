-- Anonymous Access Policies for MVP
-- Allows the extension to insert data with anonymous user IDs
-- NOTE: Replace with proper auth-based RLS for production

-- Drop existing RLS policies
DROP POLICY IF EXISTS "Users can view own submissions" ON submissions;
DROP POLICY IF EXISTS "Users can insert own submissions" ON submissions;
DROP POLICY IF EXISTS "Users can update own submissions" ON submissions;
DROP POLICY IF EXISTS "Users can delete own submissions" ON submissions;

-- Allow anonymous inserts and selects on submissions
CREATE POLICY "Allow anonymous insert" ON submissions
  FOR INSERT WITH CHECK (true);

CREATE POLICY "Allow anonymous select own" ON submissions
  FOR SELECT USING (true);

-- For skill_scores
DROP POLICY IF EXISTS "Users can view own skill scores" ON skill_scores;
DROP POLICY IF EXISTS "Users can insert own skill scores" ON skill_scores;
DROP POLICY IF EXISTS "Users can update own skill scores" ON skill_scores;

CREATE POLICY "Allow anonymous insert" ON skill_scores
  FOR INSERT WITH CHECK (true);

CREATE POLICY "Allow anonymous select" ON skill_scores
  FOR SELECT USING (true);

CREATE POLICY "Allow anonymous update" ON skill_scores
  FOR UPDATE USING (true);

-- For review_queue
DROP POLICY IF EXISTS "Users can view own review queue" ON review_queue;
DROP POLICY IF EXISTS "Users can insert own review items" ON review_queue;
DROP POLICY IF EXISTS "Users can update own review items" ON review_queue;
DROP POLICY IF EXISTS "Users can delete own review items" ON review_queue;

CREATE POLICY "Allow anonymous insert" ON review_queue
  FOR INSERT WITH CHECK (true);

CREATE POLICY "Allow anonymous select" ON review_queue
  FOR SELECT USING (true);

CREATE POLICY "Allow anonymous update" ON review_queue
  FOR UPDATE USING (true);
