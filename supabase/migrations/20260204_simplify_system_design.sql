-- Simplified System Design: Single-question attempt flow
-- Replaces multi-question sessions with simple inline attempts

-- ============ New Attempts Table ============

CREATE TABLE IF NOT EXISTS system_design_attempts (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL,
  track_id UUID REFERENCES system_design_tracks(id),
  topic TEXT NOT NULL,

  -- Question (single)
  question_text TEXT NOT NULL,
  question_focus_area TEXT,
  question_key_concepts TEXT[],

  -- Response
  response_text TEXT,
  word_count INTEGER DEFAULT 0,

  -- Simplified grading
  score REAL CHECK (score IS NULL OR (score >= 1 AND score <= 10)),
  verdict TEXT CHECK (verdict IS NULL OR verdict IN ('pass', 'fail', 'borderline')),
  feedback TEXT,
  missed_concepts TEXT[],
  review_topics TEXT[],

  -- Status
  status TEXT DEFAULT 'pending' CHECK (status IN ('pending', 'graded', 'abandoned')),
  created_at TIMESTAMPTZ DEFAULT NOW(),
  graded_at TIMESTAMPTZ
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_system_design_attempts_user_id ON system_design_attempts(user_id);
CREATE INDEX IF NOT EXISTS idx_system_design_attempts_track_id ON system_design_attempts(track_id);
CREATE INDEX IF NOT EXISTS idx_system_design_attempts_status ON system_design_attempts(status);
CREATE INDEX IF NOT EXISTS idx_system_design_attempts_created_at ON system_design_attempts(created_at DESC);

-- Enable RLS
ALTER TABLE system_design_attempts ENABLE ROW LEVEL SECURITY;

-- ============ RLS Policies for Attempts ============

-- Authenticated users can manage their own attempts
CREATE POLICY "Users can view own attempts"
  ON system_design_attempts FOR SELECT
  USING (auth.uid() = user_id);

CREATE POLICY "Users can insert own attempts"
  ON system_design_attempts FOR INSERT
  WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update own attempts"
  ON system_design_attempts FOR UPDATE
  USING (auth.uid() = user_id);

CREATE POLICY "Users can delete own attempts"
  ON system_design_attempts FOR DELETE
  USING (auth.uid() = user_id);

-- Anon (API service key) can manage all attempts
CREATE POLICY "Anon can view all attempts"
  ON system_design_attempts FOR SELECT TO anon
  USING (true);

CREATE POLICY "Anon can insert all attempts"
  ON system_design_attempts FOR INSERT TO anon
  WITH CHECK (true);

CREATE POLICY "Anon can update all attempts"
  ON system_design_attempts FOR UPDATE TO anon
  USING (true);

CREATE POLICY "Anon can delete all attempts"
  ON system_design_attempts FOR DELETE TO anon
  USING (true);

-- ============ Helper Function: Get User Attempt History ============

CREATE OR REPLACE FUNCTION get_user_attempt_history(
  p_user_id UUID,
  p_limit INTEGER DEFAULT 20,
  p_offset INTEGER DEFAULT 0
)
RETURNS TABLE (
  id UUID,
  topic TEXT,
  question_text TEXT,
  score REAL,
  verdict TEXT,
  status TEXT,
  created_at TIMESTAMPTZ,
  graded_at TIMESTAMPTZ,
  track_name TEXT
) AS $$
BEGIN
  RETURN QUERY
  SELECT
    a.id,
    a.topic,
    a.question_text,
    a.score,
    a.verdict,
    a.status,
    a.created_at,
    a.graded_at,
    t.name as track_name
  FROM system_design_attempts a
  LEFT JOIN system_design_tracks t ON a.track_id = t.id
  WHERE a.user_id = p_user_id
  ORDER BY a.created_at DESC
  LIMIT p_limit
  OFFSET p_offset;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;
