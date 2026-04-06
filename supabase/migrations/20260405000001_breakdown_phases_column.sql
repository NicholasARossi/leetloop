-- Add breakdown_phases JSONB column to onsite_prep_questions
ALTER TABLE onsite_prep_questions
    ADD COLUMN IF NOT EXISTS breakdown_phases JSONB DEFAULT '[]'::jsonb;
