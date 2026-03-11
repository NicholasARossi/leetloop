-- Oral System Design: Voice-based practice with multimodal Gemini grading
-- Replaces text-based system design practice with audio recording/upload flow

-- ============ Oral Sessions Table ============

CREATE TABLE IF NOT EXISTS system_design_oral_sessions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL,
  track_id UUID REFERENCES system_design_tracks(id),
  topic TEXT NOT NULL,
  scenario TEXT,
  status TEXT DEFAULT 'active' CHECK (status IN ('active', 'completed', 'abandoned')),
  created_at TIMESTAMPTZ DEFAULT NOW(),
  completed_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_oral_sessions_user_id ON system_design_oral_sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_oral_sessions_created_at ON system_design_oral_sessions(created_at DESC);

ALTER TABLE system_design_oral_sessions ENABLE ROW LEVEL SECURITY;

-- Authenticated users can manage their own sessions
CREATE POLICY "Users can view own oral sessions"
  ON system_design_oral_sessions FOR SELECT
  USING (auth.uid() = user_id);

CREATE POLICY "Users can insert own oral sessions"
  ON system_design_oral_sessions FOR INSERT
  WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update own oral sessions"
  ON system_design_oral_sessions FOR UPDATE
  USING (auth.uid() = user_id);

CREATE POLICY "Users can delete own oral sessions"
  ON system_design_oral_sessions FOR DELETE
  USING (auth.uid() = user_id);

-- Anon (API service key) can manage all sessions
CREATE POLICY "Anon can view all oral sessions"
  ON system_design_oral_sessions FOR SELECT TO anon
  USING (true);

CREATE POLICY "Anon can insert all oral sessions"
  ON system_design_oral_sessions FOR INSERT TO anon
  WITH CHECK (true);

CREATE POLICY "Anon can update all oral sessions"
  ON system_design_oral_sessions FOR UPDATE TO anon
  USING (true);

CREATE POLICY "Anon can delete all oral sessions"
  ON system_design_oral_sessions FOR DELETE TO anon
  USING (true);

-- ============ Oral Questions Table ============

CREATE TABLE IF NOT EXISTS system_design_oral_questions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  session_id UUID NOT NULL REFERENCES system_design_oral_sessions(id) ON DELETE CASCADE,
  part_number INTEGER NOT NULL,
  question_text TEXT NOT NULL,
  focus_area TEXT NOT NULL,
  key_concepts TEXT[],
  suggested_duration_minutes INTEGER DEFAULT 4,

  -- Audio response data (populated after grading)
  audio_duration_seconds INTEGER,
  transcript TEXT,
  dimension_scores JSONB,
  overall_score NUMERIC,
  verdict TEXT CHECK (verdict IS NULL OR verdict IN ('pass', 'fail', 'borderline')),
  feedback TEXT,
  missed_concepts TEXT[],
  strongest_moment TEXT,
  weakest_moment TEXT,
  follow_up_questions TEXT[],

  -- Status
  status TEXT DEFAULT 'pending' CHECK (status IN ('pending', 'graded')),
  created_at TIMESTAMPTZ DEFAULT NOW(),
  graded_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_oral_questions_session_id ON system_design_oral_questions(session_id);

ALTER TABLE system_design_oral_questions ENABLE ROW LEVEL SECURITY;

-- Authenticated users can manage their own questions (via session join)
CREATE POLICY "Users can view own oral questions"
  ON system_design_oral_questions FOR SELECT
  USING (EXISTS (
    SELECT 1 FROM system_design_oral_sessions s
    WHERE s.id = session_id AND s.user_id = auth.uid()
  ));

CREATE POLICY "Users can insert own oral questions"
  ON system_design_oral_questions FOR INSERT
  WITH CHECK (EXISTS (
    SELECT 1 FROM system_design_oral_sessions s
    WHERE s.id = session_id AND s.user_id = auth.uid()
  ));

CREATE POLICY "Users can update own oral questions"
  ON system_design_oral_questions FOR UPDATE
  USING (EXISTS (
    SELECT 1 FROM system_design_oral_sessions s
    WHERE s.id = session_id AND s.user_id = auth.uid()
  ));

CREATE POLICY "Users can delete own oral questions"
  ON system_design_oral_questions FOR DELETE
  USING (EXISTS (
    SELECT 1 FROM system_design_oral_sessions s
    WHERE s.id = session_id AND s.user_id = auth.uid()
  ));

-- Anon (API service key) can manage all questions
CREATE POLICY "Anon can view all oral questions"
  ON system_design_oral_questions FOR SELECT TO anon
  USING (true);

CREATE POLICY "Anon can insert all oral questions"
  ON system_design_oral_questions FOR INSERT TO anon
  WITH CHECK (true);

CREATE POLICY "Anon can update all oral questions"
  ON system_design_oral_questions FOR UPDATE TO anon
  USING (true);

CREATE POLICY "Anon can delete all oral questions"
  ON system_design_oral_questions FOR DELETE TO anon
  USING (true);
