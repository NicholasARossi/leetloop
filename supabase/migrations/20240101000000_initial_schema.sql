-- LeetLoop Initial Schema
-- Creates tables for submission tracking, skill scores, and review queue

-- Core submission log
CREATE TABLE IF NOT EXISTS submissions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL,
  problem_slug TEXT NOT NULL,
  problem_title TEXT NOT NULL,
  problem_id INTEGER,
  difficulty TEXT CHECK (difficulty IN ('Easy', 'Medium', 'Hard')),
  tags TEXT[],
  status TEXT NOT NULL CHECK (status IN (
    'Accepted',
    'Wrong Answer',
    'Time Limit Exceeded',
    'Memory Limit Exceeded',
    'Runtime Error',
    'Compile Error'
  )),
  runtime_ms INTEGER,
  runtime_percentile REAL,
  memory_mb REAL,
  memory_percentile REAL,
  attempt_number INTEGER,
  time_elapsed_seconds INTEGER,
  language TEXT,
  code TEXT,
  code_length INTEGER,
  session_id UUID,
  submitted_at TIMESTAMPTZ DEFAULT NOW(),
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes for common queries
CREATE INDEX IF NOT EXISTS idx_submissions_user_id ON submissions(user_id);
CREATE INDEX IF NOT EXISTS idx_submissions_problem_slug ON submissions(problem_slug);
CREATE INDEX IF NOT EXISTS idx_submissions_submitted_at ON submissions(submitted_at DESC);
CREATE INDEX IF NOT EXISTS idx_submissions_status ON submissions(status);
CREATE INDEX IF NOT EXISTS idx_submissions_session_id ON submissions(session_id);

-- Aggregated skill tracking (computed from submissions)
CREATE TABLE IF NOT EXISTS skill_scores (
  user_id UUID NOT NULL,
  tag TEXT NOT NULL,
  score REAL DEFAULT 50.0,
  total_attempts INTEGER DEFAULT 0,
  success_rate REAL DEFAULT 0.0,
  avg_time_seconds REAL,
  last_practiced TIMESTAMPTZ,
  updated_at TIMESTAMPTZ DEFAULT NOW(),
  PRIMARY KEY (user_id, tag)
);

CREATE INDEX IF NOT EXISTS idx_skill_scores_user_id ON skill_scores(user_id);
CREATE INDEX IF NOT EXISTS idx_skill_scores_score ON skill_scores(score);

-- Spaced repetition review queue
CREATE TABLE IF NOT EXISTS review_queue (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL,
  problem_slug TEXT NOT NULL,
  problem_title TEXT,
  reason TEXT,
  priority INTEGER DEFAULT 0,
  next_review TIMESTAMPTZ DEFAULT NOW(),
  interval_days INTEGER DEFAULT 1,
  review_count INTEGER DEFAULT 0,
  last_reviewed TIMESTAMPTZ,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_review_queue_user_id ON review_queue(user_id);
CREATE INDEX IF NOT EXISTS idx_review_queue_next_review ON review_queue(next_review);
CREATE INDEX IF NOT EXISTS idx_review_queue_priority ON review_queue(priority DESC);

-- User settings and preferences
CREATE TABLE IF NOT EXISTS user_settings (
  user_id UUID PRIMARY KEY,
  telegram_chat_id TEXT,
  daily_goal INTEGER DEFAULT 5,
  notification_enabled BOOLEAN DEFAULT TRUE,
  timezone TEXT DEFAULT 'UTC',
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Comments/notes on submissions for learning
CREATE TABLE IF NOT EXISTS submission_notes (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  submission_id UUID REFERENCES submissions(id) ON DELETE CASCADE,
  user_id UUID NOT NULL,
  note TEXT NOT NULL,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_submission_notes_submission_id ON submission_notes(submission_id);
