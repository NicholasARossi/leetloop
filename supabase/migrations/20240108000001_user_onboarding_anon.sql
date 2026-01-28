-- Anonymous access policies for user_onboarding table
-- Allows API access without auth for development/guest users

-- Allow anonymous select
CREATE POLICY "Anon can view onboarding"
  ON user_onboarding FOR SELECT
  USING (auth.role() = 'anon');

-- Allow anonymous insert
CREATE POLICY "Anon can insert onboarding"
  ON user_onboarding FOR INSERT
  WITH CHECK (auth.role() = 'anon');

-- Allow anonymous update
CREATE POLICY "Anon can update onboarding"
  ON user_onboarding FOR UPDATE
  USING (auth.role() = 'anon');
