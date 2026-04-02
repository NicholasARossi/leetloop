-- Add GCS audio path column for archiving recordings
ALTER TABLE onsite_prep_attempts ADD COLUMN IF NOT EXISTS audio_gcs_path TEXT;

-- Add ideal_answer (validated STAR story) to questions
ALTER TABLE onsite_prep_questions ADD COLUMN IF NOT EXISTS ideal_answer JSONB;

-- Add ideal_response (Gemini-generated ideal) to attempts
ALTER TABLE onsite_prep_attempts ADD COLUMN IF NOT EXISTS ideal_response JSONB;
