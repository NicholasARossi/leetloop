-- Book Content Ingestion
-- Tables for storing extracted book content for system design review

-- ============ Book Content Table ============

CREATE TABLE IF NOT EXISTS book_content (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  book_title TEXT NOT NULL,
  chapter_number INTEGER NOT NULL,
  chapter_title TEXT NOT NULL,
  sections JSONB NOT NULL DEFAULT '[]',  -- [{title, summary, page_start, page_end, key_points}]
  key_concepts TEXT[] DEFAULT '{}',
  case_studies JSONB NOT NULL DEFAULT '[]',  -- [{name, description, systems}]
  summary TEXT,
  page_start INTEGER,
  page_end INTEGER,
  track_id UUID REFERENCES system_design_tracks(id),
  created_at TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE(book_title, chapter_number)
);

CREATE INDEX IF NOT EXISTS idx_book_content_book_title ON book_content(book_title);
CREATE INDEX IF NOT EXISTS idx_book_content_track_id ON book_content(track_id);

-- ============ Enable RLS ============

ALTER TABLE book_content ENABLE ROW LEVEL SECURITY;

-- Book content is read-only for users, write only by system
CREATE POLICY "Anyone can view book content"
  ON book_content FOR SELECT
  USING (true);

-- ============ Anon Access ============

-- Allow anonymous users to read book content (matches pattern from other anon policies)
CREATE POLICY "anon_book_content_select"
  ON book_content FOR SELECT TO anon
  USING (true);
