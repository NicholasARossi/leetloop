-- Add unique constraint for upsert support on onsite_prep_questions
-- This allows seed scripts to use INSERT ... ON CONFLICT UPDATE instead of DELETE + INSERT
CREATE UNIQUE INDEX IF NOT EXISTS idx_onsite_prep_questions_natural_key
    ON onsite_prep_questions(category, prompt_text);

-- Add UPDATE policy for anon (service key) so upserts work
CREATE POLICY "Questions are updatable by anon"
    ON onsite_prep_questions FOR UPDATE TO anon USING (true);
