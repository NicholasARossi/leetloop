-- Mistake Journal table for logging specific mistakes and insights
CREATE TABLE IF NOT EXISTS mistake_journal (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES auth.users(id),
  problem_slug TEXT,
  problem_title TEXT,
  entry_text TEXT NOT NULL,
  tags TEXT[] DEFAULT '{}',
  entry_type TEXT NOT NULL DEFAULT 'general' CHECK (entry_type IN ('problem', 'general')),
  is_addressed BOOLEAN NOT NULL DEFAULT FALSE,
  feed_item_id UUID REFERENCES daily_problem_feed(id) ON DELETE SET NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Indexes
CREATE INDEX idx_mistake_journal_user_id ON mistake_journal(user_id);
CREATE INDEX idx_mistake_journal_unaddressed ON mistake_journal(user_id, is_addressed) WHERE NOT is_addressed;

-- RLS
ALTER TABLE mistake_journal ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can manage their own journal entries"
  ON mistake_journal FOR ALL
  USING (auth.uid() = user_id)
  WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Anon can manage journal entries"
  ON mistake_journal FOR ALL
  USING (auth.role() = 'anon')
  WITH CHECK (auth.role() = 'anon');

-- Update practice_source CHECK constraint to include 'journal'
ALTER TABLE daily_problem_feed DROP CONSTRAINT IF EXISTS daily_problem_feed_practice_source_check;
ALTER TABLE daily_problem_feed ADD CONSTRAINT daily_problem_feed_practice_source_check
  CHECK (practice_source IN ('review', 'review_queue', 'weak_skill', 'path', 'progression', 'insight', 'journal'));
