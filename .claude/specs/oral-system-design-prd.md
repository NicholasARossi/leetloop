# Oral System Design Practice — Ralph Loop PRD

## Overview
Replace the text-based system design practice with an oral practice mode. Users record themselves talking through system design problems (via in-browser recording or audio file upload), and Gemini evaluates both the technical content and communication quality. Questions are broken into focused sub-aspects (data modeling, inference pipelines, A/B testing, etc.) so you practice one dimension at a time — closer to how real interviews probe depth.

## Design Decisions

### Audio Flow
- **In-browser recording**: MediaRecorder API → WebM/opus → upload to API
- **File upload**: Drag-and-drop or file picker for pre-recorded audio (mp3, wav, m4a, webm)
- **Gemini multimodal**: Send audio directly to Gemini for combined transcription + evaluation (one API call, no separate transcription step)
- **Target duration**: Each sub-question has a suggested talk time (3-5 min). Timer shown during recording with visual cues (too short / good / wrapping up)

### Question Structure
Each topic (e.g., "Netflix Recommendation System") generates 3 focused sub-questions, each targeting a different aspect:
1. **Data & Storage** — "How would you model the data for Netflix recommendations? Walk me through the entities, relationships, and storage choices."
2. **ML Pipeline & Inference** — "Design the batch and real-time inference pipeline. How do candidates get generated and ranked?"
3. **Evaluation & Iteration** — "How would you set up A/B testing for this recommendation system? What metrics matter?"

Sub-questions are served one at a time. Complete one → get feedback → move to next. This avoids burnout while still covering breadth.

### Grading Rubric (Applied Scientist focus)

Gemini evaluates on 5 dimensions (each 1-10) with **few-shot behavioral anchors** and **mandatory citation of evidence** from the transcript.

#### Dimensions

**1. Technical Depth** (weight: 2)
How deep does the candidate go beyond "I'd use X"?
- **2-3 (Surface):** Names technologies without justification. "I'd use Kafka." No discussion of why, configuration, or failure modes.
- **4-5 (Shallow):** Mentions technologies with basic rationale but doesn't explore edge cases or quantify. "I'd use Kafka because it handles high throughput" — but no partition strategy, no retention discussion, no numbers.
- **6-7 (Solid):** Discusses specific configurations, capacity estimates, or failure scenarios for at least some components. "We'd partition by user_id, set 7-day retention, and need roughly 50K events/sec based on 100M DAU with 500 interactions/day."
- **8-9 (Expert):** Proactively addresses failure modes, capacity planning with math, and implementation details that show real experience. Discusses what breaks at scale and how to mitigate.

**2. Structure & Approach** (weight: 1.5)
Does the candidate have a framework, or are they stream-of-consciousness?
- **2-3 (Chaotic):** Jumps between topics randomly. No clear sections. Starts implementing before scoping.
- **4-5 (Loose):** Has a general direction but backtracks frequently. Some logical flow but no explicit structure. "Oh wait, I should have mentioned..."
- **6-7 (Organized):** Clear sections (requirements → high-level design → deep dive). Signposts transitions. "Now let me talk about the storage layer." Covers the question scope without major tangents.
- **8-9 (Exemplary):** Opens with clarifying the scope/requirements, states assumptions explicitly, builds from high-level to detail systematically. Easy to follow even without visual aids.

**3. Trade-off Reasoning** (weight: 2)
Does the candidate weigh alternatives, or just present one solution?
- **2-3 (None):** Presents one solution as if it's the only option. No "alternatively" or "the tradeoff here is."
- **4-5 (Surface):** Mentions that alternatives exist but doesn't deeply compare. "You could also use Redis but I'd go with Memcached" — without explaining why.
- **6-7 (Thoughtful):** Explicitly compares 2+ options on specific criteria (latency, cost, consistency). "DynamoDB gives us single-digit ms reads at scale but limits our query patterns. Postgres gives flexibility but we'd need read replicas for this throughput."
- **8-9 (Rigorous):** Frames decisions as trade-off matrices. Discusses when their choice would be wrong. "If our access pattern shifts to more ad-hoc queries, we'd need to revisit this — probably move to a hybrid approach."

**4. ML/Data Fluency** (weight: 2) — for MLE/DE tracks
Does the candidate demonstrate working knowledge of ML systems and data pipelines?
- **2-3 (Textbook):** Mentions ML concepts by name only. "We'd use collaborative filtering." No discussion of features, training, serving, or evaluation.
- **4-5 (Basic):** Understands the ML pipeline at a high level but stays abstract. Mentions training and serving but doesn't discuss feature engineering, model selection rationale, or online/offline evaluation.
- **6-7 (Practitioner):** Discusses specific feature types, model architectures with rationale, training/serving split, and at least one evaluation approach. Shows awareness of ML-specific challenges (data drift, cold start, training-serving skew).
- **8-9 (Expert):** Connects ML choices to business metrics. Discusses feature stores, experiment frameworks, model monitoring, and iteration cycles. Can articulate why one model type fits this problem better than alternatives with specific reasoning.

**5. Communication Quality** (weight: 1.5)
Would an interviewer enjoy listening to this? Could they follow along?
- **2-3 (Hard to follow):** Excessive filler words (um, uh, like). Long pauses. Contradicts self without correction. Interviewer would be lost.
- **4-5 (Passable):** Gets the point across but with significant filler, repetition, or tangents. Ideas are there but buried in verbal noise. Frequent self-corrections without signposting.
- **6-7 (Clear):** Mostly fluent with occasional filler. Key points land clearly. Uses transitions ("so for storage...", "moving to the serving layer..."). Self-corrects cleanly when needed.
- **8-9 (Polished):** Confident delivery. Minimal filler. Concise — doesn't over-explain simple points. Adjusts pace for complex vs simple topics. Sounds like they've explained this system before.

#### Grading Rules (enforced in prompt)
1. **CITE EVIDENCE.** For every dimension score, quote 1-2 specific phrases (10+ words each) from the transcript that justify the score.
2. **DIFFERENTIATE SCORES.** If all dimensions score within 1 point of each other, re-evaluate — it's extremely unlikely that a candidate is equally strong/weak across all dimensions.
3. **SCOPE TO THE QUESTION.** Only evaluate what the question asked. If the question is about data modeling, do NOT penalize for not covering A/B testing or real-time inference.
4. **DURATION MATTERS.** A 2-minute answer to a 5-minute question should be penalized under Structure (didn't cover enough ground). A 10-minute answer to a 3-minute question should be penalized under Communication (couldn't be concise).
5. **ORAL-SPECIFIC.** This is a spoken response, not written. Expect some natural filler — penalize patterns, not individual "um"s. Value confident delivery and clear signposting.

#### Score Computation (enforced in code, NOT by model)
- `overall_score = (technical_depth * 2 + structure * 1.5 + tradeoffs * 2 + ml_fluency * 2 + communication * 1.5) / 9`
- Verdict: `pass` (>= 7), `borderline` (5–6.9), `fail` (< 5) — computed in code from overall_score

#### Required Output Fields
- `transcript`: verbatim transcription including filler words
- `dimensions`: array of 5 objects, each with `name`, `score`, `evidence` (array of `{quote, analysis}`), `summary`
- `feedback`: 2-3 sentences of direct, actionable feedback
- `missed_concepts`: concepts relevant to THIS question only
- `strongest_moment`: single best quote from the transcript
- `weakest_moment`: single worst gap or mistake described
- `follow_up_questions`: 2-3 probing follow-ups based on gaps in THIS answer

### What Changes vs Current
- **Keep**: tracks, topics, review queue, spaced repetition, dashboard card, track progress
- **Replace**: text input → audio recorder + upload, text grading prompt → multimodal grading prompt with anchored rubric
- **Add**: audio upload endpoint, transcription display, duration timer, sub-question breakdown, 5-dimension cited rubric, strongest/weakest moments
- **Remove**: word count tracking, written response textarea (for system design only — language keeps text input)

## Task List (effort-aware)

### Batch 1: Database & Schemas (effort: low)
New tables and Pydantic models for the oral flow.

- [x] Create migration `supabase/migrations/20260311000000_oral_system_design.sql`:
  - `system_design_oral_sessions` table: `id uuid PK, user_id uuid, track_id uuid FK, topic text, scenario text, status text DEFAULT 'active' CHECK (status IN ('active','completed','abandoned')), created_at timestamptz, completed_at timestamptz`
  - `system_design_oral_questions` table: `id uuid PK, session_id uuid FK, part_number int, question_text text, focus_area text, key_concepts text[], suggested_duration_minutes int DEFAULT 4, audio_duration_seconds int, transcript text, dimension_scores jsonb, overall_score numeric, verdict text, feedback text, missed_concepts text[], strongest_moment text, weakest_moment text, follow_up_questions text[], status text DEFAULT 'pending' CHECK (status IN ('pending','graded')), created_at timestamptz, graded_at timestamptz`
  - RLS policies: authenticated users see own sessions/questions, anon/service role has full access
  - Indexes on `(user_id)`, `(session_id)`
- [x] Add Pydantic schemas in `api/app/models/system_design_schemas.py`:
  - `OralSessionCreate(track_id: str, topic: str)`
  - `OralSubQuestion(id: str, part_number: int, question_text: str, focus_area: str, key_concepts: list[str], suggested_duration_minutes: int, status: str)`
  - `OralSession(id: str, user_id: str, track_id: str, topic: str, scenario: str, status: str, questions: list[OralSubQuestion], created_at: str)`
  - `DimensionEvidence(quote: str, analysis: str)`
  - `DimensionScore(name: str, score: int, evidence: list[DimensionEvidence], summary: str)`
  - `OralGradeResult(transcript: str, dimensions: list[DimensionScore], overall_score: float, verdict: str, feedback: str, missed_concepts: list[str], strongest_moment: str, weakest_moment: str, follow_up_questions: list[str])`
  - `OralSessionSummary(session_id: str, topic: str, questions_graded: int, dimension_averages: dict[str, float], overall_score: float, verdict: str, review_topics_added: list[str])`
- [x] Validate: migration SQL is syntactically valid, `cd api && python -c "from app.models.system_design_schemas import OralGradeResult; print('OK')"`

### Batch 2: Oral Grading Service (effort: medium)
Core grading logic — Gemini multimodal audio → transcript + cited rubric scores.

- [x] Create `api/app/services/oral_grading_service.py` with `OralGradingService`:
  - `__init__`: configure Gemini model (same pattern as SystemDesignService)
  - `async transcribe_and_grade(audio_bytes: bytes, mime_type: str, question_text: str, focus_area: str, key_concepts: list[str], track_type: str, suggested_duration: int) -> OralGradeResult`
  - Uses `genai.upload_file()` to upload audio, then `model.generate_content([prompt, audio_file])` for multimodal grading
  - Prompt embeds the full rubric with behavioral anchors from this PRD
  - Parses JSON response, computes `overall_score` and `verdict` IN CODE (not trusting model)
  - Cleans up uploaded file after grading via `genai.delete_file()`
  - Singleton pattern: `get_oral_grading_service()` factory function
- [x] Add `_build_oral_grading_prompt(question_text, focus_area, key_concepts, track_type, suggested_duration) -> str` private method
  - Includes all 5 dimension anchors with score examples
  - Includes all 5 grading rules (cite evidence, differentiate, scope, duration, oral-specific)
  - Requests JSON output matching `OralGradeResult` schema (minus computed fields)
  - Minimum quote length instruction: "Each evidence quote must be at least 10 words from the transcript"
- [x] Add error handling: Gemini API failures return a clear error (no heuristic fallback for audio)
- [x] Test with demo audio file: `python3 -c "..."` script that loads `netfix.m4a` and runs `transcribe_and_grade()` — verify differentiated scores and cited evidence
- [x] Validate: `cd api && python -m pytest app/tests/ -x -q` passes

### Batch 3: API Endpoints (effort: medium)
REST endpoints for the oral session flow.

- [x] Add oral session endpoints in `api/app/routers/system_design.py`:
  - `POST /system-design/{user_id}/oral-session` — accepts `OralSessionCreate`, calls `generate_oral_questions()`, inserts session + questions into DB, returns `OralSession`
  - `GET /system-design/oral-sessions/{session_id}` — returns `OralSession` with all questions and their grades
  - `POST /system-design/oral-questions/{question_id}/submit-audio` — accepts `UploadFile` (audio), calls `OralGradingService.transcribe_and_grade()`, updates question row with transcript + scores, returns `OralGradeResult`
  - `POST /system-design/oral-sessions/{session_id}/complete` — computes aggregate dimension averages across all graded questions, updates session status, adds weak areas (dimension avg < 7) to `system_design_review_queue`, returns `OralSessionSummary`
  - `GET /system-design/{user_id}/oral-sessions` — list user's oral sessions with pagination (limit/offset), ordered by created_at desc
- [x] Add `generate_oral_questions(topic, track_type) -> tuple[str, list[OralSubQuestion]]` method to `SystemDesignService`:
  - Gemini prompt generates scenario + 3 focused sub-questions (Data & Storage, Core Pipeline, Evaluation & Ops)
  - Each sub-question has: question_text, focus_area, key_concepts (3-4), suggested_duration_minutes
  - Returns (scenario, sub_questions)
  - Fallback: deterministic sub-questions if Gemini unavailable
- [x] Wire `submit-audio` to handle file size validation (max 25MB), mime type validation (audio/webm, audio/mp4, audio/mpeg, audio/wav, audio/x-m4a)
- [x] Validate: `cd api && python -m pytest app/tests/ -x -q` passes, can manually test create session → get questions → submit audio → complete

### Batch 4: Frontend Audio Components (effort: high)
Build the recording, upload, timer, and grade display components.

- [x] Create `clients/web/src/components/system-design/AudioRecorder.tsx`
  - MediaRecorder API: start/stop recording (no pause — keep it simple)
  - Visual timer showing elapsed time with color zones: gray (< 1 min), accent (1-5 min), yellow (> 5 min)
  - Pulse animation while recording (CSS keyframes on a circle)
  - States: `idle` → `recording` → `preview` (with audio playback) → `uploading`
  - Buttons: "Start Recording" / "Stop & Review" / "Re-record" / "Submit"
  - Props: `suggestedDuration: number`, `onSubmit: (blob: Blob) => void`, `isUploading: boolean`
  - Exports WebM/opus blob on submit
- [x] Create `clients/web/src/components/system-design/AudioUploader.tsx`
  - Drag-and-drop zone + file picker button
  - Accepts: .mp3, .wav, .m4a, .webm (max 25MB)
  - Shows file name, duration (from HTMLAudioElement), file size
  - Props: `onSubmit: (file: File) => void`, `isUploading: boolean`
  - "Upload & Grade" button
- [x] Create `clients/web/src/components/system-design/OralGradeDisplay.tsx`
  - Transcript section (collapsible, starts expanded)
  - 5-dimension score bars (horizontal, colored by score: red < 5, yellow 5-6, green >= 7) with dimension name + score label
  - Each dimension expandable to show evidence quotes + analysis
  - Overall score + verdict badge (PASS green / BORDERLINE yellow / FAIL red)
  - Feedback text block
  - Missed concepts as tags/chips
  - Strongest moment (green highlight quote) + weakest moment (red highlight)
  - Follow-up questions list
  - Props: `grade: OralGradeResult`
- [x] Create `clients/web/src/components/system-design/SessionProgress.tsx`
  - Shows 3 sub-questions as steps: completed (with score) / current (highlighted) / upcoming (dimmed)
  - Horizontal step indicator with focus area labels
  - Props: `questions: OralSubQuestion[]`, `currentIndex: number`
- [x] Update barrel exports in `components/system-design/index.ts`
- [x] Validate: `cd clients/web && pnpm typecheck` passes (only pre-existing TS2802 errors in test file)

### Batch 5: Frontend Oral Practice Page (effort: high)
Rewrite the system design page for the oral flow.

- [x] Rewrite `clients/web/src/app/(app)/system-design/page.tsx` for oral flow:
  - Flow states: `select` → `session` → `question` → `grading` → `result` → (loop through questions) → `session-complete`
  - `select`: Keep existing TrackCard grid + topic picker. "Start Oral Session" button.
  - `session`: Show scenario text + SessionProgress component. Auto-advance to first question.
  - `question`: Current sub-question displayed (focus area, key concepts as chips, suggested duration). Tab toggle: "Record" | "Upload File". Renders AudioRecorder or AudioUploader based on tab.
  - `grading`: Loading spinner with "Gemini is evaluating your response..." (expect 10-30s). Show transcript streaming if possible, otherwise just animate.
  - `result`: OralGradeDisplay for current question. "Next Question" button (or "Complete Session" on last question).
  - `session-complete`: Aggregate dimension averages across all 3 questions. Overall session verdict. List of review topics added. "Start New Session" / "Back to Topics" buttons.
- [x] Update `clients/web/src/lib/api.ts` with new methods:
  - `createOralSession(userId: string, data: {track_id: string, topic: string}): Promise<OralSession>`
  - `getOralSession(sessionId: string): Promise<OralSession>`
  - `submitOralAudio(questionId: string, audioFile: Blob | File): Promise<OralGradeResult>` — uses FormData for multipart upload
  - `completeOralSession(sessionId: string): Promise<OralSessionSummary>`
  - `getOralSessions(userId: string, limit?: number): Promise<OralSession[]>`
- [x] Add TypeScript types to `api.ts`:
  - `OralSession`, `OralSubQuestion`, `DimensionEvidence`, `DimensionScore`, `OralGradeResult`, `OralSessionSummary`
- [x] Validate: `cd clients/web && pnpm typecheck && pnpm lint` passes (only pre-existing TS2802 errors; no eslint config exists)

### Batch 6: Dashboard & Integration (effort: medium)
Wire dashboard card, handle edge cases, ensure review queue works.

- [x] Update `SystemDesignDashboardCard.tsx`:
  - Replace inline text question input with "Start Oral Practice" button
  - Show most recent oral session: topic, overall score, verdict
  - Show count of sessions this week
  - Keep reviews due section as-is
- [x] Handle microphone permissions in AudioRecorder:
  - Call `navigator.mediaDevices.getUserMedia({audio: true})` on mount or first click
  - Show clear error message if permission denied: "Microphone access required for recording. You can also upload a pre-recorded audio file."
  - Fall back to upload-only mode if mic unavailable
- [x] Add loading/error states throughout:
  - Gemini timeout: show message after 30s "Still processing... audio evaluation can take up to a minute"
  - Network error on upload: show retry button, preserve audio blob in memory
  - File too large: client-side validation before upload with clear message (AudioUploader 25MB check)
- [x] Ensure review queue integration: verify that `complete` endpoint adds weak dimension topics to `system_design_review_queue` with appropriate reason text
- [x] Test full end-to-end flow manually: select track → pick topic → start oral session → record/upload for each of 3 questions → see grades with cited evidence → complete session → verify review queue
- [x] Validate: `cd clients/web && pnpm typecheck && pnpm lint` passes, `cd api && python -m pytest app/tests/ -x -q` passes

## Verification
After each batch:
1. `cd api && python -m pytest app/tests/ -x -q` (API tests)
2. `cd clients/web && pnpm typecheck` (type checking)
3. `cd clients/web && pnpm lint` (linting)
4. No regressions in existing functionality

## Completion Promise
All 6 batches complete. User can: (1) select a system design track/topic, (2) start an oral session with 3 focused sub-questions, (3) record audio in-browser OR upload an audio file for each question, (4) receive Gemini-powered grading with verbatim transcription, 5 differentiated dimension scores with cited evidence quotes, actionable feedback, strongest/weakest moments, and follow-up questions, (5) complete the session and see weak areas added to the review queue. `pnpm typecheck`, `pnpm lint`, and API tests all pass.
