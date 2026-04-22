-- Add vocab_targets JSONB column to language_daily_exercises
-- Stores vocabulary target words/expressions for open-ended grammar-targeted prompts

ALTER TABLE language_daily_exercises
  ADD COLUMN IF NOT EXISTS vocab_targets JSONB DEFAULT '[]'::jsonb;

-- Also add to language_attempts for history tracking
ALTER TABLE language_attempts
  ADD COLUMN IF NOT EXISTS vocab_targets JSONB DEFAULT '[]'::jsonb;
