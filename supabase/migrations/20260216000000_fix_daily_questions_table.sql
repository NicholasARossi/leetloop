-- Fix: Ensure system_design_daily_questions table exists
-- The original migration (20260205000000) may have failed due to a
-- 'valid_until' index bug. This migration is fully idempotent.

CREATE TABLE IF NOT EXISTS system_design_daily_questions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  track_id UUID NOT NULL REFERENCES system_design_tracks(id) ON DELETE CASCADE,
  topic TEXT NOT NULL,
  scenario TEXT NOT NULL,
  question_text TEXT NOT NULL,
  focus_area TEXT,
  key_concepts JSONB DEFAULT '[]'::jsonb,
  part_number INTEGER DEFAULT 1,
  total_parts INTEGER DEFAULT 3,
  question_set_id UUID,
  generated_at TIMESTAMPTZ DEFAULT NOW(),
  serve_date DATE DEFAULT CURRENT_DATE,
  completed BOOLEAN DEFAULT FALSE,
  completed_at TIMESTAMPTZ,
  UNIQUE(user_id, track_id, topic, part_number, serve_date)
);

CREATE INDEX IF NOT EXISTS idx_daily_questions_user_topic ON system_design_daily_questions(user_id, track_id, topic);
CREATE INDEX IF NOT EXISTS idx_daily_questions_serve_date ON system_design_daily_questions(user_id, serve_date);

ALTER TABLE system_design_daily_questions ENABLE ROW LEVEL SECURITY;

-- Idempotent policy creation
DO $$ BEGIN
  CREATE POLICY "Users can view own daily questions" ON system_design_daily_questions
    FOR SELECT USING (auth.uid() = user_id);
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

DO $$ BEGIN
  CREATE POLICY "Users can insert own daily questions" ON system_design_daily_questions
    FOR INSERT WITH CHECK (auth.uid() = user_id);
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

DO $$ BEGIN
  CREATE POLICY "Users can update own daily questions" ON system_design_daily_questions
    FOR UPDATE USING (auth.uid() = user_id);
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

DO $$ BEGIN
  CREATE POLICY "Users can delete own daily questions" ON system_design_daily_questions
    FOR DELETE USING (auth.uid() = user_id);
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

DO $$ BEGIN
  CREATE POLICY "Anon can manage daily questions" ON system_design_daily_questions
    FOR ALL TO anon USING (true) WITH CHECK (true);
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;
