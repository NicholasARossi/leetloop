-- Anonymous access policies for daily missions and problem stats
-- Allows API access without auth for development/demo purposes

-- Anon policies for daily_missions
CREATE POLICY "Anon can view all daily missions"
  ON daily_missions FOR SELECT TO anon
  USING (true);

CREATE POLICY "Anon can insert daily missions"
  ON daily_missions FOR INSERT TO anon
  WITH CHECK (true);

CREATE POLICY "Anon can update daily missions"
  ON daily_missions FOR UPDATE TO anon
  USING (true);

-- Anon policies for problem_attempt_stats
CREATE POLICY "Anon can view all problem stats"
  ON problem_attempt_stats FOR SELECT TO anon
  USING (true);

CREATE POLICY "Anon can insert problem stats"
  ON problem_attempt_stats FOR INSERT TO anon
  WITH CHECK (true);

CREATE POLICY "Anon can update problem stats"
  ON problem_attempt_stats FOR UPDATE TO anon
  USING (true);
