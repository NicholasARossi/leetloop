-- Allow users to delete their own daily missions
-- This enables the mission reset functionality

-- Add DELETE policy for daily_missions
CREATE POLICY "Users can delete own daily missions"
  ON daily_missions FOR DELETE
  USING (auth.uid() = user_id);

-- Add DELETE policy for mission_problems (cascades but explicit is safer)
CREATE POLICY "Users can delete own mission problems"
  ON mission_problems FOR DELETE
  USING (
    EXISTS (
      SELECT 1 FROM daily_missions dm
      WHERE dm.id = mission_problems.mission_id
      AND dm.user_id = auth.uid()
    )
  );
