-- Add breakdown mode support to onsite prep

-- Add mode and current_phase to attempts
ALTER TABLE onsite_prep_attempts
    ADD COLUMN IF NOT EXISTS mode TEXT DEFAULT 'stand_and_deliver',
    ADD COLUMN IF NOT EXISTS current_phase INTEGER DEFAULT 0;

-- Phase submissions for breakdown mode
CREATE TABLE IF NOT EXISTS onsite_prep_phase_submissions (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    attempt_id UUID NOT NULL REFERENCES onsite_prep_attempts(id) ON DELETE CASCADE,
    phase_number INTEGER NOT NULL CHECK (phase_number BETWEEN 1 AND 7),
    transcript TEXT,
    dimensions JSONB,
    overall_score REAL,
    verdict TEXT,
    feedback TEXT,
    strongest_moment TEXT,
    weakest_moment TEXT,
    audio_gcs_path TEXT,
    duration_seconds INTEGER,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE (attempt_id, phase_number)
);

-- Images for both modes
CREATE TABLE IF NOT EXISTS onsite_prep_images (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    attempt_id UUID REFERENCES onsite_prep_attempts(id) ON DELETE CASCADE,
    phase_submission_id UUID REFERENCES onsite_prep_phase_submissions(id) ON DELETE CASCADE,
    gcs_path TEXT NOT NULL,
    filename TEXT NOT NULL,
    include_in_grading BOOLEAN DEFAULT FALSE,
    sort_order INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    CHECK (attempt_id IS NOT NULL OR phase_submission_id IS NOT NULL)
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_onsite_prep_phase_submissions_attempt
    ON onsite_prep_phase_submissions(attempt_id);
CREATE INDEX IF NOT EXISTS idx_onsite_prep_phase_submissions_phase
    ON onsite_prep_phase_submissions(attempt_id, phase_number);
CREATE INDEX IF NOT EXISTS idx_onsite_prep_images_attempt
    ON onsite_prep_images(attempt_id);
CREATE INDEX IF NOT EXISTS idx_onsite_prep_images_phase
    ON onsite_prep_images(phase_submission_id);

-- RLS
ALTER TABLE onsite_prep_phase_submissions ENABLE ROW LEVEL SECURITY;
ALTER TABLE onsite_prep_images ENABLE ROW LEVEL SECURITY;

-- Phase submissions: user owns via attempt FK chain
CREATE POLICY "Users can read own phase submissions"
    ON onsite_prep_phase_submissions FOR SELECT TO authenticated
    USING (EXISTS (SELECT 1 FROM onsite_prep_attempts a WHERE a.id = attempt_id AND a.user_id = auth.uid()));
CREATE POLICY "Anon can read all phase submissions"
    ON onsite_prep_phase_submissions FOR SELECT TO anon USING (true);
CREATE POLICY "Anon can insert phase submissions"
    ON onsite_prep_phase_submissions FOR INSERT TO anon WITH CHECK (true);
CREATE POLICY "Anon can update phase submissions"
    ON onsite_prep_phase_submissions FOR UPDATE TO anon USING (true);
CREATE POLICY "Anon can delete phase submissions"
    ON onsite_prep_phase_submissions FOR DELETE TO anon USING (true);

-- Images: user owns via attempt FK chain
CREATE POLICY "Users can read own images"
    ON onsite_prep_images FOR SELECT TO authenticated
    USING (
        (attempt_id IS NOT NULL AND EXISTS (SELECT 1 FROM onsite_prep_attempts a WHERE a.id = attempt_id AND a.user_id = auth.uid()))
        OR
        (phase_submission_id IS NOT NULL AND EXISTS (
            SELECT 1 FROM onsite_prep_phase_submissions ps
            JOIN onsite_prep_attempts a ON a.id = ps.attempt_id
            WHERE ps.id = phase_submission_id AND a.user_id = auth.uid()
        ))
    );
CREATE POLICY "Anon can read all images"
    ON onsite_prep_images FOR SELECT TO anon USING (true);
CREATE POLICY "Anon can insert images"
    ON onsite_prep_images FOR INSERT TO anon WITH CHECK (true);
CREATE POLICY "Anon can update images"
    ON onsite_prep_images FOR UPDATE TO anon USING (true);
CREATE POLICY "Anon can delete images"
    ON onsite_prep_images FOR DELETE TO anon USING (true);
