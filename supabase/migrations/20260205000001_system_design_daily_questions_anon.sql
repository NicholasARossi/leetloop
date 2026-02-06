-- Allow anon/service role access for backend API
CREATE POLICY "Anon can manage daily questions" ON system_design_daily_questions
  FOR ALL USING (true) WITH CHECK (true);
