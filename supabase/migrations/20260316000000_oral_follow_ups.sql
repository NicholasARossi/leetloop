-- Follow-up question responses for oral system design sessions
-- Users can record audio answers to follow-up questions generated after grading

CREATE TABLE IF NOT EXISTS system_design_oral_follow_ups (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  question_id UUID NOT NULL REFERENCES system_design_oral_questions(id) ON DELETE CASCADE,
  follow_up_index INTEGER NOT NULL,
  follow_up_text TEXT NOT NULL,

  -- Grading results (populated after audio submission)
  transcript TEXT,
  score INTEGER CHECK (score IS NULL OR (score >= 1 AND score <= 10)),
  feedback TEXT,
  addressed_gap BOOLEAN,

  -- Status
  status TEXT DEFAULT 'pending' CHECK (status IN ('pending', 'graded')),
  created_at TIMESTAMPTZ DEFAULT NOW(),
  graded_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_oral_follow_ups_question_id ON system_design_oral_follow_ups(question_id);
CREATE UNIQUE INDEX IF NOT EXISTS idx_oral_follow_ups_question_index ON system_design_oral_follow_ups(question_id, follow_up_index);

ALTER TABLE system_design_oral_follow_ups ENABLE ROW LEVEL SECURITY;

-- Authenticated users can manage their own follow-ups (via question → session join)
CREATE POLICY "Users can view own oral follow-ups"
  ON system_design_oral_follow_ups FOR SELECT
  USING (EXISTS (
    SELECT 1 FROM system_design_oral_questions q
    JOIN system_design_oral_sessions s ON s.id = q.session_id
    WHERE q.id = question_id AND s.user_id = auth.uid()
  ));

CREATE POLICY "Users can insert own oral follow-ups"
  ON system_design_oral_follow_ups FOR INSERT
  WITH CHECK (EXISTS (
    SELECT 1 FROM system_design_oral_questions q
    JOIN system_design_oral_sessions s ON s.id = q.session_id
    WHERE q.id = question_id AND s.user_id = auth.uid()
  ));

CREATE POLICY "Users can update own oral follow-ups"
  ON system_design_oral_follow_ups FOR UPDATE
  USING (EXISTS (
    SELECT 1 FROM system_design_oral_questions q
    JOIN system_design_oral_sessions s ON s.id = q.session_id
    WHERE q.id = question_id AND s.user_id = auth.uid()
  ));

CREATE POLICY "Users can delete own oral follow-ups"
  ON system_design_oral_follow_ups FOR DELETE
  USING (EXISTS (
    SELECT 1 FROM system_design_oral_questions q
    JOIN system_design_oral_sessions s ON s.id = q.session_id
    WHERE q.id = question_id AND s.user_id = auth.uid()
  ));

-- Anon (API service key) can manage all follow-ups
CREATE POLICY "Anon can view all oral follow-ups"
  ON system_design_oral_follow_ups FOR SELECT TO anon
  USING (true);

CREATE POLICY "Anon can insert all oral follow-ups"
  ON system_design_oral_follow_ups FOR INSERT TO anon
  WITH CHECK (true);

CREATE POLICY "Anon can update all oral follow-ups"
  ON system_design_oral_follow_ups FOR UPDATE TO anon
  USING (true);

CREATE POLICY "Anon can delete all oral follow-ups"
  ON system_design_oral_follow_ups FOR DELETE TO anon
  USING (true);
