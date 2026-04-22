# Language Oral Practice v1 — Phase 1 Ralph Loop PRD

## Overview
Add oral recording + async grading to the language learning system. Users open `/language`, see a monologue prompt drawn from their current textbook chapter, record themselves speaking in French, and get graded asynchronously on 4 CEFR-aligned dimensions. The textbook is a deep well — each chapter generates many prompts via a pre-generated bank, and the progress bar fills as you work through chapter content day after day. Streaks track daily consistency.

## Phase 1 Scope
- Oral recording + grading loop on dashboard (no chaining, no Telegram, no error library)
- Pre-generated prompt bank per chapter (no on-the-fly Gemini prompt generation at page load)
- Async grading (fire-and-forget: record → confirmation → result appears later)
- Cloud STT (Chirp 2, fr-FR) for transcription
- 4-dimension rubric: grammar accuracy, lexical range, discourse/coherence, task completion
- Streak tracking
- Book progress bar

## Design Decisions

### Content Model
The textbook (`book_content`) is an infinite prompt generator. Each chapter's grammar rules, vocabulary, and themes feed a pre-generated bank of 10-20 oral prompts. The daily session serves prompts from the current chapter position. Progress bar = how far through the book you've drawn from. You never run out — each chapter generates many varied prompts.

### Prompt Bank
- Pre-generation script reads `book_content` for each chapter → calls Gemini to generate 10-20 monologue prompts per chapter
- Prompts stored in `language_oral_prompts` table
- Each prompt specifies: theme, grammar targets, vocab targets, suggested duration (60-180s)
- Prompt style: free monologue. "Décrivez une situation où..." / "Argumentez pour ou contre..." / "Expliquez en détail comment..."
- Daily session picks 2-3 unrecorded prompts from current chapter

### Transcription (Cloud STT French)
- **Primary**: Google Cloud Speech-to-Text (Chirp 2) with `language_codes=["fr-FR"]`
  - Same pipeline as onsite prep: format detection → ffmpeg conversion for non-WebM → GCS temp upload → BatchRecognize → cleanup
  - Automatic punctuation enabled
- **Fallback**: Gemini multimodal transcription with French prompt
  - "Transcris cet audio mot à mot. Inclus les hésitations (euh, hmm). Pas de commentaire, pas de formatage — juste la transcription brute."

### Grading Rubric (4 dimensions, CEFR C1 targets)

**1. Grammar Accuracy** (weight 2.0)
Conjugation, agreement, tense selection, syntax, register-appropriate structures.
- 1-2: Systematic errors impeding comprehension (wrong tenses, no agreement)
- 3-4: Frequent errors but message communicated; avoids complex structures
- 5-6: Good control of common structures; errors in complex ones (subjunctive, conditional past)
- 7-8: Consistent accuracy; handles complex structures with occasional slips
- 9-10: Near-native; confident use of subjunctive, concordance des temps, formal/informal register shifts

**2. Lexical Range** (weight 1.5)
Vocabulary breadth, precision, idiomatic usage, avoidance of anglicisms.
- 1-2: Very limited; relies on basic high-frequency words; frequent anglicisms
- 3-4: Adequate for simple topics; repetitive; imprecise word choice
- 5-6: Good range for familiar topics; some idiomatic expressions; occasional imprecision
- 7-8: Rich vocabulary; uses nuance (synonyms, register-appropriate terms); natural collocations
- 9-10: Near-native lexical precision; abstract vocabulary; natural use of expressions figées

**3. Discourse & Coherence** (weight 1.5)
Logical structure, cohesion markers, argumentation flow, topic development.
- 1-2: Disconnected fragments; no connectors; hard to follow
- 3-4: Basic connectors (et, mais, parce que); some logical flow but jumps between ideas
- 5-6: Varied connectors (donc, alors, cependant); clear progression; minor tangents
- 7-8: Sophisticated markers (en revanche, d'ailleurs, néanmoins, quoi qu'il en soit); well-structured argumentation
- 9-10: Seamless discourse; masterful use of concession, nuance, reformulation; rhetoric

**4. Task Completion** (weight 1.0)
Did the monologue address the prompt fully? Depth of engagement with the theme.
- 1-2: Barely addresses the prompt; very short or off-topic
- 3-4: Partially addresses prompt; surface-level treatment
- 5-6: Covers main aspects; adequate depth
- 7-8: Thorough treatment; engages with nuance of the prompt
- 9-10: Comprehensive; brings original perspective; goes beyond the minimum

### Grading Rules
1. **CITE EVIDENCE.** For each dimension, quote 1-2 specific phrases (5+ words) from the transcript.
2. **DIFFERENTIATE SCORES.** Scores should NOT all cluster within 1 point.
3. **ORAL-SPECIFIC.** This is spontaneous speech. Expect hesitation — penalize patterns, not individual "euh"s.
4. **IMMERSION.** All feedback in French. JSON field names in English.
5. **C1 TARGET.** Grade against CEFR C1 descriptors, not native-speaker perfection.

### Score Computation
- `overall_score = (grammar * 2.0 + lexical * 1.5 + discourse * 1.5 + task * 1.0) / 6.0`
- Verdict: `strong` (>= 7), `developing` (5-6.9), `needs_work` (< 5)
- Computed in code, NOT by the model.
- Scores are feedback — they do NOT gate book progression.

### Async Grading
- User records → POST audio → API returns `{ session_id, status: "grading" }` immediately
- Background: transcribe → grade → store result → update status to "graded"
- Frontend polls or checks on next page load for results
- Session card shows: "En cours d'évaluation..." while grading, then reveals full result

### Streak Tracking
- Columns on `user_language_settings`: `current_streak`, `longest_streak`, `last_practice_date`
- Streak increments when user completes at least 1 recording in a day
- Streak resets if a day is missed
- Prominent display: flame icon + "Jour 14" on language dashboard

### Book Progress
- Progress bar: "Chapitre 12/27 — Les pronoms relatifs composés"
- Advances when all prompts from a chapter's bank have been recorded (or a threshold like 5 of 15)
- Infinite scroll feel: within a chapter, there are many prompts to work through

---

## Task List (effort-aware)

### Batch 1: Database Migration (effort: low)
New tables for oral sessions, gradings, and prompt bank.

- [ ] Create migration `supabase/migrations/20260414000000_language_oral_practice.sql`:
  - CREATE `language_oral_prompts`:
    - `id uuid PK DEFAULT gen_random_uuid()`
    - `track_id uuid REFERENCES language_tracks(id) NOT NULL`
    - `chapter_ref text NOT NULL` — topic name from the track's topics array
    - `chapter_order int NOT NULL`
    - `prompt_text text NOT NULL` — the monologue prompt (in French)
    - `theme text` — short theme label
    - `grammar_targets text[]` — grammar concepts to exercise
    - `vocab_targets text[]` — vocabulary to incorporate
    - `suggested_duration_seconds int DEFAULT 120`
    - `sort_order int DEFAULT 0`
    - `created_at timestamptz DEFAULT now()`
  - CREATE `language_oral_sessions`:
    - `id uuid PK DEFAULT gen_random_uuid()`
    - `user_id uuid NOT NULL`
    - `prompt_id uuid REFERENCES language_oral_prompts(id) NOT NULL`
    - `track_id uuid REFERENCES language_tracks(id) NOT NULL`
    - `chapter_ref text NOT NULL`
    - `audio_gcs_path text`
    - `audio_duration_seconds int`
    - `status text DEFAULT 'prompted' CHECK (status IN ('prompted', 'recorded', 'grading', 'graded', 'failed'))`
    - `created_at timestamptz DEFAULT now()`
    - `graded_at timestamptz`
  - CREATE `language_oral_gradings`:
    - `id uuid PK DEFAULT gen_random_uuid()`
    - `session_id uuid REFERENCES language_oral_sessions(id) NOT NULL UNIQUE`
    - `transcript text`
    - `transcription_flags jsonb` — low-confidence words (non-graded, future use)
    - `scores jsonb NOT NULL` — `{grammar: {score, evidence[], summary}, lexical: {...}, discourse: {...}, task: {...}}`
    - `overall_score numeric`
    - `verdict text` — strong/developing/needs_work
    - `feedback text` — in French
    - `strongest_moment text`
    - `weakest_moment text`
    - `created_at timestamptz DEFAULT now()`
  - ALTER `user_language_settings`: add `current_streak int DEFAULT 0`, `longest_streak int DEFAULT 0`, `last_practice_date date`, `current_chapter_order int DEFAULT 1`
  - RLS policies: authenticated users see own rows, anon/service role full access
  - Indexes: `language_oral_sessions(user_id, status)`, `language_oral_sessions(prompt_id)`, `language_oral_prompts(track_id, chapter_order)`
- [ ] Validate: `pnpm db:push` succeeds, `\d language_oral_sessions` shows all columns

### Batch 2: Pydantic Schemas (effort: low)
Models for prompts, sessions, gradings, and streak.

- [ ] Create `api/app/models/language_oral_schemas.py`:
  - `OralPrompt(BaseModel)`: id, track_id, chapter_ref, chapter_order, prompt_text, theme, grammar_targets, vocab_targets, suggested_duration_seconds, sort_order
  - `OralDimensionEvidence(BaseModel)`: quote, analysis
  - `OralDimensionScore(BaseModel)`: name, score (1-10), evidence list, summary
  - `OralGrading(BaseModel)`: transcript, scores (dict of OralDimensionScore), overall_score, verdict, feedback, strongest_moment, weakest_moment
  - `OralSession(BaseModel)`: id, user_id, prompt_id, track_id, chapter_ref, prompt (nested OralPrompt), grading (optional nested OralGrading), audio_duration_seconds, status, created_at, graded_at
  - `OralSessionCreate(BaseModel)`: prompt_id
  - `OralDashboard(BaseModel)`: current_chapter (name + order), book_progress (chapters_done / total), current_streak, longest_streak, todays_prompts (list of OralPrompt), pending_sessions (list of OralSession with status != graded), recent_gradings (list of OralSession with grading)
  - `StreakInfo(BaseModel)`: current_streak, longest_streak, last_practice_date
- [ ] Validate: `cd api && python -c "from app.models.language_oral_schemas import OralSession, OralGrading, OralDashboard; print('OK')"`

### Batch 3: Prompt Bank Generation Script (effort: medium)
Script to pre-generate oral prompts from book_content for each chapter.

- [ ] Create `api/scripts/generate_oral_prompts.py`:
  - Takes: `--track-id` (required)
  - For each chapter (topic) in the track:
    - Fetch `book_content` for that chapter (summary, key_concepts, sections)
    - Call Gemini to generate 10-15 monologue prompts, each with: prompt_text (in French), theme, grammar_targets, vocab_targets, suggested_duration
    - Prompt to Gemini: "Generate oral monologue prompts for a B2→C1 French learner. Chapter theme: X. Grammar targets: Y. The student will speak for 1-3 minutes. Prompts should require argumentation, description, explanation, or narrative. All in French. Vary the register and topic angle."
    - Insert into `language_oral_prompts` with sort_order
  - Upsert pattern (don't duplicate on re-run)
  - Print summary: "Generated X prompts across Y chapters"
- [ ] Run against Grammaire Progressive track: `cd api && python scripts/generate_oral_prompts.py --track-id 5eba8cda-1cbf-4d07-b770-1204a7b54a75`
- [ ] Validate: `SELECT chapter_ref, count(*) FROM language_oral_prompts GROUP BY chapter_ref ORDER BY chapter_order` shows 10+ prompts per chapter

### Batch 4: Transcription & Grading Service (effort: high)
French STT + 4-dimension async grading.

- [ ] Create `api/app/services/language_oral_service.py`:
  - `LanguageOralService` class (singleton pattern via `get_language_oral_service()`)
  - `async transcribe_french(audio_bytes, mime_type) -> str`:
    - Cloud STT (Chirp 2) with `language_codes=["fr-FR"]` — same pipeline as `OnsitePrepService._transcribe_audio()` but French
    - Gemini fallback with French prompt
  - `async grade_monologue(transcript, prompt, grammar_targets, vocab_targets, chapter_context) -> OralGrading`:
    - Build rubric prompt with 4 dimensions + behavioral anchors + CITE EVIDENCE rules
    - Call Gemini, parse JSON (with escape-fixing)
    - Compute `overall_score` via weighted average in code
    - Compute verdict in code
    - Return `OralGrading`
  - `async transcribe_and_grade(session_id, audio_bytes, mime_type)`:
    - Full pipeline: transcribe → grade → update session + grading in DB → update status to "graded"
    - On failure: update session status to "failed"
    - Archive audio to GCS (best-effort)
  - `update_streak(user_id)`:
    - Check `last_practice_date`, increment/reset streak accordingly
  - `DIMENSION_WEIGHTS = {"grammar": 2.0, "lexical": 1.5, "discourse": 1.5, "task": 1.0}`
- [ ] Validate: Unit test mocking Cloud STT + Gemini, verify French config, weighted score computation, verdict thresholds

### Batch 5: API Router (effort: medium)
Endpoints for oral practice flow.

- [ ] Create `api/app/routers/language_oral.py`:
  - `GET /language/oral/{user_id}/dashboard` — returns OralDashboard:
    - Current chapter from `user_language_settings.current_chapter_order`
    - Book progress (current_chapter_order / total_topics)
    - Streak info
    - Today's available prompts (unrecorded prompts from current chapter, limit 3)
    - Pending sessions (status = 'grading')
    - Recent graded sessions (last 10)
  - `POST /language/oral/{user_id}/sessions` — create session from prompt_id:
    - Validates prompt exists and matches user's active track
    - Creates `language_oral_sessions` row with status='prompted'
    - Returns OralSession
  - `POST /language/oral/sessions/{session_id}/upload-audio` — FormData upload:
    - Validates session exists, status is 'prompted'
    - Reads audio bytes + mime_type, validates size < 25MB
    - Updates session status to 'recorded', then 'grading'
    - **Fires off `transcribe_and_grade()` as background task** (asyncio.create_task or BackgroundTasks)
    - Updates streak
    - Returns `{ session_id, status: "grading" }` immediately
  - `GET /language/oral/sessions/{session_id}` — get session with grading if available
  - `GET /language/oral/{user_id}/sessions` — list sessions (paginated, most recent first)
  - `GET /language/oral/{user_id}/streak` — returns StreakInfo
  - Chapter advancement logic:
    - After audio upload, check if user has recorded >= 5 prompts from current chapter
    - If yes: increment `current_chapter_order` on user_language_settings
- [ ] Register router in `main.py`
- [ ] Validate: `curl` the dashboard endpoint, create a session, upload audio, verify status transitions and async grading fires

### Batch 6: Frontend — Oral Dashboard & Recorder (effort: high)
New oral practice page with recording, progress bar, streak display.

- [ ] Create `clients/web/src/app/(app)/language/oral/page.tsx`:
  - Fetches `GET /language/oral/{user_id}/dashboard` on load
  - Layout:
    - **Top bar**: Streak flame + "Jour 14" | Book progress bar "Chapitre 12/27 — Les pronoms relatifs" (44%)
    - **Prompt cards**: Today's 2-3 monologue prompts from current chapter
    - **Pending sessions**: Cards showing "En cours d'évaluation..." with spinner
    - **Recent results**: Graded sessions with scores (expandable)
  - Polls for grading results every 15s when there are pending sessions
- [ ] Create `clients/web/src/components/language/oral/OralPromptCard.tsx`:
  - Shows prompt text, theme tag, grammar/vocab targets as pills
  - Suggested duration indicator
  - "Enregistrer" button → expands to recorder
  - States: ready → recording → preview → uploading → submitted ("En cours d'évaluation...")
- [ ] Copy + adapt `AudioRecorder` from `components/system-design/AudioRecorder.tsx` to `components/language/oral/LanguageRecorder.tsx`:
  - French copy: "Enregistrement en cours...", "Bon rythme", "Pensez à conclure..."
  - Default suggested duration from prompt (60-180s)
  - Same codec: WebM/Opus, 1s chunks
  - On submit: call upload-audio endpoint, show "submitted" state
- [ ] Create `clients/web/src/components/language/oral/OralGradingCard.tsx`:
  - Shows: overall score + verdict badge
  - 4 dimension bars (name, score 1-10, colored bar)
  - Expandable: evidence quotes + analysis per dimension
  - Strongest/weakest moments
  - Feedback text (in French)
  - Collapsible transcript section
- [ ] Create `clients/web/src/components/language/oral/StreakBadge.tsx`:
  - Flame icon + streak count
  - Subtle animation on increment
- [ ] Add to `api.ts`:
  - `getOralDashboard(userId)` → OralDashboard
  - `createOralSession(userId, promptId)` → OralSession
  - `uploadOralAudio(sessionId, audioFile)` → `{ session_id, status }` (FormData, 30s timeout — it's async so just upload time)
  - `getOralSession(sessionId)` → OralSession
  - `getOralSessions(userId, limit)` → OralSession[]
  - Frontend types: OralPrompt, OralSession, OralGrading, OralDimensionScore, OralDimensionEvidence, OralDashboard, StreakInfo
- [ ] Add `/language/oral` to sidebar navigation
- [ ] Validate: Open `/language/oral`, see prompts + streak + progress bar, record a monologue, submit, see "grading..." state, refresh, see grading result with dimensions

### Batch 7: Polish & Edge Cases (effort: low)
Error handling, progress edge cases, cleanup.

- [ ] Handle microphone permission denied (French message, no fallback to text — this is an oral tool)
- [ ] Handle STT failure: update session status to 'failed', show "Échec de la transcription. Veuillez réessayer." with re-record option
- [ ] Handle grading failure: same pattern, allow re-upload
- [ ] Streak edge cases: timezone (use user's local date from frontend header or default UTC), first practice (streak = 1)
- [ ] Chapter completion: when `current_chapter_order` exceeds total chapters, show "Livre terminé!" state
- [ ] Empty prompt bank: if chapter has no prompts yet, show "Prompts en cours de génération" (shouldn't happen after Batch 3 but defensive)
- [ ] Polling cleanup: stop polling when no pending sessions
- [ ] Validate: `pnpm typecheck && pnpm lint` pass with no new errors

## Verification
After each batch:
1. Run the batch-specific validate step
2. `cd api && python -m pytest tests/ -x -q` (no regressions)
3. `pnpm typecheck` (no new TS errors)

## Completion Promise
Oral practice flow works end-to-end: open `/language/oral`, see streak + chapter progress bar + monologue prompts from current chapter, record voice, get async confirmation, come back to see 4-dimension grading with cited evidence. Prompt bank has 10+ prompts per chapter. Chapter advances after 5 recordings. Streak tracks across days. `pnpm typecheck && pnpm lint` pass.
