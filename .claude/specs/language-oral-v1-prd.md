# Language Oral Practice v1 — PRD

## Implementation Status: DESIGN

Brainstorm captured from conversation on 2026-04-14. No code yet — this doc locks the design decisions so implementation can proceed in follow-up passes.

## Motivation

Current language module is text-exercise-only. To reach French C1 and Chinese HSK5 (from HSK3), the user needs daily *productive speaking* practice — not pronunciation drilling (which they get from human speakers), but clarity, grammar, lexical range, and discourse under spontaneous monologue.

The design borrows the structured topic-bank pattern from `docs/amazon-prep/` onsite prep, retargets the existing `oral_grading_service` (currently system-design-only) at language, and adds a Telegram front-end so daily homework can be submitted from anywhere.

## Core Loop

```
Curriculum (N-day plan per language, anchored to a textbook)
    ↓ defines
Today's session for each active language:
    ─ prompt generated from { current chapter theme + yesterday's thread notes + grammar/vocab target }
    ─ user records free monologue (voice note in Telegram OR dashboard)
    ─ Gemini multimodal grades (transcript + rubric, async)
    ─ extractor pulls "thread notes" for tomorrow + error library entries
    ↓ feeds
Tomorrow's prompt (chaining) + tomorrow's text drills (error remediation)
Low grade → bonus work added to tomorrow (curriculum stays on schedule)
```

## Locked design decisions

| # | Decision | Notes |
|---|----------|-------|
| D1 | **Prompt style: free monologue**, not structured STAR or Q&A | Chaining across days provides structure |
| D2 | **Chaining** via DB-stored thread notes, NOT Gemini conversation memory | Extractor runs post-grading, stores in Postgres, splices into tomorrow's prompt builder |
| D3 | **Grading rubric: 4 dimensions** — grammar accuracy, lexical range, discourse/coherence, task completion | No pronunciation dimension |
| D4 | **Transcription confidence flags** surfaced as non-graded side panel | Words Gemini struggled on — breadcrumb for human tutors, not a score |
| D5 | **Curriculum = N-day structured plan** anchored to a textbook, auto-advance on completion | Bonus remediation work added for low grades, schedule does not slip |
| D6 | **Both languages active simultaneously** — French + Chinese every day | Two threads, two prompts, two recordings per day |
| D7 | **Rubric anchors** — CEFR C1 targets for French, HSK 5 targets for Chinese | Same schema, language-specific rubric config |
| D8 | **Text ↔ oral integration** — oral errors feed tomorrow's text drill generation | Oral is the productive-weakness diagnostic; text reinforces |
| D9 | **Telegram = convenient input surface**, dashboard = review | Voice note in → short feedback card back + link to full dashboard review |
| D10 | **Grading is async** — no latency budget | Bot sends "got it, grading..." and edits message when result returns |
| D11 | **Gemini only invoked during grading and curriculum authoring** | No always-on context; thread state lives in Postgres |
| D12 | **No spaced repetition** — curriculum-driven progression | Errors surface via bonus work + error library, not SRS intervals |

## Data model sketch

```
language_curricula
  id, user_id, language (fr|zh), textbook_ref, total_days, created_at

language_curriculum_days
  id, curriculum_id, day_number, chapter_ref,
  theme, grammar_targets[], vocab_targets[],
  status (pending|in_progress|completed)

language_oral_threads
  id, curriculum_id, chapter_ref,
  rolling_summary TEXT,     -- updated each session, not raw transcripts
  open_threads JSONB,       -- [{claim, dropped_idea, avoided_structure}]
  created_at, closed_at

language_oral_sessions
  id, thread_id, curriculum_day_id, user_id, language,
  prompt TEXT, prompt_targets JSONB,
  audio_gcs_uri, audio_duration_sec,
  status (prompted|recorded|grading|graded|skipped),
  created_at, graded_at

language_oral_gradings
  id, session_id,
  transcript TEXT,
  transcription_flags JSONB,   -- low-confidence words
  scores JSONB,                -- {grammar, lexical, discourse, task}
  errors JSONB,                -- [{type, quote, correction, explanation}]
  overall_score NUMERIC, verdict TEXT, feedback TEXT

language_error_library
  id, user_id, language, chapter_ref,
  error_type, pattern, first_seen_session_id,
  occurrence_count, last_seen_at,
  remediation_status (open|drilled|resolved)

language_telegram_bindings
  user_id, telegram_chat_id, bound_at, active_language
```

## API surface

- `POST /api/language/curriculum` — author N-day curriculum for a language (Gemini-assisted, given textbook + level target)
- `GET  /api/language/today` — returns today's prompts (one per active language) with yesterday's context
- `POST /api/language/oral/upload` — accept audio (multipart or GCS pre-signed), creates session, enqueues grading
- `GET  /api/language/oral/session/{id}` — full grading result + transcript
- `GET  /api/language/thread/{id}` — thread view across days
- `GET  /api/language/errors` — error library (filter by language, chapter, status)
- `POST /api/telegram/webhook` — bot webhook (voice note, commands)
- `POST /api/telegram/bind` — one-time chat_id ↔ user_id binding via deep link

## Telegram bot surface (minimal)

| Command | Behavior |
|---------|----------|
| `/today` | Fetches both language prompts for today (French + Chinese) |
| *(voice note)* | Auto-routes to currently active language, uploads, triggers grading, replies with "got it, grading..." then edits with feedback card |
| `/switch fr` `/switch zh` | Sets active language for next voice note |
| `/skip` | Skips today's session for active language |
| `/status` | Curriculum progress (day N of X) for both languages |
| `/bind <token>` | One-time binding from dashboard deep link |

## Prompt-builder logic (per day, per language)

1. Load `curriculum_day` for today → chapter ref, grammar/vocab targets
2. Load open `language_oral_thread` for chapter → rolling summary + open threads
3. Load recent errors from `language_error_library` for this chapter
4. Ask Gemini (during prompt authoring OR cached day-zero) to produce a monologue prompt that:
   - Hooks on one open thread from yesterday ("you argued X — defend it in a formal register")
   - Forces at least one grammar target the user has been avoiding
   - Invites chapter vocabulary naturally

If grade on day D < threshold → append *bonus drill* (text tier) to day D+1 targeting the error types surfaced.

## Rubric config (language-specific)

```python
RUBRICS = {
  "fr": {
    "target_level": "C1",
    "dimensions": {
      "grammar":   {"weight": 2.0, "anchors": "..."},  # subjunctive, concordance, register
      "lexical":   {"weight": 1.5, "anchors": "..."},  # idiomatic, abstract, nuance
      "discourse": {"weight": 1.5, "anchors": "..."},  # cohesion markers, argumentation
      "task":      {"weight": 1.0, "anchors": "..."},
    },
  },
  "zh": {
    "target_level": "HSK5",
    "dimensions": {
      "grammar":   {"weight": 2.0, "anchors": "..."},  # 把/被, 了 placement, measure words
      "lexical":   {"weight": 1.5, "anchors": "..."},  # HSK5 vocab, light chengyu
      "discourse": {"weight": 1.5, "anchors": "..."},  # topic-comment, 连接词
      "task":      {"weight": 1.0, "anchors": "..."},
    },
  },
}
```

## Open questions for v1 → v1.1

- **Curriculum authoring UX.** Does the user upload a textbook PDF and Gemini generates the N-day plan? Or hand-edit a YAML spec and ingest it? Leaning toward Gemini-drafted, user-editable.
- **Chapter boundary ritual.** When a chapter thread closes, do we prompt a capstone summary monologue before advancing? Nice for reinforcement but optional.
- **Review of past sessions.** Dashboard shows thread timeline — do we let the user re-record an old day? Probably not for v1 (keeps curriculum deterministic).
- **Vocab proof-of-use.** Should lexical scoring explicitly check which chapter-target words made it into the transcript? Probably yes — cheap signal.

## Implementation phases

### Phase 1 — Oral recording loop (dashboard only, French only)
- Migration: `language_oral_threads`, `language_oral_sessions`, `language_oral_gradings`
- Extend `oral_grading_service` with language rubric dispatch
- Dashboard: record → upload → async grade → review UI
- No curriculum yet — prompts are hand-picked from a seed bank

### Phase 2 — Curriculum + chaining
- Migration: `language_curricula`, `language_curriculum_days`, `language_error_library`
- Curriculum authoring flow (Gemini-drafted)
- Thread note extractor post-grading
- Prompt builder that reads thread + curriculum + errors
- Add Chinese track alongside French

### Phase 3 — Telegram bot
- Bot scaffold in `clients/telegram/` (python or node — match rest of stack)
- Webhook endpoint + voice note handler
- Binding flow from dashboard
- Commands: `/today`, `/switch`, `/skip`, `/status`

### Phase 4 — Text ↔ oral loop
- Error library → text drill generator signal
- Bonus work assignment on low grades
- Chapter progression auto-advance + bonus remediation

## Files expected to change / create

| Area | Files |
|------|-------|
| Schema | `supabase/migrations/2026042*_language_oral_*.sql` |
| API | `api/app/routers/language_oral.py`, extend `language.py` |
| Services | Extend `api/app/services/oral_grading_service.py`, new `language_curriculum_service.py`, `thread_extractor_service.py` |
| Models | `api/app/models/language_oral_schemas.py` |
| Web | `clients/web/src/app/(app)/language/oral/`, new components under `clients/web/src/components/language/oral/` |
| Telegram | `clients/telegram/` (scaffold from stub) |
| API for bot | `api/app/routers/telegram.py` |

## Non-goals (v1)

- Pronunciation scoring (explicit design choice — human speakers handle this)
- Spaced repetition intervals (curriculum-driven instead)
- Real-time conversation with the bot (voice note in / feedback out is enough)
- Live Gemini chat during recording
- Multi-user support beyond the single owner
