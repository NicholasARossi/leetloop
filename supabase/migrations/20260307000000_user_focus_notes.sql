-- Add focus_notes column to user_settings for steering feed generation
ALTER TABLE user_settings ADD COLUMN IF NOT EXISTS focus_notes TEXT;
