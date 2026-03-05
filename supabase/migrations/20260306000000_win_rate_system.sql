-- Win Rate Targeting System
-- Creates tables for win rate targets, daily problem feed, metric attempts, and win rate snapshots

-- Win Rate Targets: user's target solve rates per difficulty
CREATE TABLE IF NOT EXISTS win_rate_targets (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL UNIQUE,
  easy_target REAL NOT NULL DEFAULT 0.90,
  medium_target REAL NOT NULL DEFAULT 0.70,
  hard_target REAL NOT NULL DEFAULT 0.50,
  optimality_threshold REAL NOT NULL DEFAULT 70.0,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Daily Problem Feed: pre-generated daily problems (~30/day)
CREATE TABLE IF NOT EXISTS daily_problem_feed (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL,
  feed_date DATE NOT NULL,
  problem_slug TEXT NOT NULL,
  problem_title TEXT,
  difficulty TEXT CHECK (difficulty IN ('Easy', 'Medium', 'Hard')),
  tags TEXT[] DEFAULT '{}',
  feed_type TEXT NOT NULL CHECK (feed_type IN ('practice', 'metric')),
  practice_source TEXT CHECK (practice_source IN ('review', 'weak_skill', 'path', 'insight')),
  practice_reason TEXT,
  metric_rationale TEXT,
  sort_order INTEGER NOT NULL,
  status TEXT DEFAULT 'pending' CHECK (status IN ('pending', 'completed', 'skipped')),
  completed_at TIMESTAMPTZ,
  submission_id UUID,
  was_accepted BOOLEAN,
  was_optimal BOOLEAN,
  runtime_percentile REAL,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE(user_id, feed_date, problem_slug)
);

-- Metric Attempts: win rate measurement log
CREATE TABLE IF NOT EXISTS metric_attempts (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL,
  problem_slug TEXT NOT NULL,
  difficulty TEXT NOT NULL CHECK (difficulty IN ('Easy', 'Medium', 'Hard')),
  submission_id UUID REFERENCES submissions(id),
  feed_item_id UUID REFERENCES daily_problem_feed(id),
  accepted BOOLEAN NOT NULL,
  runtime_percentile REAL,
  optimal BOOLEAN NOT NULL DEFAULT FALSE,
  gemini_optimal BOOLEAN,
  gemini_time_complexity TEXT,
  gemini_space_complexity TEXT,
  final_optimal BOOLEAN NOT NULL DEFAULT FALSE,
  attempted_at TIMESTAMPTZ NOT NULL,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Win Rate Snapshots: materialized rates per user per day
CREATE TABLE IF NOT EXISTS win_rate_snapshots (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL,
  snapshot_date DATE NOT NULL,
  easy_rate_alltime REAL DEFAULT 0.0,
  easy_attempts_alltime INTEGER DEFAULT 0,
  easy_optimal_alltime INTEGER DEFAULT 0,
  medium_rate_alltime REAL DEFAULT 0.0,
  medium_attempts_alltime INTEGER DEFAULT 0,
  medium_optimal_alltime INTEGER DEFAULT 0,
  hard_rate_alltime REAL DEFAULT 0.0,
  hard_attempts_alltime INTEGER DEFAULT 0,
  hard_optimal_alltime INTEGER DEFAULT 0,
  easy_rate_30d REAL DEFAULT 0.0,
  easy_attempts_30d INTEGER DEFAULT 0,
  easy_optimal_30d INTEGER DEFAULT 0,
  medium_rate_30d REAL DEFAULT 0.0,
  medium_attempts_30d INTEGER DEFAULT 0,
  medium_optimal_30d INTEGER DEFAULT 0,
  hard_rate_30d REAL DEFAULT 0.0,
  hard_attempts_30d INTEGER DEFAULT 0,
  hard_optimal_30d INTEGER DEFAULT 0,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE(user_id, snapshot_date)
);

-- Indexes
CREATE INDEX idx_daily_problem_feed_user_date ON daily_problem_feed(user_id, feed_date);
CREATE INDEX idx_daily_problem_feed_status ON daily_problem_feed(status);
CREATE INDEX idx_metric_attempts_user ON metric_attempts(user_id);
CREATE INDEX idx_metric_attempts_difficulty ON metric_attempts(user_id, difficulty);
CREATE INDEX idx_win_rate_snapshots_user ON win_rate_snapshots(user_id, snapshot_date);

-- RLS policies
ALTER TABLE win_rate_targets ENABLE ROW LEVEL SECURITY;
ALTER TABLE daily_problem_feed ENABLE ROW LEVEL SECURITY;
ALTER TABLE metric_attempts ENABLE ROW LEVEL SECURITY;
ALTER TABLE win_rate_snapshots ENABLE ROW LEVEL SECURITY;

-- win_rate_targets policies
CREATE POLICY "Users can view own targets" ON win_rate_targets
    FOR SELECT USING (auth.uid() = user_id);
CREATE POLICY "Users can insert own targets" ON win_rate_targets
    FOR INSERT WITH CHECK (auth.uid() = user_id);
CREATE POLICY "Users can update own targets" ON win_rate_targets
    FOR UPDATE USING (auth.uid() = user_id);
CREATE POLICY "Anon can manage all targets" ON win_rate_targets
    FOR ALL USING (auth.role() = 'anon');

-- daily_problem_feed policies
CREATE POLICY "Users can view own feed" ON daily_problem_feed
    FOR SELECT USING (auth.uid() = user_id);
CREATE POLICY "Users can insert own feed" ON daily_problem_feed
    FOR INSERT WITH CHECK (auth.uid() = user_id);
CREATE POLICY "Users can update own feed" ON daily_problem_feed
    FOR UPDATE USING (auth.uid() = user_id);
CREATE POLICY "Anon can manage all feed" ON daily_problem_feed
    FOR ALL USING (auth.role() = 'anon');

-- metric_attempts policies
CREATE POLICY "Users can view own metric attempts" ON metric_attempts
    FOR SELECT USING (auth.uid() = user_id);
CREATE POLICY "Users can insert own metric attempts" ON metric_attempts
    FOR INSERT WITH CHECK (auth.uid() = user_id);
CREATE POLICY "Anon can manage all metric attempts" ON metric_attempts
    FOR ALL USING (auth.role() = 'anon');

-- win_rate_snapshots policies
CREATE POLICY "Users can view own snapshots" ON win_rate_snapshots
    FOR SELECT USING (auth.uid() = user_id);
CREATE POLICY "Users can insert own snapshots" ON win_rate_snapshots
    FOR INSERT WITH CHECK (auth.uid() = user_id);
CREATE POLICY "Users can update own snapshots" ON win_rate_snapshots
    FOR UPDATE USING (auth.uid() = user_id);
CREATE POLICY "Anon can manage all snapshots" ON win_rate_snapshots
    FOR ALL USING (auth.role() = 'anon');

-- Submission matching trigger: auto-match submissions to feed items
CREATE OR REPLACE FUNCTION match_submission_to_feed()
RETURNS TRIGGER AS $$
DECLARE
  v_feed_item RECORD;
  v_threshold REAL;
  v_is_optimal BOOLEAN;
BEGIN
  IF NEW.status NOT IN ('Accepted', 'Wrong Answer', 'Time Limit Exceeded',
                         'Memory Limit Exceeded', 'Runtime Error') THEN
    RETURN NEW;
  END IF;

  SELECT df.*, wrt.optimality_threshold
  INTO v_feed_item
  FROM daily_problem_feed df
  LEFT JOIN win_rate_targets wrt ON wrt.user_id = df.user_id
  WHERE df.user_id = NEW.user_id
    AND df.feed_date = CURRENT_DATE
    AND df.problem_slug = NEW.problem_slug
    AND df.status = 'pending'
  LIMIT 1;

  IF NOT FOUND THEN
    RETURN NEW;
  END IF;

  v_threshold := COALESCE(v_feed_item.optimality_threshold, 70.0);
  v_is_optimal := (NEW.status = 'Accepted' AND
                   NEW.runtime_percentile IS NOT NULL AND
                   NEW.runtime_percentile >= v_threshold);

  UPDATE daily_problem_feed SET
    status = 'completed',
    completed_at = NEW.submitted_at,
    submission_id = NEW.id,
    was_accepted = (NEW.status = 'Accepted'),
    was_optimal = v_is_optimal,
    runtime_percentile = NEW.runtime_percentile
  WHERE id = v_feed_item.id;

  IF v_feed_item.feed_type = 'metric' THEN
    INSERT INTO metric_attempts (
      user_id, problem_slug, difficulty, submission_id, feed_item_id,
      accepted, runtime_percentile, optimal, final_optimal, attempted_at
    ) VALUES (
      NEW.user_id, NEW.problem_slug, v_feed_item.difficulty, NEW.id, v_feed_item.id,
      (NEW.status = 'Accepted'), NEW.runtime_percentile, v_is_optimal, v_is_optimal,
      NEW.submitted_at
    );
  END IF;

  RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

CREATE TRIGGER on_submission_match_feed
AFTER INSERT ON submissions
FOR EACH ROW EXECUTE FUNCTION match_submission_to_feed();
