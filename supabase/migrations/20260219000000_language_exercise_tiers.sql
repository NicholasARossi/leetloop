-- Add new exercise types for tiered response format system
-- New types: error_correction, situational, dialogue, journal_entry, opinion_essay, story_continuation, letter_writing

-- Update language_daily_exercises exercise_type CHECK constraint
ALTER TABLE language_daily_exercises DROP CONSTRAINT IF EXISTS language_daily_exercises_exercise_type_check;
ALTER TABLE language_daily_exercises ADD CONSTRAINT language_daily_exercises_exercise_type_check
  CHECK (exercise_type IN (
    'vocabulary', 'grammar', 'fill_blank', 'conjugation',
    'sentence_construction', 'reading_comprehension',
    'error_correction', 'situational', 'dialogue',
    'journal_entry', 'opinion_essay', 'story_continuation', 'letter_writing'
  ));

-- Update language_attempts exercise_type CHECK constraint
ALTER TABLE language_attempts DROP CONSTRAINT IF EXISTS language_attempts_exercise_type_check;
ALTER TABLE language_attempts ADD CONSTRAINT language_attempts_exercise_type_check
  CHECK (exercise_type IN (
    'vocabulary', 'grammar', 'fill_blank', 'conjugation',
    'sentence_construction', 'reading_comprehension', 'dictation',
    'error_correction', 'situational', 'dialogue',
    'journal_entry', 'opinion_essay', 'story_continuation', 'letter_writing'
  ));
