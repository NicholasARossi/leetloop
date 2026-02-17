-- Allow anon/service role access for backend API
DO $$ BEGIN
  CREATE POLICY "Anon can manage daily questions" ON system_design_daily_questions
    FOR ALL TO anon USING (true) WITH CHECK (true);
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;
