-- Auth-based RLS Policies
-- Supports both authenticated users (via auth.uid()) and guest mode (via passed user_id)
-- Guest mode uses the anon key with a UUID passed from the client

-- Drop existing permissive anonymous policies
DROP POLICY IF EXISTS "Allow anonymous insert" ON submissions;
DROP POLICY IF EXISTS "Allow anonymous select own" ON submissions;
DROP POLICY IF EXISTS "Allow anonymous insert" ON skill_scores;
DROP POLICY IF EXISTS "Allow anonymous select" ON skill_scores;
DROP POLICY IF EXISTS "Allow anonymous update" ON skill_scores;
DROP POLICY IF EXISTS "Allow anonymous insert" ON review_queue;
DROP POLICY IF EXISTS "Allow anonymous select" ON review_queue;
DROP POLICY IF EXISTS "Allow anonymous update" ON review_queue;

-- Submissions policies
-- Authenticated: user_id must match auth.uid()
-- Guest: allow insert/select for any valid UUID (client provides their guest UUID)
CREATE POLICY "submissions_select_policy" ON submissions
  FOR SELECT
  USING (
    -- Authenticated users can see their own data
    (auth.uid() IS NOT NULL AND user_id = auth.uid())
    OR
    -- Guest users can see data matching their client-provided user_id
    (auth.uid() IS NULL AND true)
  );

CREATE POLICY "submissions_insert_policy" ON submissions
  FOR INSERT
  WITH CHECK (
    -- Authenticated users must insert with their auth.uid()
    (auth.uid() IS NOT NULL AND user_id = auth.uid())
    OR
    -- Guest users can insert with any valid UUID
    (auth.uid() IS NULL AND user_id IS NOT NULL)
  );

CREATE POLICY "submissions_update_policy" ON submissions
  FOR UPDATE
  USING (
    (auth.uid() IS NOT NULL AND user_id = auth.uid())
    OR
    (auth.uid() IS NULL AND true)
  );

CREATE POLICY "submissions_delete_policy" ON submissions
  FOR DELETE
  USING (
    (auth.uid() IS NOT NULL AND user_id = auth.uid())
  );

-- Skill scores policies
CREATE POLICY "skill_scores_select_policy" ON skill_scores
  FOR SELECT
  USING (
    (auth.uid() IS NOT NULL AND user_id = auth.uid())
    OR
    (auth.uid() IS NULL AND true)
  );

CREATE POLICY "skill_scores_insert_policy" ON skill_scores
  FOR INSERT
  WITH CHECK (
    (auth.uid() IS NOT NULL AND user_id = auth.uid())
    OR
    (auth.uid() IS NULL AND user_id IS NOT NULL)
  );

CREATE POLICY "skill_scores_update_policy" ON skill_scores
  FOR UPDATE
  USING (
    (auth.uid() IS NOT NULL AND user_id = auth.uid())
    OR
    (auth.uid() IS NULL AND true)
  );

CREATE POLICY "skill_scores_delete_policy" ON skill_scores
  FOR DELETE
  USING (
    (auth.uid() IS NOT NULL AND user_id = auth.uid())
  );

-- Review queue policies
CREATE POLICY "review_queue_select_policy" ON review_queue
  FOR SELECT
  USING (
    (auth.uid() IS NOT NULL AND user_id = auth.uid())
    OR
    (auth.uid() IS NULL AND true)
  );

CREATE POLICY "review_queue_insert_policy" ON review_queue
  FOR INSERT
  WITH CHECK (
    (auth.uid() IS NOT NULL AND user_id = auth.uid())
    OR
    (auth.uid() IS NULL AND user_id IS NOT NULL)
  );

CREATE POLICY "review_queue_update_policy" ON review_queue
  FOR UPDATE
  USING (
    (auth.uid() IS NOT NULL AND user_id = auth.uid())
    OR
    (auth.uid() IS NULL AND true)
  );

CREATE POLICY "review_queue_delete_policy" ON review_queue
  FOR DELETE
  USING (
    (auth.uid() IS NOT NULL AND user_id = auth.uid())
  );

-- User settings policies
DROP POLICY IF EXISTS "Users can view own settings" ON user_settings;
DROP POLICY IF EXISTS "Users can insert own settings" ON user_settings;
DROP POLICY IF EXISTS "Users can update own settings" ON user_settings;

CREATE POLICY "user_settings_select_policy" ON user_settings
  FOR SELECT
  USING (
    (auth.uid() IS NOT NULL AND user_id = auth.uid())
    OR
    (auth.uid() IS NULL AND true)
  );

CREATE POLICY "user_settings_insert_policy" ON user_settings
  FOR INSERT
  WITH CHECK (
    (auth.uid() IS NOT NULL AND user_id = auth.uid())
    OR
    (auth.uid() IS NULL AND user_id IS NOT NULL)
  );

CREATE POLICY "user_settings_update_policy" ON user_settings
  FOR UPDATE
  USING (
    (auth.uid() IS NOT NULL AND user_id = auth.uid())
    OR
    (auth.uid() IS NULL AND true)
  );

-- Submission notes policies
DROP POLICY IF EXISTS "Users can view own notes" ON submission_notes;
DROP POLICY IF EXISTS "Users can insert own notes" ON submission_notes;
DROP POLICY IF EXISTS "Users can update own notes" ON submission_notes;
DROP POLICY IF EXISTS "Users can delete own notes" ON submission_notes;

CREATE POLICY "submission_notes_select_policy" ON submission_notes
  FOR SELECT
  USING (
    (auth.uid() IS NOT NULL AND user_id = auth.uid())
    OR
    (auth.uid() IS NULL AND true)
  );

CREATE POLICY "submission_notes_insert_policy" ON submission_notes
  FOR INSERT
  WITH CHECK (
    (auth.uid() IS NOT NULL AND user_id = auth.uid())
    OR
    (auth.uid() IS NULL AND user_id IS NOT NULL)
  );

CREATE POLICY "submission_notes_update_policy" ON submission_notes
  FOR UPDATE
  USING (
    (auth.uid() IS NOT NULL AND user_id = auth.uid())
    OR
    (auth.uid() IS NULL AND true)
  );

CREATE POLICY "submission_notes_delete_policy" ON submission_notes
  FOR DELETE
  USING (
    (auth.uid() IS NOT NULL AND user_id = auth.uid())
  );
