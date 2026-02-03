-- System Design Review Feature
-- Tables for track-based system design interview prep with Gemini grading

-- ============ Track Definitions ============

CREATE TABLE IF NOT EXISTS system_design_tracks (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name TEXT NOT NULL UNIQUE,
  description TEXT,
  track_type TEXT NOT NULL CHECK (track_type IN ('mle', 'traditional', 'infra', 'data')),
  topics JSONB NOT NULL DEFAULT '[]',  -- [{name, order, difficulty, example_systems}]
  total_topics INTEGER DEFAULT 0,
  rubric JSONB NOT NULL DEFAULT '{"depth": 3, "tradeoffs": 3, "clarity": 2, "scalability": 2}',
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============ Individual Sessions ============

CREATE TABLE IF NOT EXISTS system_design_sessions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL,
  track_id UUID REFERENCES system_design_tracks(id),
  topic TEXT NOT NULL,
  questions JSONB NOT NULL DEFAULT '[]',  -- [{id, text, focus_area, key_concepts}]
  session_type TEXT CHECK (session_type IN ('track', 'gap_fill', 'review')),
  status TEXT DEFAULT 'in_progress' CHECK (status IN ('in_progress', 'completed', 'abandoned')),
  started_at TIMESTAMPTZ DEFAULT NOW(),
  completed_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_system_design_sessions_user_id ON system_design_sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_system_design_sessions_track_id ON system_design_sessions(track_id);
CREATE INDEX IF NOT EXISTS idx_system_design_sessions_status ON system_design_sessions(status);

-- ============ User Responses ============

CREATE TABLE IF NOT EXISTS system_design_responses (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  session_id UUID NOT NULL REFERENCES system_design_sessions(id) ON DELETE CASCADE,
  question_id INTEGER NOT NULL,
  response_text TEXT NOT NULL,
  word_count INTEGER,
  submitted_at TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE(session_id, question_id)
);

CREATE INDEX IF NOT EXISTS idx_system_design_responses_session_id ON system_design_responses(session_id);

-- ============ Grading Results ============

CREATE TABLE IF NOT EXISTS system_design_grades (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  session_id UUID NOT NULL UNIQUE REFERENCES system_design_sessions(id) ON DELETE CASCADE,
  overall_score REAL NOT NULL CHECK (overall_score >= 1 AND overall_score <= 10),
  overall_feedback TEXT NOT NULL,
  question_grades JSONB NOT NULL,  -- [{question_id, score, feedback, rubric_scores, missed_concepts}]
  strengths TEXT[] DEFAULT '{}',
  gaps TEXT[] DEFAULT '{}',
  review_topics TEXT[] DEFAULT '{}',
  would_hire BOOLEAN,
  graded_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_system_design_grades_session_id ON system_design_grades(session_id);

-- ============ Spaced Repetition Queue ============

CREATE TABLE IF NOT EXISTS system_design_review_queue (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL,
  track_id UUID REFERENCES system_design_tracks(id),
  topic TEXT NOT NULL,
  reason TEXT,
  priority INTEGER DEFAULT 0,
  next_review TIMESTAMPTZ DEFAULT NOW(),
  interval_days INTEGER DEFAULT 1,
  review_count INTEGER DEFAULT 0,
  last_reviewed TIMESTAMPTZ,
  source_session_id UUID REFERENCES system_design_sessions(id),
  created_at TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE(user_id, topic)
);

CREATE INDEX IF NOT EXISTS idx_system_design_review_queue_user_id ON system_design_review_queue(user_id);
CREATE INDEX IF NOT EXISTS idx_system_design_review_queue_next_review ON system_design_review_queue(next_review);

-- ============ User Track Progress ============

CREATE TABLE IF NOT EXISTS user_track_progress (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL,
  track_id UUID NOT NULL REFERENCES system_design_tracks(id),
  completed_topics TEXT[] DEFAULT '{}',
  sessions_completed INTEGER DEFAULT 0,
  average_score REAL DEFAULT 0.0,
  started_at TIMESTAMPTZ DEFAULT NOW(),
  last_activity_at TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE(user_id, track_id)
);

CREATE INDEX IF NOT EXISTS idx_user_track_progress_user_id ON user_track_progress(user_id);
CREATE INDEX IF NOT EXISTS idx_user_track_progress_track_id ON user_track_progress(track_id);

-- ============ Enable RLS ============

ALTER TABLE system_design_tracks ENABLE ROW LEVEL SECURITY;
ALTER TABLE system_design_sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE system_design_responses ENABLE ROW LEVEL SECURITY;
ALTER TABLE system_design_grades ENABLE ROW LEVEL SECURITY;
ALTER TABLE system_design_review_queue ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_track_progress ENABLE ROW LEVEL SECURITY;

-- ============ RLS Policies ============

-- Tracks: anyone can read, only system can write
CREATE POLICY "Anyone can view system design tracks"
  ON system_design_tracks FOR SELECT
  USING (true);

-- Sessions: users can manage their own
CREATE POLICY "Users can view own sessions"
  ON system_design_sessions FOR SELECT
  USING (auth.uid() = user_id);

CREATE POLICY "Users can insert own sessions"
  ON system_design_sessions FOR INSERT
  WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update own sessions"
  ON system_design_sessions FOR UPDATE
  USING (auth.uid() = user_id);

CREATE POLICY "Users can delete own sessions"
  ON system_design_sessions FOR DELETE
  USING (auth.uid() = user_id);

-- Responses: based on session ownership
CREATE POLICY "Users can view responses for own sessions"
  ON system_design_responses FOR SELECT
  USING (EXISTS (
    SELECT 1 FROM system_design_sessions s
    WHERE s.id = session_id AND s.user_id = auth.uid()
  ));

CREATE POLICY "Users can insert responses for own sessions"
  ON system_design_responses FOR INSERT
  WITH CHECK (EXISTS (
    SELECT 1 FROM system_design_sessions s
    WHERE s.id = session_id AND s.user_id = auth.uid()
  ));

CREATE POLICY "Users can update responses for own sessions"
  ON system_design_responses FOR UPDATE
  USING (EXISTS (
    SELECT 1 FROM system_design_sessions s
    WHERE s.id = session_id AND s.user_id = auth.uid()
  ));

-- Grades: based on session ownership
CREATE POLICY "Users can view grades for own sessions"
  ON system_design_grades FOR SELECT
  USING (EXISTS (
    SELECT 1 FROM system_design_sessions s
    WHERE s.id = session_id AND s.user_id = auth.uid()
  ));

-- Review queue: users can manage their own
CREATE POLICY "Users can view own review queue"
  ON system_design_review_queue FOR SELECT
  USING (auth.uid() = user_id);

CREATE POLICY "Users can insert own review items"
  ON system_design_review_queue FOR INSERT
  WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update own review items"
  ON system_design_review_queue FOR UPDATE
  USING (auth.uid() = user_id);

CREATE POLICY "Users can delete own review items"
  ON system_design_review_queue FOR DELETE
  USING (auth.uid() = user_id);

-- Track progress: users can manage their own
CREATE POLICY "Users can view own track progress"
  ON user_track_progress FOR SELECT
  USING (auth.uid() = user_id);

CREATE POLICY "Users can insert own track progress"
  ON user_track_progress FOR INSERT
  WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update own track progress"
  ON user_track_progress FOR UPDATE
  USING (auth.uid() = user_id);

-- ============ Spaced Repetition Function ============

CREATE OR REPLACE FUNCTION complete_system_design_review(p_review_id UUID, p_success BOOLEAN)
RETURNS void AS $$
DECLARE
  v_current_interval INTEGER;
BEGIN
  -- Get current interval
  SELECT interval_days INTO v_current_interval
  FROM system_design_review_queue
  WHERE id = p_review_id;

  IF NOT FOUND THEN
    RAISE EXCEPTION 'Review item not found';
  END IF;

  IF p_success THEN
    -- Success: double interval (max 30 days)
    UPDATE system_design_review_queue
    SET
      interval_days = LEAST(v_current_interval * 2, 30),
      next_review = NOW() + (LEAST(v_current_interval * 2, 30) || ' days')::INTERVAL,
      review_count = review_count + 1,
      last_reviewed = NOW()
    WHERE id = p_review_id;
  ELSE
    -- Failure: reset to 1 day
    UPDATE system_design_review_queue
    SET
      interval_days = 1,
      next_review = NOW() + INTERVAL '1 day',
      review_count = review_count + 1,
      last_reviewed = NOW()
    WHERE id = p_review_id;
  END IF;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- ============ Get Due Reviews Function ============

CREATE OR REPLACE FUNCTION get_due_system_design_reviews(p_user_id UUID, p_limit INTEGER DEFAULT 10)
RETURNS SETOF system_design_review_queue AS $$
BEGIN
  RETURN QUERY
  SELECT *
  FROM system_design_review_queue
  WHERE user_id = p_user_id
    AND next_review <= NOW()
  ORDER BY priority DESC, next_review ASC
  LIMIT p_limit;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- ============ Seed Data: MLE Track ============

INSERT INTO system_design_tracks (name, description, track_type, topics, total_topics, rubric)
VALUES (
  'Machine Learning Engineering',
  'System design for ML infrastructure, recommendation systems, real-time ML pipelines, and feature stores',
  'mle',
  '[
    {"name": "Recommendation System", "order": 1, "difficulty": "hard", "example_systems": ["Netflix recommendations", "YouTube video suggestions", "Amazon product recommendations"]},
    {"name": "Search Ranking", "order": 2, "difficulty": "hard", "example_systems": ["Google Search", "Bing", "E-commerce search"]},
    {"name": "Fraud Detection", "order": 3, "difficulty": "hard", "example_systems": ["Stripe fraud detection", "PayPal risk engine", "Bank transaction monitoring"]},
    {"name": "Real-time ML Pipeline", "order": 4, "difficulty": "hard", "example_systems": ["Uber surge pricing", "DoorDash delivery estimates", "Airbnb dynamic pricing"]},
    {"name": "Feature Store", "order": 5, "difficulty": "medium", "example_systems": ["Feast", "Tecton", "Hopsworks"]}
  ]'::JSONB,
  5,
  '{"depth": 3, "tradeoffs": 3, "clarity": 2, "scalability": 2}'::JSONB
)
ON CONFLICT (name) DO UPDATE SET
  description = EXCLUDED.description,
  topics = EXCLUDED.topics,
  total_topics = EXCLUDED.total_topics;

-- Traditional System Design Track
INSERT INTO system_design_tracks (name, description, track_type, topics, total_topics, rubric)
VALUES (
  'Traditional System Design',
  'Classic system design topics covering distributed systems, caching, messaging, and web-scale architecture',
  'traditional',
  '[
    {"name": "URL Shortener", "order": 1, "difficulty": "medium", "example_systems": ["bit.ly", "TinyURL", "t.co"]},
    {"name": "Rate Limiter", "order": 2, "difficulty": "medium", "example_systems": ["API gateways", "DDoS protection", "Fair usage enforcement"]},
    {"name": "Distributed Cache", "order": 3, "difficulty": "hard", "example_systems": ["Redis Cluster", "Memcached", "CDN edge caching"]},
    {"name": "Message Queue", "order": 4, "difficulty": "hard", "example_systems": ["Kafka", "RabbitMQ", "AWS SQS"]},
    {"name": "Notification System", "order": 5, "difficulty": "hard", "example_systems": ["Push notifications", "Email at scale", "In-app notifications"]},
    {"name": "Chat System", "order": 6, "difficulty": "hard", "example_systems": ["Slack", "Discord", "WhatsApp"]},
    {"name": "News Feed", "order": 7, "difficulty": "hard", "example_systems": ["Twitter timeline", "Facebook feed", "LinkedIn feed"]},
    {"name": "Video Streaming", "order": 8, "difficulty": "hard", "example_systems": ["YouTube", "Netflix", "Twitch"]}
  ]'::JSONB,
  8,
  '{"depth": 3, "tradeoffs": 3, "clarity": 2, "scalability": 2}'::JSONB
)
ON CONFLICT (name) DO UPDATE SET
  description = EXCLUDED.description,
  topics = EXCLUDED.topics,
  total_topics = EXCLUDED.total_topics;

-- Data Engineering Track
INSERT INTO system_design_tracks (name, description, track_type, topics, total_topics, rubric)
VALUES (
  'Data Engineering',
  'System design for data pipelines, warehouses, streaming systems, and analytics infrastructure',
  'data',
  '[
    {"name": "Data Warehouse", "order": 1, "difficulty": "hard", "example_systems": ["Snowflake", "BigQuery", "Redshift"]},
    {"name": "ETL Pipeline", "order": 2, "difficulty": "medium", "example_systems": ["Airflow DAGs", "dbt pipelines", "Fivetran"]},
    {"name": "Streaming Analytics", "order": 3, "difficulty": "hard", "example_systems": ["Kafka Streams", "Flink", "Spark Streaming"]},
    {"name": "Log Aggregation", "order": 4, "difficulty": "medium", "example_systems": ["ELK Stack", "Splunk", "Datadog"]},
    {"name": "Metrics Platform", "order": 5, "difficulty": "hard", "example_systems": ["Prometheus + Grafana", "Datadog", "New Relic"]}
  ]'::JSONB,
  5,
  '{"depth": 3, "tradeoffs": 3, "clarity": 2, "scalability": 2}'::JSONB
)
ON CONFLICT (name) DO UPDATE SET
  description = EXCLUDED.description,
  topics = EXCLUDED.topics,
  total_topics = EXCLUDED.total_topics;
