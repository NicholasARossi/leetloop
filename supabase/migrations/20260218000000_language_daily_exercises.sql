-- Language Daily Exercises
-- Pre-generated daily exercise batches for the language learning dashboard
-- Exercises are generated once per day and completed inline

-- ============ Daily Exercises Table ============

CREATE TABLE IF NOT EXISTS language_daily_exercises (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL,
  track_id UUID REFERENCES language_tracks(id),
  generated_date DATE NOT NULL DEFAULT CURRENT_DATE,
  sort_order INTEGER NOT NULL DEFAULT 0,

  -- Exercise content
  topic TEXT NOT NULL,
  exercise_type TEXT NOT NULL CHECK (exercise_type IN ('vocabulary', 'grammar', 'fill_blank', 'conjugation', 'sentence_construction', 'reading_comprehension')),
  question_text TEXT NOT NULL,
  expected_answer TEXT,
  focus_area TEXT,
  key_concepts TEXT[] DEFAULT '{}',

  -- User response & grading
  response_text TEXT,
  word_count INTEGER DEFAULT 0,
  score NUMERIC(4,2) CHECK (score IS NULL OR (score >= 0 AND score <= 10)),
  verdict TEXT CHECK (verdict IS NULL OR verdict IN ('pass', 'fail', 'borderline')),
  feedback TEXT,
  corrections TEXT,
  missed_concepts TEXT[] DEFAULT '{}',

  -- Status
  status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'completed', 'skipped')),
  is_review BOOLEAN DEFAULT FALSE,
  review_topic_reason TEXT,

  -- Timestamps
  created_at TIMESTAMPTZ DEFAULT NOW(),
  completed_at TIMESTAMPTZ,

  -- Unique constraint: one exercise per sort position per user per day
  UNIQUE(user_id, generated_date, sort_order)
);

-- ============ Indexes ============

CREATE INDEX IF NOT EXISTS idx_language_daily_exercises_user_date
  ON language_daily_exercises(user_id, generated_date);

CREATE INDEX IF NOT EXISTS idx_language_daily_exercises_user_status_date
  ON language_daily_exercises(user_id, status, generated_date);

-- ============ Enable RLS ============

ALTER TABLE language_daily_exercises ENABLE ROW LEVEL SECURITY;

-- ============ RLS Policies (Authenticated Users) ============

CREATE POLICY "Users can view own daily exercises"
  ON language_daily_exercises FOR SELECT
  USING (auth.uid() = user_id);

CREATE POLICY "Users can insert own daily exercises"
  ON language_daily_exercises FOR INSERT
  WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update own daily exercises"
  ON language_daily_exercises FOR UPDATE
  USING (auth.uid() = user_id);

CREATE POLICY "Users can delete own daily exercises"
  ON language_daily_exercises FOR DELETE
  USING (auth.uid() = user_id);

-- ============ Anon Policies (API service key) ============

CREATE POLICY "Anon can view all daily exercises"
  ON language_daily_exercises FOR SELECT TO anon
  USING (true);

CREATE POLICY "Anon can insert all daily exercises"
  ON language_daily_exercises FOR INSERT TO anon
  WITH CHECK (true);

CREATE POLICY "Anon can update all daily exercises"
  ON language_daily_exercises FOR UPDATE TO anon
  USING (true);

CREATE POLICY "Anon can delete all daily exercises"
  ON language_daily_exercises FOR DELETE TO anon
  USING (true);
