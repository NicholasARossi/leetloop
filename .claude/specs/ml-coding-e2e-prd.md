# ML Coding Drills — Playwright E2E Tests — Ralph Loop PRD

## Overview
Full Playwright E2E test suite for the ML Coding Drills feature. Covers the `/ml-coding` page (daily exercises, code editor, submit + grade flow, regeneration) and the `MLCodingDashboardCard` on `/dashboard`. All API responses are mocked with `page.route()` — no real backend needed.

## Task List (effort-aware)

### Batch 1: Test file scaffold + mock data + helpers (effort: low)

Create `clients/web/tests/ml-coding.spec.ts` with all mock data and helper functions.

**Mock data:**
- `mockExercises` — 3 exercises matching `MLCodingDailyExercise`: 1 review (K-Means, pending), 2 new (Logistic Regression + PCA, pending). Each has `prompt_text` with a coding task, `starter_code` with def stub, `problem_title`, `problem_slug`.
- `mockBatch` — `MLCodingDailyBatch` wrapping the 3 exercises (completed_count: 0, total_count: 3, average_score: null)
- `mockGradePass` — `MLCodingExerciseGrade` with score 8.5, verdict 'pass', correctness_score 9.0, code_quality_score 7.5, math_understanding_score 8.0, feedback text, empty missed_concepts, 2 suggested_improvements
- `mockGradeFail` — `MLCodingExerciseGrade` with score 4.0, verdict 'fail', correctness_score 3.0, code_quality_score 5.0, math_understanding_score 4.0, 2 missed_concepts, feedback text, 1 suggested_improvement
- `mockCompletedBatch` — all 3 exercises with status 'completed', scores, verdicts, feedback, sub-scores
- `mockDashboardSummary` — `MLCodingDashboardSummary` with problems_attempted: 5, problems_total: 10, today_exercise_count: 3, today_completed_count: 1, average_score: 7.8, reviews_due_count: 2, recent_scores: [8.0, 7.5, 8.0]

**Helpers:**
- `setUserAuth(page)` — navigate to `/login`, set `localStorage` with `leetloop_user_id`
- `mockMLCodingDailyAPI(page, batch)` — mock `GET /api/ml-coding/{userId}/daily-exercises`
- `mockMLCodingSubmitAPI(page, grade)` — mock `POST /api/ml-coding/daily-exercises/*/submit`
- `mockMLCodingRegenerateAPI(page)` — mock `POST /api/ml-coding/{userId}/daily-exercises/regenerate` with modified exercises
- `mockMLCodingDashboardAPI(page, summary)` — mock `GET /api/ml-coding/{userId}/dashboard`
- `mockDashboardPageAPIs(page, opts)` — mock ALL dashboard endpoints (win rate, feed, system design, ml-coding, progress, focus notes, onboarding) so `/dashboard` renders without errors

- [ ] Create test file with all mock data and helpers
- [ ] Validate: `cd clients/web && npx tsc --noEmit tests/ml-coding.spec.ts --esModuleInterop --moduleResolution node --target es2020 --module commonjs --strict --skipLibCheck` compiles (or simply `pnpm typecheck` with no new errors)

### Batch 2: ML Coding page tests — loading + rendering (effort: medium)

Tests for the `/ml-coding` page loading states and exercise card rendering.

- [ ] **Test: loading state** — delay API response 2s, navigate to `/ml-coding`, assert "Loading ML coding drills..." visible
- [ ] **Test: exercises render after loading** — mock batch, navigate, assert "ML Coding Drills" heading visible, assert all 3 exercise prompt texts visible
- [ ] **Test: progress header shows correct count** — assert "0/3 problems" progress counter visible
- [ ] **Test: review badge shown on review exercises** — assert "Review" badge visible on K-Means exercise, "Review Problems" section heading visible
- [ ] **Test: new problems section shown** — assert "New Problems" section heading visible with 2 exercises
- [ ] **Test: code editor has dark theme** — assert `textarea` with `bg-gray-900` class exists for each exercise card
- [ ] **Test: starter code pre-filled** — assert textarea value contains the starter code `def` stub
- [ ] Validate: `cd clients/web && npx playwright test tests/ml-coding.spec.ts --project chromium --grep "Page Loading|Exercise Rendering"` — all pass

### Batch 3: ML Coding page tests — code submission + grading flow (effort: high)

Tests for the full submit → grade → display cycle.

- [ ] **Test: submit button disabled when only starter code** — assert "Submit Code" button is disabled initially (starter code counts as empty/unchanged)
- [ ] **Test: submit button enables when code is modified** — type additional code in textarea, assert "Submit Code" button becomes enabled
- [ ] **Test: grading state shown after submit** — delay submit response 1.5s, click "Submit Code", assert "Grading..." button text visible
- [ ] **Test: pass grade displays score and verdict** — mock submit with `mockGradePass`, submit code, assert score "8.5" visible, assert "Pass" badge visible
- [ ] **Test: graded card collapsed by default** — after grading, assert feedback text is NOT visible (collapsed), assert score IS visible on summary line
- [ ] **Test: expand graded card shows sub-scores** — click graded card summary, assert 3 sub-score boxes visible (Correctness "9.0", Code Quality "7.5", Math "8.0")
- [ ] **Test: expand graded card shows feedback** — click to expand, assert "Feedback:" label and feedback text visible
- [ ] **Test: expand graded card shows submitted code** — click to expand, assert "Your Code:" label visible, assert dark code block with submitted code exists
- [ ] **Test: expand graded card shows suggested improvements** — click to expand, assert "Improvements:" label visible, assert 2 improvement items visible
- [ ] **Test: fail grade shows missed concepts** — mock submit with `mockGradeFail`, submit code, expand card, assert "Missed Concepts:" label visible, assert 2 concept tags visible
- [ ] **Test: progress updates after grading** — assert progress changes from "0" to "1" after submitting one exercise
- [ ] Validate: `cd clients/web && npx playwright test tests/ml-coding.spec.ts --project chromium --grep "Grading Flow"` — all pass

### Batch 4: ML Coding page tests — completion + regeneration + errors (effort: medium)

- [ ] **Test: all-done summary when batch complete** — mock with `mockCompletedBatch`, navigate, assert "All done for today!" visible, assert "Completed" and "Avg Score" stats visible
- [ ] **Test: regenerate button visible** — assert "Regenerate" button visible on page
- [ ] **Test: regenerate replaces exercises** — click "Regenerate", assert "Regenerating..." text during request, assert new exercise texts appear with "[Regenerated]" prefix
- [ ] **Test: error state on API failure** — mock daily exercises to return 500, navigate, assert error message visible, assert "Retry" button visible
- [ ] **Test: retry after error** — click "Retry" button, mock success on second call, assert exercises load
- [ ] Validate: `cd clients/web && npx playwright test tests/ml-coding.spec.ts --project chromium --grep "Completion|Regeneration|Error"` — all pass

### Batch 5: Dashboard card tests (effort: medium)

Tests for `MLCodingDashboardCard` rendering on `/dashboard`.

- [ ] **Test: ML Coding card renders on dashboard** — mock all dashboard APIs including ML coding summary, navigate to `/dashboard`, assert "ML Coding Drills" card heading visible
- [ ] **Test: dashboard card shows progress bar** — assert "Problems covered" label visible, assert "5/10" progress text visible
- [ ] **Test: dashboard card shows stats grid** — assert "Today" stat with "1/3" visible, assert "Avg Score" with "7.8" visible, assert "Reviews" with "2" visible
- [ ] **Test: dashboard card shows reviews due badge** — assert "2 reviews due" badge visible
- [ ] **Test: dashboard card CTA links to /ml-coding** — assert "Start Coding" link visible, assert "Go" button visible, assert link href is `/ml-coding`
- [ ] **Test: dashboard card shows "View all problems" link** — assert "View all problems" link visible with href `/ml-coding`
- [ ] Validate: `cd clients/web && npx playwright test tests/ml-coding.spec.ts --project chromium --grep "Dashboard"` — all pass

## Verification
After all batches:
1. `cd clients/web && npx playwright test tests/ml-coding.spec.ts --project chromium` — all tests pass
2. `cd clients/web && pnpm typecheck` — no new errors (only pre-existing TS2802 in dashboard-timing.spec.ts)
3. No regressions in other test files

## Completion Promise
All Playwright E2E tests in `clients/web/tests/ml-coding.spec.ts` pass against mocked API data. Tests cover: page loading, exercise rendering with review/new sections, dark code editor with starter code, submit + grade flow with 3-dimension sub-scores, graded card expand/collapse, fail grade with missed concepts, completion summary, regeneration, error handling, and dashboard card with progress + stats + CTA. `<promise>COMPLETE</promise>`
