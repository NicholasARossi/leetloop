-- Rename onboarding column from has_objective to has_win_rate_target
ALTER TABLE user_onboarding RENAME COLUMN has_objective TO has_win_rate_target;

-- Create trigger for auto-setting onboarding on win_rate_targets insert
CREATE OR REPLACE FUNCTION set_onboarding_win_rate_target()
RETURNS TRIGGER AS $$
BEGIN
  UPDATE user_onboarding
  SET has_win_rate_target = TRUE, updated_at = NOW()
  WHERE user_id = NEW.user_id;
  RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

CREATE TRIGGER trg_set_onboarding_win_rate
AFTER INSERT ON win_rate_targets
FOR EACH ROW EXECUTE FUNCTION set_onboarding_win_rate_target();
