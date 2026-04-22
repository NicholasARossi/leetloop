-- Add written_grading JSONB column to language_daily_exercises
-- Stores the full 4-dimension rubric grading result (grammar, lexical, discourse, task)

ALTER TABLE language_daily_exercises
  ADD COLUMN IF NOT EXISTS written_grading JSONB DEFAULT NULL;
