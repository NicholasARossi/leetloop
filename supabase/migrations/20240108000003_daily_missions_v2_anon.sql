-- Anonymous access policies for mission_problems table
-- Allows API access without auth for development/guest users

-- Allow anonymous select through mission relationship
CREATE POLICY "Anon can view mission problems"
  ON mission_problems FOR SELECT
  USING (auth.role() = 'anon');

-- Allow anonymous insert
CREATE POLICY "Anon can insert mission problems"
  ON mission_problems FOR INSERT
  WITH CHECK (auth.role() = 'anon');

-- Allow anonymous update
CREATE POLICY "Anon can update mission problems"
  ON mission_problems FOR UPDATE
  USING (auth.role() = 'anon');

-- Allow anonymous delete
CREATE POLICY "Anon can delete mission problems"
  ON mission_problems FOR DELETE
  USING (auth.role() = 'anon');
