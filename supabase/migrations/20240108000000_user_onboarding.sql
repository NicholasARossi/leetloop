-- User Onboarding Schema
-- Tracks onboarding progress through the 4-step wizard

-- =============================================================================
-- User Onboarding - Tracks onboarding state
-- =============================================================================
CREATE TABLE IF NOT EXISTS user_onboarding (
  user_id UUID PRIMARY KEY,

  -- Step completion flags
  has_objective BOOLEAN DEFAULT FALSE,           -- Step 1: Set career goal
  extension_installed BOOLEAN DEFAULT FALSE,     -- Step 2: Chrome extension verified
  history_imported BOOLEAN DEFAULT FALSE,        -- Step 3: LeetCode history imported
  first_path_selected BOOLEAN DEFAULT FALSE,     -- Step 4: Learning path chosen

  -- Overall status
  onboarding_complete BOOLEAN DEFAULT FALSE,
  current_step INTEGER DEFAULT 1 CHECK (current_step >= 1 AND current_step <= 4),

  -- When extension was verified (for tracking)
  extension_verified_at TIMESTAMPTZ,
  history_imported_at TIMESTAMPTZ,

  -- How many problems were imported
  problems_imported_count INTEGER DEFAULT 0,

  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_user_onboarding_complete ON user_onboarding(onboarding_complete);
CREATE INDEX IF NOT EXISTS idx_user_onboarding_step ON user_onboarding(current_step);

-- =============================================================================
-- Row Level Security
-- =============================================================================
ALTER TABLE user_onboarding ENABLE ROW LEVEL SECURITY;

-- Users can view their own onboarding status
CREATE POLICY "Users can view own onboarding"
  ON user_onboarding FOR SELECT
  USING (auth.uid() = user_id);

-- Users can insert their own onboarding record
CREATE POLICY "Users can insert own onboarding"
  ON user_onboarding FOR INSERT
  WITH CHECK (auth.uid() = user_id);

-- Users can update their own onboarding
CREATE POLICY "Users can update own onboarding"
  ON user_onboarding FOR UPDATE
  USING (auth.uid() = user_id);

-- Service role has full access
CREATE POLICY "Service role full access to user_onboarding"
  ON user_onboarding FOR ALL
  USING (auth.role() = 'service_role');

-- =============================================================================
-- Function to auto-update onboarding_complete flag
-- =============================================================================
CREATE OR REPLACE FUNCTION update_onboarding_complete()
RETURNS TRIGGER AS $$
BEGIN
  -- Check if all steps are complete
  NEW.onboarding_complete := (
    NEW.has_objective = TRUE AND
    NEW.extension_installed = TRUE AND
    NEW.history_imported = TRUE AND
    NEW.first_path_selected = TRUE
  );

  -- Calculate current step (first incomplete step)
  IF NOT NEW.has_objective THEN
    NEW.current_step := 1;
  ELSIF NOT NEW.extension_installed THEN
    NEW.current_step := 2;
  ELSIF NOT NEW.history_imported THEN
    NEW.current_step := 3;
  ELSIF NOT NEW.first_path_selected THEN
    NEW.current_step := 4;
  ELSE
    NEW.current_step := 4;  -- All done, stay on last step
  END IF;

  NEW.updated_at := NOW();

  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger to auto-update onboarding status
DROP TRIGGER IF EXISTS trg_update_onboarding_complete ON user_onboarding;
CREATE TRIGGER trg_update_onboarding_complete
  BEFORE INSERT OR UPDATE ON user_onboarding
  FOR EACH ROW
  EXECUTE FUNCTION update_onboarding_complete();

-- =============================================================================
-- Function to create onboarding record when user creates objective
-- =============================================================================
CREATE OR REPLACE FUNCTION create_onboarding_on_objective()
RETURNS TRIGGER AS $$
BEGIN
  -- Create or update onboarding record when objective is created
  INSERT INTO user_onboarding (user_id, has_objective)
  VALUES (NEW.user_id, TRUE)
  ON CONFLICT (user_id) DO UPDATE SET
    has_objective = TRUE,
    updated_at = NOW();

  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger on meta_objectives
DROP TRIGGER IF EXISTS trg_create_onboarding_on_objective ON meta_objectives;
CREATE TRIGGER trg_create_onboarding_on_objective
  AFTER INSERT ON meta_objectives
  FOR EACH ROW
  EXECUTE FUNCTION create_onboarding_on_objective();

-- =============================================================================
-- Function to update onboarding when user selects a path
-- =============================================================================
CREATE OR REPLACE FUNCTION update_onboarding_on_path_select()
RETURNS TRIGGER AS $$
BEGIN
  -- Update onboarding when user sets current path
  UPDATE user_onboarding
  SET first_path_selected = TRUE, updated_at = NOW()
  WHERE user_id = NEW.user_id;

  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger on user_settings when current_path_id is set
DROP TRIGGER IF EXISTS trg_update_onboarding_on_path ON user_settings;
CREATE TRIGGER trg_update_onboarding_on_path
  AFTER INSERT OR UPDATE OF current_path_id ON user_settings
  FOR EACH ROW
  WHEN (NEW.current_path_id IS NOT NULL)
  EXECUTE FUNCTION update_onboarding_on_path_select();
