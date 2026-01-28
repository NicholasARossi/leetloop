-- Function to reset a user's daily mission
-- Bypasses RLS by using SECURITY DEFINER

CREATE OR REPLACE FUNCTION reset_daily_mission(p_user_id UUID, p_mission_date DATE DEFAULT CURRENT_DATE)
RETURNS JSONB
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
  v_mission_id UUID;
  v_deleted_count INT := 0;
BEGIN
  -- Get the mission ID
  SELECT id INTO v_mission_id
  FROM daily_missions
  WHERE user_id = p_user_id AND mission_date = p_mission_date;

  IF v_mission_id IS NULL THEN
    RETURN jsonb_build_object('success', true, 'message', 'No mission found for this date');
  END IF;

  -- Delete mission problems (cascade should handle, but explicit)
  DELETE FROM mission_problems WHERE mission_id = v_mission_id;

  -- Delete the mission
  DELETE FROM daily_missions WHERE id = v_mission_id;
  GET DIAGNOSTICS v_deleted_count = ROW_COUNT;

  RETURN jsonb_build_object(
    'success', true,
    'message', 'Mission reset successfully',
    'deleted_count', v_deleted_count
  );
END;
$$;

-- Grant execute to anon and authenticated roles
GRANT EXECUTE ON FUNCTION reset_daily_mission(UUID, DATE) TO anon, authenticated;
