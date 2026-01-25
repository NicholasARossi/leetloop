-- Row Level Security Policies
-- Users can only see and modify their own data

-- Enable RLS on all tables
ALTER TABLE submissions ENABLE ROW LEVEL SECURITY;
ALTER TABLE skill_scores ENABLE ROW LEVEL SECURITY;
ALTER TABLE review_queue ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_settings ENABLE ROW LEVEL SECURITY;
ALTER TABLE submission_notes ENABLE ROW LEVEL SECURITY;

-- Submissions policies
CREATE POLICY "Users can view own submissions"
  ON submissions FOR SELECT
  USING (auth.uid() = user_id);

CREATE POLICY "Users can insert own submissions"
  ON submissions FOR INSERT
  WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update own submissions"
  ON submissions FOR UPDATE
  USING (auth.uid() = user_id);

CREATE POLICY "Users can delete own submissions"
  ON submissions FOR DELETE
  USING (auth.uid() = user_id);

-- Skill scores policies
CREATE POLICY "Users can view own skill scores"
  ON skill_scores FOR SELECT
  USING (auth.uid() = user_id);

CREATE POLICY "Users can insert own skill scores"
  ON skill_scores FOR INSERT
  WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update own skill scores"
  ON skill_scores FOR UPDATE
  USING (auth.uid() = user_id);

-- Review queue policies
CREATE POLICY "Users can view own review queue"
  ON review_queue FOR SELECT
  USING (auth.uid() = user_id);

CREATE POLICY "Users can insert own review items"
  ON review_queue FOR INSERT
  WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update own review items"
  ON review_queue FOR UPDATE
  USING (auth.uid() = user_id);

CREATE POLICY "Users can delete own review items"
  ON review_queue FOR DELETE
  USING (auth.uid() = user_id);

-- User settings policies
CREATE POLICY "Users can view own settings"
  ON user_settings FOR SELECT
  USING (auth.uid() = user_id);

CREATE POLICY "Users can insert own settings"
  ON user_settings FOR INSERT
  WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update own settings"
  ON user_settings FOR UPDATE
  USING (auth.uid() = user_id);

-- Submission notes policies
CREATE POLICY "Users can view own notes"
  ON submission_notes FOR SELECT
  USING (auth.uid() = user_id);

CREATE POLICY "Users can insert own notes"
  ON submission_notes FOR INSERT
  WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update own notes"
  ON submission_notes FOR UPDATE
  USING (auth.uid() = user_id);

CREATE POLICY "Users can delete own notes"
  ON submission_notes FOR DELETE
  USING (auth.uid() = user_id);
