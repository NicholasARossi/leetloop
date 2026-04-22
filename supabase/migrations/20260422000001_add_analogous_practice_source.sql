-- Add 'analogous' to practice_source check constraint for new practice problem generation
ALTER TABLE daily_problem_feed DROP CONSTRAINT IF EXISTS daily_problem_feed_practice_source_check;
ALTER TABLE daily_problem_feed ADD CONSTRAINT daily_problem_feed_practice_source_check
  CHECK (practice_source IN ('review', 'review_queue', 'weak_skill', 'path', 'progression', 'insight', 'journal', 'analogous'));
