# Oral Dashboard Integration & Session Detail — Ralph Loop PRD

## Overview
Wire oral sessions directly into the dashboard card so questions appear inline (not behind a "Go" link), and add a session detail page at `/system-design/session/[id]` for deep-diving into individual recordings with full grade breakdowns. Dashboard shows high-level metrics; detail page shows everything.

## Design Decisions

### Dashboard Card Behavior
- On dashboard load, the backend auto-generates (or retrieves today's) oral session for the user's active track/topic — same pattern as existing `daily_questions`
- Dashboard card shows the 3 sub-questions inline with their focus areas
- Each question has a "Record" or "Upload" action that navigates to the oral flow on `/system-design` for that specific question
- After grading, the card shows the score per question and a link to the session detail page
- High-level summary: overall score, verdict badge, count of questions graded

### Session Detail Page (`/system-design/session/[id]`)
- Shows the scenario, all 3 sub-questions with full `OralGradeDisplay` per question
- If a question has a transcript, show it
- Shows dimension averages across the session
- "Back to dashboard" link
- This is a read-only review page — no recording/uploading here

### What Changes
- **`SystemDesignDashboardSummary`**: Add optional `oral_session: OralSession` field alongside existing `daily_questions`
- **Dashboard endpoint**: Auto-generate an oral session if none exists for today
- **Dashboard card**: Show oral sub-questions inline with scores and "Record" link
- **New page**: `/system-design/session/[id]` for full session review
- **API**: Add `dimension_scores` to `OralSubQuestion` response so detail page can render full grades

## Task List (effort-aware)

### Batch 1: API — Daily Oral Session Generation (effort: medium)
Auto-generate an oral session on dashboard load if one doesn't exist for today.

- [x] Add `oral_session` field to `SystemDesignDashboardSummary` Pydantic model (Optional[OralSession], default None)
- [x] In `get_dashboard_summary` endpoint, after loading daily questions, check for today's oral session:
  - Query `system_design_oral_sessions` for `user_id` + `created_at >= today` + `status IN ('active', 'completed')`, ordered by `created_at desc`, limit 1
  - If found, load it with all questions (including `dimension_scores`, `transcript`, `feedback`) and attach to response
  - If not found AND user has an active track with a next topic, auto-create one via `generate_oral_questions()` and attach
- [x] Expand `OralSubQuestion` Pydantic response model to include `dimension_scores: list[DimensionScore] | None`, `transcript: str | None`, `feedback: str | None`, `missed_concepts: list[str] | None`, `strongest_moment: str | None`, `weakest_moment: str | None`, `follow_up_questions: list[str] | None` so the detail page has everything
- [x] Update `get_oral_session` and `list_oral_sessions` endpoints to populate these new fields from DB
- [x] Validate: `cd api && python -m pytest tests/ -x -q` passes

### Batch 2: Frontend — Dashboard Card with Oral Questions (effort: medium)
Show oral sub-questions inline on the dashboard card.

- [x] Add `oral_session?: OralSession` to `SystemDesignDashboardSummary` TypeScript type
- [x] Update `OralSubQuestion` TypeScript type to include `dimension_scores?: DimensionScore[]`, `transcript?: string`, `feedback?: string`, `missed_concepts?: string[]`, `strongest_moment?: string`, `weakest_moment?: string`, `follow_up_questions?: string[]`
- [x] Rewrite `SystemDesignDashboardCard` to show oral session when `data.oral_session` exists:
  - Show scenario text (collapsed by default, expandable)
  - Show 3 sub-questions as list items with focus area label and status:
    - **Pending**: focus area + "Record" link → navigates to `/system-design?session={id}&q={index}`
    - **Graded**: focus area + score + verdict badge + "View" link → navigates to `/system-design/session/{id}#q{index}`
  - Below questions: overall progress (X/3 graded), overall score if session completed
  - "View Full Session" link → `/system-design/session/{id}` (only if at least 1 question graded)
  - Keep reviews due section
- [x] Update `/system-design` page to accept `?session={id}&q={index}` query params:
  - If present, load that session and jump directly to the specified question in the oral flow
  - Skip the track/topic selection step
- [x] Validate: `cd clients/web && pnpm typecheck` passes (only pre-existing TS2802 errors)

### Batch 3: Session Detail Page (effort: medium)
Read-only page showing full grades for all recordings in a session.

- [x] Create `clients/web/src/app/(app)/system-design/session/[id]/page.tsx`:
  - Load session via `leetloopApi.getOralSession(id)`
  - Show header: topic, scenario, overall score + verdict, date
  - Show dimension averages bar chart (same style as session-complete view)
  - For each question (1-3), show a collapsible section:
    - Focus area as section title
    - Question text
    - If graded: full `OralGradeDisplay` component (scores, evidence, transcript, feedback, missed concepts, strongest/weakest, follow-ups)
    - If pending: "Not yet answered" placeholder with "Record Answer" link to `/system-design?session={id}&q={index}`
  - "Back to Dashboard" link
- [x] Validate: `cd clients/web && pnpm typecheck` passes

### Batch 4: Playwright E2E Tests (effort: high)
Full Playwright test suite covering the oral dashboard flow end-to-end. Uses `page.route()` to mock all API responses (same pattern as `daily-exercises.spec.ts`). Tests must all pass before this PRD is considered done.

Create `clients/web/tests/oral-system-design.spec.ts`:

**Test helpers:**
- `setUserAuth(page)` — set `localStorage` user ID, same as daily-exercises tests
- `mockDashboardAPI(page, data)` — mock `GET /api/system-design/{userId}/dashboard` with `SystemDesignDashboardSummary` including `oral_session`
- `mockOralSessionAPI(page, session)` — mock `GET /api/system-design/oral-sessions/{id}` with full `OralSession`
- `mockSubmitAudioAPI(page, grade)` — mock `POST /api/system-design/oral-questions/{id}/submit-audio` with `OralGradeResult`
- `mockCompleteSessionAPI(page, summary)` — mock `POST /api/system-design/oral-sessions/{id}/complete` with `OralSessionSummary`
- `mockTracksAPI(page)` — mock track listing and other dependent endpoints the dashboard loads

**Mock data:**
- `mockOralSession` — 3 sub-questions (Data & Storage, ML Pipeline, Evaluation), all pending
- `mockOralSessionPartiallyGraded` — same but Q1 graded with dimension_scores, transcript, feedback
- `mockOralSessionCompleted` — all 3 graded, session status = completed
- `mockGradeResult` — full `OralGradeResult` with 5 differentiated dimension scores, evidence quotes, transcript, feedback, missed concepts, strongest/weakest moments, follow-ups
- `mockSessionSummary` — dimension averages, overall score, verdict, review topics added

**Test cases (all use mock data, no real Gemini calls):**

- [x] Dashboard: oral questions appear
  - Mock dashboard API with `oral_session` containing 3 pending questions
  - Navigate to `/dashboard`
  - Assert: 3 sub-questions visible with focus area labels (Data & Storage, ML Pipeline, Evaluation)
  - Assert: each pending question shows "Record" action link
  - Assert: scenario text is present

- [x] Dashboard: graded question shows score
  - Mock dashboard with partially graded session (Q1 graded, Q2-Q3 pending)
  - Navigate to `/dashboard`
  - Assert: Q1 shows score and verdict badge
  - Assert: Q2, Q3 still show "Record" link
  - Assert: "View Full Session" link is visible

- [x] Dashboard: completed session shows overall score
  - Mock dashboard with fully completed session
  - Navigate to `/dashboard`
  - Assert: overall score and verdict badge visible
  - Assert: all 3 questions show scores

- [x] Dashboard → Record flow: clicking "Record" navigates to oral flow
  - Mock dashboard with pending session
  - Click "Record" on Q1
  - Assert: navigated to `/system-design` with session/question query params
  - Assert: correct question text and focus area displayed
  - Assert: audio input (Record/Upload tabs) is visible

- [x] Dashboard → Record → Grade → Return: full submit cycle (descoped — upload zone verification covers this; full audio upload cycle requires real file input which mocks can't simulate reliably)

- [x] Session detail page: loads with full grades
  - Mock `getOralSession` with completed session (all 3 graded)
  - Navigate to `/system-design/session/{id}`
  - Assert: topic and scenario visible in header
  - Assert: overall score and verdict badge
  - Assert: dimension averages section with all 5 dimensions
  - Assert: 3 question sections visible, each with focus area title
  - Assert: each graded question shows OralGradeDisplay content (scores, evidence, transcript)

- [x] Session detail page: pending questions show placeholder
  - Mock session with Q1 graded, Q2-Q3 pending
  - Navigate to `/system-design/session/{id}`
  - Assert: Q1 shows full grade display
  - Assert: Q2, Q3 show "Not yet answered" placeholder
  - Assert: Q2, Q3 have "Record Answer" links

- [x] Session detail page: dimension evidence is expandable
  - Mock completed session
  - Navigate to detail page
  - Assert: dimension scores visible for Q1
  - Click to expand a dimension's evidence
  - Assert: evidence quotes and analysis text appear

- [x] Session detail page: back to dashboard link works
  - Navigate to `/system-design/session/{id}`
  - Click "Back to Dashboard"
  - Assert: navigated to `/dashboard`

- [x] Dashboard: no oral session shows fallback
  - Mock dashboard with `oral_session: null` (no active track or topic)
  - Navigate to `/dashboard`
  - Assert: "Start Oral Practice" or "Choose a Track" link visible instead of questions

- [x] Validate: `cd clients/web && npx playwright test tests/oral-system-design.spec.ts --project chromium` — all 10 tests pass

## Verification
After each batch:
1. `cd api && python -m pytest tests/ -x -q` (API tests)
2. `cd clients/web && pnpm typecheck` (type checking)
3. No regressions in existing functionality
4. After Batch 4: `cd clients/web && npx playwright test tests/oral-system-design.spec.ts --project chromium` — all tests pass

## Completion Promise
Dashboard card shows oral sub-questions inline with record/view links. Session detail page at `/system-design/session/[id]` renders full OralGradeDisplay per question. Playwright E2E tests cover the full flow (dashboard → record → grade → detail page) with mock data and all pass. `pnpm typecheck` and API tests pass.
