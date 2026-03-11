-- Drop deprecated text-based system design tables
-- These were replaced by the oral practice flow (system_design_oral_sessions / system_design_oral_questions)

DROP TABLE IF EXISTS system_design_grades CASCADE;
DROP TABLE IF EXISTS system_design_responses CASCADE;
DROP TABLE IF EXISTS system_design_sessions CASCADE;
DROP TABLE IF EXISTS system_design_daily_questions CASCADE;
DROP TABLE IF EXISTS system_design_attempts CASCADE;
