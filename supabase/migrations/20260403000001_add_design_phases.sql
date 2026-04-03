-- Add phases and structured_probes columns to onsite_prep_questions
-- phases: array of {name, prompt, duration_seconds, key_areas[]} for design questions
-- structured_probes: hardcoded follow-up drill-down questions for design questions

ALTER TABLE onsite_prep_questions
  ADD COLUMN IF NOT EXISTS phases JSONB DEFAULT '[]'::jsonb,
  ADD COLUMN IF NOT EXISTS structured_probes JSONB DEFAULT '[]'::jsonb;
