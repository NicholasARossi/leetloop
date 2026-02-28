# Gemini Feedback Optimization — Ralph Loop PRD

## Overview
Optimize all Gemini-driven feedback across LeetLoop's LeetCode side: code analysis, mission/side quest generation, recommendations, and tips. The current system captures submission outcomes but drops critical error context (actual vs expected output, error messages, test case counts). Every Gemini call operates blind — it knows you failed, but not *how*. This PRD closes that gap end-to-end: capture richer data, detect patterns across submissions, and feed intelligence back into every Gemini touchpoint.

## Implementation Status: COMPLETE

### Batch 1: Data Capture Enrichment
- Added `code_output`, `expected_output`, `status_msg`, `total_correct`, `total_testcases` to extension types (`InterceptorPayload`, `SubmissionPayload`)
- Updated `interceptor.ts` and `content.ts` to pass all 5 fields from `LeetCodeCheckResponse`
- Migration `20260227000000_submission_error_context.sql` adds columns to `submissions` table

### Batch 2: Enhanced Code Analysis
- Rewrote `GeminiGateway.analyze_code()` with status-specific context blocks (Wrong Answer, TLE/MLE, Runtime Error, Compile Error)
- Structured JSON response: `root_cause`, `the_fix`, `pattern_type`, `concept_gap`, `time_complexity`, `space_complexity`
- `CodeAnalyzer.analyze()` accepts error context + previous attempt history
- Router queries previous attempts from `submissions` table

### Batch 3: Submission Pattern Analyzer
- New service: `api/app/services/pattern_analyzer.py`
- `PatternAnalyzer.analyze_patterns()` detects recurring mistakes, learning velocity, blind spots
- Gemini prompt analyzes grouped failures with error context + skill scores
- Cache table `user_pattern_analysis` (migration `20260227000001`)
- Endpoint: `GET /patterns/{user_id}`

### Batch 4: Strategic Mission Generation
- `_build_gemini_context()` queries cached pattern analysis + recent failure details with error context
- Prompt includes pattern analysis section, failure details, blind spot instructions
- Side quest generation: 2-3 quests targeting blind spots or reinforcing concepts
- Velocity-aware difficulty adjustment

### Batch 5: Feedback Loop & Adaptive Tips
- `submission_insights` table (migration `20260227000002`) stores per-submission `pattern_type`, `concept_gap`, `root_cause`
- Insights stored automatically after each code analysis
- `RecommendationEngine` queries insights for recurring pattern-driven recommendations
- `generate_tips()` overhauled with pattern analysis, aggregated insights, progress acknowledgment

### Batch 6: Review & Polish
- 50 API tests passing, extension builds clean, TypeScript typecheck clean (pre-existing TS2802 only)
- Frontend `api.ts` updated with new types (`CodeAnalysis`, `PatternInsight`, `UserPatterns`) and API methods

## Files Changed
- `clients/extension/src/types.ts`
- `clients/extension/src/interceptor.ts`
- `clients/extension/src/content.ts`
- `api/app/services/gemini_gateway.py`
- `api/app/services/code_analyzer.py`
- `api/app/services/mission_generator.py`
- `api/app/services/recommendation_engine.py`
- `api/app/services/pattern_analyzer.py` (new)
- `api/app/models/schemas.py`
- `api/app/routers/coaching.py`
- `clients/web/src/lib/api.ts`
- `supabase/migrations/20260227000000_submission_error_context.sql` (new)
- `supabase/migrations/20260227000001_user_pattern_analysis.sql` (new)
- `supabase/migrations/20260227000002_submission_insights.sql` (new)
