-- Cache table for user pattern analysis (refreshed periodically)

CREATE TABLE IF NOT EXISTS user_pattern_analysis (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL,
    patterns JSONB NOT NULL DEFAULT '{}',
    analyzed_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(user_id)
);

-- RLS policies
ALTER TABLE user_pattern_analysis ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can read own patterns" ON user_pattern_analysis
    FOR SELECT USING (auth.uid() = user_id);

CREATE POLICY "Users can insert own patterns" ON user_pattern_analysis
    FOR INSERT WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update own patterns" ON user_pattern_analysis
    FOR UPDATE USING (auth.uid() = user_id);

-- Anon policy for API service key
CREATE POLICY "Service can manage all patterns" ON user_pattern_analysis
    FOR ALL USING (auth.role() = 'anon');
