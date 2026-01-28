-- Anonymous access policies for meta objectives (demo mode)
-- Allows access via service key for API server

-- Templates - anyone can read
CREATE POLICY "Anon can view objective templates"
  ON objective_templates FOR SELECT TO anon
  USING (true);

-- Meta objectives - anon access for API
CREATE POLICY "Anon can view all objectives"
  ON meta_objectives FOR SELECT TO anon
  USING (true);

CREATE POLICY "Anon can insert objectives"
  ON meta_objectives FOR INSERT TO anon
  WITH CHECK (true);

CREATE POLICY "Anon can update objectives"
  ON meta_objectives FOR UPDATE TO anon
  USING (true);

CREATE POLICY "Anon can delete objectives"
  ON meta_objectives FOR DELETE TO anon
  USING (true);

-- Objective progress - anon access for API
CREATE POLICY "Anon can view all progress"
  ON objective_progress FOR SELECT TO anon
  USING (true);

CREATE POLICY "Anon can insert progress"
  ON objective_progress FOR INSERT TO anon
  WITH CHECK (true);

CREATE POLICY "Anon can update progress"
  ON objective_progress FOR UPDATE TO anon
  USING (true);
