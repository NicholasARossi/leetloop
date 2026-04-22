-- Language Oral Practice
-- Tables for oral recording sessions, async grading, and pre-generated prompt bank

-- ============ Oral Prompts (pre-generated bank) ============

CREATE TABLE IF NOT EXISTS language_oral_prompts (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  track_id UUID REFERENCES language_tracks(id) NOT NULL,
  chapter_ref TEXT NOT NULL,          -- topic name from track's topics array
  chapter_order INT NOT NULL,
  prompt_text TEXT NOT NULL,          -- the monologue prompt (in target language)
  theme TEXT,                         -- short theme label
  grammar_targets TEXT[] DEFAULT '{}',
  vocab_targets TEXT[] DEFAULT '{}',
  suggested_duration_seconds INT DEFAULT 120,
  sort_order INT DEFAULT 0,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_oral_prompts_track_chapter
  ON language_oral_prompts(track_id, chapter_order);

-- ============ Oral Sessions ============

CREATE TABLE IF NOT EXISTS language_oral_sessions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL,
  prompt_id UUID REFERENCES language_oral_prompts(id) NOT NULL,
  track_id UUID REFERENCES language_tracks(id) NOT NULL,
  chapter_ref TEXT NOT NULL,
  audio_gcs_path TEXT,
  audio_duration_seconds INT,
  status TEXT NOT NULL DEFAULT 'prompted'
    CHECK (status IN ('prompted', 'recorded', 'grading', 'graded', 'failed')),
  created_at TIMESTAMPTZ DEFAULT NOW(),
  graded_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_oral_sessions_user_status
  ON language_oral_sessions(user_id, status);

CREATE INDEX IF NOT EXISTS idx_oral_sessions_prompt
  ON language_oral_sessions(prompt_id);

-- ============ Oral Gradings ============

CREATE TABLE IF NOT EXISTS language_oral_gradings (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  session_id UUID REFERENCES language_oral_sessions(id) NOT NULL UNIQUE,
  transcript TEXT,
  transcription_flags JSONB,       -- low-confidence words (non-graded, future use)
  scores JSONB NOT NULL,           -- {grammar: {score, evidence[], summary}, lexical: {...}, ...}
  overall_score NUMERIC(4,2),
  verdict TEXT CHECK (verdict IN ('strong', 'developing', 'needs_work')),
  feedback TEXT,                   -- in target language
  strongest_moment TEXT,
  weakest_moment TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_oral_gradings_session
  ON language_oral_gradings(session_id);

-- ============ Streak & Chapter Tracking ============

ALTER TABLE user_language_settings
  ADD COLUMN IF NOT EXISTS current_streak INT DEFAULT 0,
  ADD COLUMN IF NOT EXISTS longest_streak INT DEFAULT 0,
  ADD COLUMN IF NOT EXISTS last_practice_date DATE,
  ADD COLUMN IF NOT EXISTS current_chapter_order INT DEFAULT 1;

-- ============ RLS ============

ALTER TABLE language_oral_prompts ENABLE ROW LEVEL SECURITY;
ALTER TABLE language_oral_sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE language_oral_gradings ENABLE ROW LEVEL SECURITY;

-- Prompts: public read
CREATE POLICY "Anyone can view oral prompts"
  ON language_oral_prompts FOR SELECT
  USING (true);

-- Sessions: user sees own, anon full access (API service key)
CREATE POLICY "Users can view own oral sessions"
  ON language_oral_sessions FOR SELECT
  USING (auth.uid() = user_id);

CREATE POLICY "Users can insert own oral sessions"
  ON language_oral_sessions FOR INSERT
  WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update own oral sessions"
  ON language_oral_sessions FOR UPDATE
  USING (auth.uid() = user_id);

-- Gradings: accessible via session ownership (join through sessions)
CREATE POLICY "Users can view own oral gradings"
  ON language_oral_gradings FOR SELECT
  USING (
    EXISTS (
      SELECT 1 FROM language_oral_sessions s
      WHERE s.id = language_oral_gradings.session_id
        AND s.user_id = auth.uid()
    )
  );

-- ============ Anon Policies (API service key) ============

CREATE POLICY "Anon can view all oral prompts"
  ON language_oral_prompts FOR SELECT TO anon
  USING (true);

CREATE POLICY "Anon can insert oral prompts"
  ON language_oral_prompts FOR INSERT TO anon
  WITH CHECK (true);

CREATE POLICY "Anon can update oral prompts"
  ON language_oral_prompts FOR UPDATE TO anon
  USING (true);

CREATE POLICY "Anon can view all oral sessions"
  ON language_oral_sessions FOR SELECT TO anon
  USING (true);

CREATE POLICY "Anon can insert all oral sessions"
  ON language_oral_sessions FOR INSERT TO anon
  WITH CHECK (true);

CREATE POLICY "Anon can update all oral sessions"
  ON language_oral_sessions FOR UPDATE TO anon
  USING (true);

CREATE POLICY "Anon can delete all oral sessions"
  ON language_oral_sessions FOR DELETE TO anon
  USING (true);

CREATE POLICY "Anon can view all oral gradings"
  ON language_oral_gradings FOR SELECT TO anon
  USING (true);

CREATE POLICY "Anon can insert all oral gradings"
  ON language_oral_gradings FOR INSERT TO anon
  WITH CHECK (true);

CREATE POLICY "Anon can update all oral gradings"
  ON language_oral_gradings FOR UPDATE TO anon
  USING (true);
