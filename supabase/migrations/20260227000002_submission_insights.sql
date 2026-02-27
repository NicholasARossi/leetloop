-- Stores per-submission insights from code analysis (pattern_type, concept_gap, root_cause)
-- Used to feed intelligence back into recommendations and tips

CREATE TABLE IF NOT EXISTS submission_insights (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    submission_id UUID REFERENCES submissions(id),
    user_id UUID NOT NULL,
    pattern_type TEXT,
    concept_gap TEXT,
    root_cause TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_submission_insights_user ON submission_insights(user_id);
CREATE INDEX IF NOT EXISTS idx_submission_insights_pattern ON submission_insights(user_id, pattern_type);

-- RLS policies
ALTER TABLE submission_insights ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can read own insights" ON submission_insights
    FOR SELECT USING (auth.uid() = user_id);

CREATE POLICY "Users can insert own insights" ON submission_insights
    FOR INSERT WITH CHECK (auth.uid() = user_id);

-- Anon policy for API service key
CREATE POLICY "Service can manage all insights" ON submission_insights
    FOR ALL USING (auth.role() = 'anon');
