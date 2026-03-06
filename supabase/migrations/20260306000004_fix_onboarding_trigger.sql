-- Fix update_onboarding_complete trigger function to use renamed column
CREATE OR REPLACE FUNCTION update_onboarding_complete()
RETURNS TRIGGER AS $$
BEGIN
  -- Check if all steps are complete
  NEW.onboarding_complete := (
    NEW.has_win_rate_target = TRUE AND
    NEW.extension_installed = TRUE AND
    NEW.history_imported = TRUE AND
    NEW.first_path_selected = TRUE
  );

  -- Calculate current step (first incomplete step)
  IF NOT NEW.has_win_rate_target THEN
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
