-- Onsite Prep V2: ideal response, conversational follow-ups, missing delete policy

-- Add ideal_response column to attempts
ALTER TABLE onsite_prep_attempts ADD COLUMN IF NOT EXISTS ideal_response JSONB;

-- Add parent_follow_up_id for conversational chaining
ALTER TABLE onsite_prep_follow_ups ADD COLUMN IF NOT EXISTS parent_follow_up_id UUID REFERENCES onsite_prep_follow_ups(id) ON DELETE SET NULL;

-- Add ideal_answer column to follow-ups for per-probe ideal responses
ALTER TABLE onsite_prep_follow_ups ADD COLUMN IF NOT EXISTS ideal_answer TEXT;

-- Missing delete policy for follow-ups (needed for idempotent regeneration)
CREATE POLICY "Anon can delete follow-ups"
    ON onsite_prep_follow_ups FOR DELETE TO anon USING (true);
