-- Add active system design track tracking for users
-- This enables showing system design on the main dashboard

-- Add active_system_design_track_id to user preferences
-- We'll use a simple table to track this per user
CREATE TABLE IF NOT EXISTS user_system_design_settings (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL UNIQUE,
  active_track_id UUID REFERENCES system_design_tracks(id) ON DELETE SET NULL,
  show_on_dashboard BOOLEAN DEFAULT true,
  daily_topic_enabled BOOLEAN DEFAULT true,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_user_sd_settings_user_id ON user_system_design_settings(user_id);

-- Enable RLS
ALTER TABLE user_system_design_settings ENABLE ROW LEVEL SECURITY;

-- RLS Policies
CREATE POLICY "Users can view own system design settings"
  ON user_system_design_settings FOR SELECT
  USING (auth.uid() = user_id);

CREATE POLICY "Users can insert own system design settings"
  ON user_system_design_settings FOR INSERT
  WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update own system design settings"
  ON user_system_design_settings FOR UPDATE
  USING (auth.uid() = user_id);

-- Anonymous API access policies
CREATE POLICY "Anon can view system design settings"
  ON user_system_design_settings FOR SELECT TO anon
  USING (true);

CREATE POLICY "Anon can insert system design settings"
  ON user_system_design_settings FOR INSERT TO anon
  WITH CHECK (true);

CREATE POLICY "Anon can update system design settings"
  ON user_system_design_settings FOR UPDATE TO anon
  USING (true);

-- Function to get user's next system design topic
CREATE OR REPLACE FUNCTION get_next_system_design_topic(p_user_id UUID)
RETURNS TABLE (
  track_id UUID,
  track_name TEXT,
  track_type TEXT,
  topic_name TEXT,
  topic_order INTEGER,
  topic_difficulty TEXT,
  example_systems JSONB,
  topics_completed INTEGER,
  total_topics INTEGER
) AS $$
DECLARE
  v_active_track_id UUID;
  v_completed_topics TEXT[];
BEGIN
  -- Get user's active track
  SELECT active_track_id INTO v_active_track_id
  FROM user_system_design_settings
  WHERE user_id = p_user_id;

  IF v_active_track_id IS NULL THEN
    RETURN;
  END IF;

  -- Get completed topics for this track
  SELECT COALESCE(utp.completed_topics, '{}')
  INTO v_completed_topics
  FROM user_track_progress utp
  WHERE utp.user_id = p_user_id AND utp.track_id = v_active_track_id;

  -- Return next uncompleted topic
  RETURN QUERY
  SELECT
    t.id as track_id,
    t.name as track_name,
    t.track_type,
    (topic->>'name')::TEXT as topic_name,
    (topic->>'order')::INTEGER as topic_order,
    (topic->>'difficulty')::TEXT as topic_difficulty,
    (topic->'example_systems')::JSONB as example_systems,
    array_length(v_completed_topics, 1) as topics_completed,
    t.total_topics
  FROM system_design_tracks t,
       jsonb_array_elements(t.topics) as topic
  WHERE t.id = v_active_track_id
    AND NOT ((topic->>'name')::TEXT = ANY(v_completed_topics))
  ORDER BY (topic->>'order')::INTEGER
  LIMIT 1;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;
