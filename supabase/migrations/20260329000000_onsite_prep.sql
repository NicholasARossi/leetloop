-- Onsite Prep tables for Amazon interview preparation
-- Categories: lp (leadership principles), breadth (ML breadth), depth (ML depth), design (system design)

-- Questions bank
CREATE TABLE IF NOT EXISTS onsite_prep_questions (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    category TEXT NOT NULL CHECK (category IN ('lp', 'breadth', 'depth', 'design')),
    subcategory TEXT,
    prompt_text TEXT NOT NULL,
    context_hint TEXT,
    rubric_dimensions JSONB NOT NULL DEFAULT '[]'::jsonb,
    target_duration_seconds INTEGER NOT NULL DEFAULT 120,
    sort_order INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Attempts (graded recordings)
CREATE TABLE IF NOT EXISTS onsite_prep_attempts (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    user_id UUID NOT NULL,
    question_id UUID NOT NULL REFERENCES onsite_prep_questions(id) ON DELETE CASCADE,
    transcript TEXT,
    dimensions JSONB,
    overall_score REAL,
    verdict TEXT,
    feedback TEXT,
    strongest_moment TEXT,
    weakest_moment TEXT,
    duration_seconds INTEGER,
    follow_up_questions JSONB DEFAULT '[]'::jsonb,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Follow-up probes (dynamically generated from transcript gaps)
CREATE TABLE IF NOT EXISTS onsite_prep_follow_ups (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    attempt_id UUID NOT NULL REFERENCES onsite_prep_attempts(id) ON DELETE CASCADE,
    question_text TEXT NOT NULL,
    transcript TEXT,
    score REAL,
    feedback TEXT,
    addressed_gap BOOLEAN DEFAULT FALSE,
    sort_order INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_onsite_prep_questions_category ON onsite_prep_questions(category);
CREATE INDEX IF NOT EXISTS idx_onsite_prep_attempts_user ON onsite_prep_attempts(user_id);
CREATE INDEX IF NOT EXISTS idx_onsite_prep_attempts_question ON onsite_prep_attempts(question_id);
CREATE INDEX IF NOT EXISTS idx_onsite_prep_follow_ups_attempt ON onsite_prep_follow_ups(attempt_id);

-- RLS policies
ALTER TABLE onsite_prep_questions ENABLE ROW LEVEL SECURITY;
ALTER TABLE onsite_prep_attempts ENABLE ROW LEVEL SECURITY;
ALTER TABLE onsite_prep_follow_ups ENABLE ROW LEVEL SECURITY;

-- Questions: readable by all
CREATE POLICY "Questions are readable by authenticated users"
    ON onsite_prep_questions FOR SELECT TO authenticated USING (true);
CREATE POLICY "Questions are readable by anon"
    ON onsite_prep_questions FOR SELECT TO anon USING (true);
CREATE POLICY "Questions are insertable by anon"
    ON onsite_prep_questions FOR INSERT TO anon WITH CHECK (true);
CREATE POLICY "Questions are deletable by anon"
    ON onsite_prep_questions FOR DELETE TO anon USING (true);

-- Attempts: user owns their own, anon (service key) has full access
CREATE POLICY "Users can read own attempts"
    ON onsite_prep_attempts FOR SELECT TO authenticated USING (auth.uid() = user_id);
CREATE POLICY "Users can insert own attempts"
    ON onsite_prep_attempts FOR INSERT TO authenticated WITH CHECK (auth.uid() = user_id);
CREATE POLICY "Anon can read all attempts"
    ON onsite_prep_attempts FOR SELECT TO anon USING (true);
CREATE POLICY "Anon can insert attempts"
    ON onsite_prep_attempts FOR INSERT TO anon WITH CHECK (true);
CREATE POLICY "Anon can update attempts"
    ON onsite_prep_attempts FOR UPDATE TO anon USING (true);

-- Follow-ups: user owns via attempt, anon has full access
CREATE POLICY "Users can read own follow-ups"
    ON onsite_prep_follow_ups FOR SELECT TO authenticated
    USING (EXISTS (SELECT 1 FROM onsite_prep_attempts a WHERE a.id = attempt_id AND a.user_id = auth.uid()));
CREATE POLICY "Anon can read all follow-ups"
    ON onsite_prep_follow_ups FOR SELECT TO anon USING (true);
CREATE POLICY "Anon can insert follow-ups"
    ON onsite_prep_follow_ups FOR INSERT TO anon WITH CHECK (true);
CREATE POLICY "Anon can update follow-ups"
    ON onsite_prep_follow_ups FOR UPDATE TO anon USING (true);
