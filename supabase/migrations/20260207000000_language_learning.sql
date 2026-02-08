-- Language Learning Feature
-- Tables for track-based language learning with AI grading and spaced repetition
-- Mirrors system_design_ table family with language-specific columns

-- ============ Track Definitions ============

CREATE TABLE IF NOT EXISTS language_tracks (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name TEXT NOT NULL UNIQUE,
  description TEXT,
  language TEXT NOT NULL CHECK (language IN ('french', 'chinese', 'spanish', 'german', 'japanese', 'italian', 'portuguese', 'korean')),
  level TEXT NOT NULL CHECK (level IN ('a1', 'a2', 'b1', 'b2', 'c1', 'c2')),
  topics JSONB NOT NULL DEFAULT '[]',  -- [{name, order, difficulty, key_concepts}]
  total_topics INTEGER DEFAULT 0,
  rubric JSONB NOT NULL DEFAULT '{"accuracy": 3, "grammar": 3, "vocabulary": 2, "naturalness": 2}',
  source_book TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============ Exercise Attempts ============

CREATE TABLE IF NOT EXISTS language_attempts (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL,
  track_id UUID REFERENCES language_tracks(id),
  topic TEXT NOT NULL,

  -- Exercise
  exercise_type TEXT NOT NULL CHECK (exercise_type IN ('vocabulary', 'grammar', 'fill_blank', 'conjugation', 'sentence_construction', 'reading_comprehension', 'dictation')),
  question_text TEXT NOT NULL,
  expected_answer TEXT,
  question_focus_area TEXT,
  question_key_concepts TEXT[],

  -- Response
  response_text TEXT,
  word_count INTEGER DEFAULT 0,

  -- Grading
  score REAL CHECK (score IS NULL OR (score >= 1 AND score <= 10)),
  verdict TEXT CHECK (verdict IS NULL OR verdict IN ('pass', 'fail', 'borderline')),
  feedback TEXT,
  corrections TEXT,
  missed_concepts TEXT[],

  -- Status
  status TEXT DEFAULT 'pending' CHECK (status IN ('pending', 'graded', 'abandoned')),
  created_at TIMESTAMPTZ DEFAULT NOW(),
  graded_at TIMESTAMPTZ
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_language_attempts_user_id ON language_attempts(user_id);
CREATE INDEX IF NOT EXISTS idx_language_attempts_track_id ON language_attempts(track_id);
CREATE INDEX IF NOT EXISTS idx_language_attempts_status ON language_attempts(status);
CREATE INDEX IF NOT EXISTS idx_language_attempts_created_at ON language_attempts(created_at DESC);

-- ============ Spaced Repetition Queue ============

CREATE TABLE IF NOT EXISTS language_review_queue (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL,
  track_id UUID REFERENCES language_tracks(id),
  topic TEXT NOT NULL,
  reason TEXT,
  priority INTEGER DEFAULT 0,
  next_review TIMESTAMPTZ DEFAULT NOW(),
  interval_days INTEGER DEFAULT 1,
  review_count INTEGER DEFAULT 0,
  last_reviewed TIMESTAMPTZ,
  source_attempt_id UUID REFERENCES language_attempts(id),
  created_at TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE(user_id, topic)
);

CREATE INDEX IF NOT EXISTS idx_language_review_queue_user_id ON language_review_queue(user_id);
CREATE INDEX IF NOT EXISTS idx_language_review_queue_next_review ON language_review_queue(next_review);

-- ============ Track Progress ============

CREATE TABLE IF NOT EXISTS language_track_progress (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL,
  track_id UUID NOT NULL REFERENCES language_tracks(id),
  completed_topics TEXT[] DEFAULT '{}',
  sessions_completed INTEGER DEFAULT 0,
  average_score REAL DEFAULT 0.0,
  started_at TIMESTAMPTZ DEFAULT NOW(),
  last_activity_at TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE(user_id, track_id)
);

CREATE INDEX IF NOT EXISTS idx_language_track_progress_user_id ON language_track_progress(user_id);
CREATE INDEX IF NOT EXISTS idx_language_track_progress_track_id ON language_track_progress(track_id);

-- ============ User Language Settings ============

CREATE TABLE IF NOT EXISTS user_language_settings (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL UNIQUE,
  active_track_id UUID REFERENCES language_tracks(id),
  show_on_dashboard BOOLEAN DEFAULT true,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============ Add language_track_id to book_content ============

ALTER TABLE book_content ADD COLUMN IF NOT EXISTS language_track_id UUID REFERENCES language_tracks(id);
CREATE INDEX IF NOT EXISTS idx_book_content_language_track_id ON book_content(language_track_id);

-- ============ Enable RLS ============

ALTER TABLE language_tracks ENABLE ROW LEVEL SECURITY;
ALTER TABLE language_attempts ENABLE ROW LEVEL SECURITY;
ALTER TABLE language_review_queue ENABLE ROW LEVEL SECURITY;
ALTER TABLE language_track_progress ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_language_settings ENABLE ROW LEVEL SECURITY;

-- ============ RLS Policies ============

-- Tracks: public read
CREATE POLICY "Anyone can view language tracks"
  ON language_tracks FOR SELECT
  USING (true);

-- Attempts: users manage their own
CREATE POLICY "Users can view own language attempts"
  ON language_attempts FOR SELECT
  USING (auth.uid() = user_id);

CREATE POLICY "Users can insert own language attempts"
  ON language_attempts FOR INSERT
  WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update own language attempts"
  ON language_attempts FOR UPDATE
  USING (auth.uid() = user_id);

CREATE POLICY "Users can delete own language attempts"
  ON language_attempts FOR DELETE
  USING (auth.uid() = user_id);

-- Review queue: users manage their own
CREATE POLICY "Users can view own language reviews"
  ON language_review_queue FOR SELECT
  USING (auth.uid() = user_id);

CREATE POLICY "Users can insert own language reviews"
  ON language_review_queue FOR INSERT
  WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update own language reviews"
  ON language_review_queue FOR UPDATE
  USING (auth.uid() = user_id);

CREATE POLICY "Users can delete own language reviews"
  ON language_review_queue FOR DELETE
  USING (auth.uid() = user_id);

-- Track progress: users manage their own
CREATE POLICY "Users can view own language progress"
  ON language_track_progress FOR SELECT
  USING (auth.uid() = user_id);

CREATE POLICY "Users can insert own language progress"
  ON language_track_progress FOR INSERT
  WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update own language progress"
  ON language_track_progress FOR UPDATE
  USING (auth.uid() = user_id);

-- Settings: users manage their own
CREATE POLICY "Users can view own language settings"
  ON user_language_settings FOR SELECT
  USING (auth.uid() = user_id);

CREATE POLICY "Users can insert own language settings"
  ON user_language_settings FOR INSERT
  WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update own language settings"
  ON user_language_settings FOR UPDATE
  USING (auth.uid() = user_id);

-- ============ Anon Policies (API service key) ============

CREATE POLICY "Anon can view all language tracks"
  ON language_tracks FOR SELECT TO anon
  USING (true);

CREATE POLICY "Anon can insert language tracks"
  ON language_tracks FOR INSERT TO anon
  WITH CHECK (true);

CREATE POLICY "Anon can update language tracks"
  ON language_tracks FOR UPDATE TO anon
  USING (true);

CREATE POLICY "Anon can view all language attempts"
  ON language_attempts FOR SELECT TO anon
  USING (true);

CREATE POLICY "Anon can insert all language attempts"
  ON language_attempts FOR INSERT TO anon
  WITH CHECK (true);

CREATE POLICY "Anon can update all language attempts"
  ON language_attempts FOR UPDATE TO anon
  USING (true);

CREATE POLICY "Anon can delete all language attempts"
  ON language_attempts FOR DELETE TO anon
  USING (true);

CREATE POLICY "Anon can view all language reviews"
  ON language_review_queue FOR SELECT TO anon
  USING (true);

CREATE POLICY "Anon can insert all language reviews"
  ON language_review_queue FOR INSERT TO anon
  WITH CHECK (true);

CREATE POLICY "Anon can update all language reviews"
  ON language_review_queue FOR UPDATE TO anon
  USING (true);

CREATE POLICY "Anon can delete all language reviews"
  ON language_review_queue FOR DELETE TO anon
  USING (true);

CREATE POLICY "Anon can view all language progress"
  ON language_track_progress FOR SELECT TO anon
  USING (true);

CREATE POLICY "Anon can insert all language progress"
  ON language_track_progress FOR INSERT TO anon
  WITH CHECK (true);

CREATE POLICY "Anon can update all language progress"
  ON language_track_progress FOR UPDATE TO anon
  USING (true);

CREATE POLICY "Anon can view all language settings"
  ON user_language_settings FOR SELECT TO anon
  USING (true);

CREATE POLICY "Anon can insert all language settings"
  ON user_language_settings FOR INSERT TO anon
  WITH CHECK (true);

CREATE POLICY "Anon can update all language settings"
  ON user_language_settings FOR UPDATE TO anon
  USING (true);

-- ============ Spaced Repetition Function ============

CREATE OR REPLACE FUNCTION complete_language_review(p_review_id UUID, p_success BOOLEAN)
RETURNS void AS $$
DECLARE
  v_current_interval INTEGER;
BEGIN
  SELECT interval_days INTO v_current_interval
  FROM language_review_queue
  WHERE id = p_review_id;

  IF NOT FOUND THEN
    RAISE EXCEPTION 'Review item not found';
  END IF;

  IF p_success THEN
    -- Success: double interval (max 30 days)
    UPDATE language_review_queue
    SET
      interval_days = LEAST(v_current_interval * 2, 30),
      next_review = NOW() + (LEAST(v_current_interval * 2, 30) || ' days')::INTERVAL,
      review_count = review_count + 1,
      last_reviewed = NOW()
    WHERE id = p_review_id;
  ELSE
    -- Failure: reset to 1 day
    UPDATE language_review_queue
    SET
      interval_days = 1,
      next_review = NOW() + INTERVAL '1 day',
      review_count = review_count + 1,
      last_reviewed = NOW()
    WHERE id = p_review_id;
  END IF;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- ============ Get Due Reviews Function ============

CREATE OR REPLACE FUNCTION get_due_language_reviews(p_user_id UUID, p_limit INTEGER DEFAULT 10)
RETURNS SETOF language_review_queue AS $$
BEGIN
  RETURN QUERY
  SELECT *
  FROM language_review_queue
  WHERE user_id = p_user_id
    AND next_review <= NOW()
  ORDER BY priority DESC, next_review ASC
  LIMIT p_limit;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;
