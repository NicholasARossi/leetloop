-- Remove objective system tables and related triggers

-- Drop triggers
DROP TRIGGER IF EXISTS on_submission_update_objective ON submissions;
DROP TRIGGER IF EXISTS trg_create_onboarding_on_objective ON meta_objectives;

-- Drop functions
DROP FUNCTION IF EXISTS update_objective_progress_on_submission();
DROP FUNCTION IF EXISTS create_onboarding_on_objective();

-- Drop all RLS policies
DROP POLICY IF EXISTS "Anyone can view objective templates" ON objective_templates;
DROP POLICY IF EXISTS "Anon can view objective templates" ON objective_templates;
DROP POLICY IF EXISTS "Users can view own objectives" ON meta_objectives;
DROP POLICY IF EXISTS "Users can insert own objectives" ON meta_objectives;
DROP POLICY IF EXISTS "Users can update own objectives" ON meta_objectives;
DROP POLICY IF EXISTS "Users can delete own objectives" ON meta_objectives;
DROP POLICY IF EXISTS "Anon can view all objectives" ON meta_objectives;
DROP POLICY IF EXISTS "Anon can insert objectives" ON meta_objectives;
DROP POLICY IF EXISTS "Anon can update objectives" ON meta_objectives;
DROP POLICY IF EXISTS "Anon can delete objectives" ON meta_objectives;
DROP POLICY IF EXISTS "Users can view own progress" ON objective_progress;
DROP POLICY IF EXISTS "Users can insert own progress" ON objective_progress;
DROP POLICY IF EXISTS "Users can update own progress" ON objective_progress;
DROP POLICY IF EXISTS "Anon can view all progress" ON objective_progress;
DROP POLICY IF EXISTS "Anon can insert progress" ON objective_progress;
DROP POLICY IF EXISTS "Anon can update progress" ON objective_progress;

-- Drop tables (order matters for FK)
DROP TABLE IF EXISTS objective_progress;
DROP TABLE IF EXISTS meta_objectives;
DROP TABLE IF EXISTS objective_templates;
