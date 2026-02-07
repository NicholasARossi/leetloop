-- Anon policies for System Design tables (API access)
-- Allows the API service to manage data on behalf of users

-- ============ Tracks: Already public read ============

-- ============ Sessions: Anon CRUD ============

CREATE POLICY "Anon can view all sessions"
  ON system_design_sessions FOR SELECT TO anon
  USING (true);

CREATE POLICY "Anon can insert sessions"
  ON system_design_sessions FOR INSERT TO anon
  WITH CHECK (true);

CREATE POLICY "Anon can update sessions"
  ON system_design_sessions FOR UPDATE TO anon
  USING (true);

CREATE POLICY "Anon can delete sessions"
  ON system_design_sessions FOR DELETE TO anon
  USING (true);

-- ============ Responses: Anon CRUD ============

CREATE POLICY "Anon can view all responses"
  ON system_design_responses FOR SELECT TO anon
  USING (true);

CREATE POLICY "Anon can insert responses"
  ON system_design_responses FOR INSERT TO anon
  WITH CHECK (true);

CREATE POLICY "Anon can update responses"
  ON system_design_responses FOR UPDATE TO anon
  USING (true);

-- ============ Grades: Anon CRUD ============

CREATE POLICY "Anon can view all grades"
  ON system_design_grades FOR SELECT TO anon
  USING (true);

CREATE POLICY "Anon can insert grades"
  ON system_design_grades FOR INSERT TO anon
  WITH CHECK (true);

-- ============ Review Queue: Anon CRUD ============

CREATE POLICY "Anon can view all review items"
  ON system_design_review_queue FOR SELECT TO anon
  USING (true);

CREATE POLICY "Anon can insert review items"
  ON system_design_review_queue FOR INSERT TO anon
  WITH CHECK (true);

CREATE POLICY "Anon can update review items"
  ON system_design_review_queue FOR UPDATE TO anon
  USING (true);

CREATE POLICY "Anon can delete review items"
  ON system_design_review_queue FOR DELETE TO anon
  USING (true);

-- ============ Track Progress: Anon CRUD ============

CREATE POLICY "Anon can view all track progress"
  ON user_track_progress FOR SELECT TO anon
  USING (true);

CREATE POLICY "Anon can insert track progress"
  ON user_track_progress FOR INSERT TO anon
  WITH CHECK (true);

CREATE POLICY "Anon can update track progress"
  ON user_track_progress FOR UPDATE TO anon
  USING (true);
