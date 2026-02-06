-- Create table for caching pre-generated daily questions (sub-questions format)
CREATE TABLE IF NOT EXISTS system_design_daily_questions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  track_id UUID NOT NULL REFERENCES system_design_tracks(id) ON DELETE CASCADE,
  topic TEXT NOT NULL,
  scenario TEXT NOT NULL,  -- Shared scenario context
  question_text TEXT NOT NULL,  -- The focused sub-question
  focus_area TEXT,
  key_concepts JSONB DEFAULT '[]'::jsonb,  -- Exactly 2 concepts per sub-question
  part_number INTEGER DEFAULT 1,  -- Which part (1, 2, or 3)
  total_parts INTEGER DEFAULT 3,  -- Total parts in the full scenario
  question_set_id UUID,  -- Links sub-questions from same scenario
  generated_at TIMESTAMPTZ DEFAULT NOW(),
  serve_date DATE DEFAULT CURRENT_DATE,  -- Which day to serve this question
  completed BOOLEAN DEFAULT FALSE,
  completed_at TIMESTAMPTZ,
  UNIQUE(user_id, track_id, topic, part_number, serve_date)
);

-- Index for efficient lookups
CREATE INDEX idx_daily_questions_user_topic ON system_design_daily_questions(user_id, track_id, topic);
CREATE INDEX idx_daily_questions_valid ON system_design_daily_questions(valid_until);

-- Enable RLS
ALTER TABLE system_design_daily_questions ENABLE ROW LEVEL SECURITY;

-- Users can only see their own questions
CREATE POLICY "Users can view own daily questions" ON system_design_daily_questions
  FOR SELECT USING (auth.uid() = user_id);

CREATE POLICY "Users can insert own daily questions" ON system_design_daily_questions
  FOR INSERT WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update own daily questions" ON system_design_daily_questions
  FOR UPDATE USING (auth.uid() = user_id);

CREATE POLICY "Users can delete own daily questions" ON system_design_daily_questions
  FOR DELETE USING (auth.uid() = user_id);
