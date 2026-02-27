-- Add error context columns to submissions table
-- Captures detailed failure information from LeetCode check responses

ALTER TABLE submissions ADD COLUMN IF NOT EXISTS code_output TEXT;
ALTER TABLE submissions ADD COLUMN IF NOT EXISTS expected_output TEXT;
ALTER TABLE submissions ADD COLUMN IF NOT EXISTS status_msg TEXT;
ALTER TABLE submissions ADD COLUMN IF NOT EXISTS total_correct INTEGER;
ALTER TABLE submissions ADD COLUMN IF NOT EXISTS total_testcases INTEGER;
