---
name: Language Written — Open-ended Grammar-Targeted Prompts
description: Replace mixed-tier written drills with oral-style open-ended prompts targeting explicit grammar points. Preserves two-column dashboard aesthetic. Kills single-line drills. Gates the refactor behind a generator eval.
type: prd
---

# Language Written — Open-ended Grammar-Targeted Prompts

## Overview

The written column on `/language` is currently a mix of one-word drills, fill-in-the-blanks, and a single free-form prompt (4 tiers, 8 cards). We are collapsing this into one open-ended tier that mirrors the oral prompts: a scenario + explicit `grammar_targets` chips + `vocab_targets` chips + a textarea. The oral column stays untouched. The **aesthetic of the two-column layout (`grid-cols-[3fr_2fr]`) and the card chip styling is preserved** — written becomes the typed twin of oral.

## Scope & Non-goals

- **In scope**: written generator, written grader, written schema, written card UI, single eval of grammar-target generation quality.
- **Not in scope**: oral side (no changes), review queue math, spaced repetition intervals, book ingestion, `language/reviews` page, `language/book-progress` page.
- **Explicitly killed**: the `quick` tier (single_line, 3 cards), the `short` tier (20-word drills, 2 cards). No "drill mode" toggle — if we want that later, it's a separate PRD.

## Gating decision

**Batch 1 is a gate.** It produces a markdown report comparing generator outputs against the grammar targets requested. If fewer than 80% of generated prompts can plausibly elicit their stated grammar targets, we stop and iterate the prompt before touching schemas or UI. Do not proceed to Batch 2 until the report is reviewed.

## Task List (effort-aware)

### Batch 1: Grammar-targeted generator eval (effort: medium) [GATE]

Goal: prove we can reliably generate prompts that force specific grammar points to appear in a natural response. This is the single riskiest piece of the refactor.

- [x] Add `api/scripts/eval_written_prompt_generation.py` — a standalone script (not wired to the API) that:
  - Loads 10 target `(chapter_title, grammar_targets, vocab_targets, genre, word_target)` tuples hand-picked from the Grammaire Progressive B2 track (cover: subjonctif, passé composé vs imparfait, conditionnel, pronoms relatifs, articles partitifs, gérondif, concordance des temps, accord du participe, discours indirect, voix passive).
  - Calls Gemini with a new `_build_written_prompt_generation_prompt(...)` that takes the tuple and asks for a scenario that *naturally elicits* the grammar targets without listing them verbatim inside the scenario text.
  - For each result, Gemini is called a second time as a "critic" to score 1–10 whether the scenario, if answered well in the target language, would realistically require the listed grammar points. Critic outputs JSON: `{grammar_point: {forced: true|false, rationale: str}}`.
  - Writes `.claude/specs/written-prompt-eval.md` with: the 10 tuples, the generated prompts, the critic verdict per grammar target, and a summary hit-rate.
- [x] Run the script. Aim for ≥80% grammar targets marked `forced: true`.
- [x] If below threshold, iterate the generation prompt (not the critic) until threshold is met. Document what changed.
- [x] **Validate**: `python api/scripts/eval_written_prompt_generation.py` runs to completion and the resulting report shows ≥80% hit rate. Commit the final prompt + report.

### Batch 2: Schema and tier collapse (effort: low)

Goal: make the data model express "open-ended grammar-targeted prompt" cleanly, without a destructive migration.

- [x] In `api/app/services/language_service.py`, replace `EXERCISE_TIERS` with a single tier config:
  ```
  WRITTEN_PROMPT_CONFIG = {
    "count_per_day": 3,  # down from 8
    "word_targets": [100, 150, 200],  # one of each per day; bumps if user requests more
    "genres": ["journal_entry", "opinion_essay", "letter_writing", "story_continuation", "situational", "dialogue"],
    "response_format": "long_text",
  }
  ```
  Remove `single_line` and `short_text` as generatable formats. Keep the enum values in the Pydantic schema for backward-compat with historical rows.
- [x] Add fields to the daily-exercise row shape (reuse existing DB columns — no migration):
  - `exercise_type` → now always one of the `genres` values.
  - `key_concepts` → continues to hold grammar target strings (rename at the API boundary to `grammar_targets`).
  - Add a new derived field `vocab_targets: list[str]` — if the DB lacks a column, stuff it into the existing `key_concepts` with a convention, OR add a nullable `vocab_targets` JSONB column via migration `20260420000000_add_vocab_targets.sql`. Pick migration path (cleaner).
- [x] Update `DailyExercise` Pydantic model (`api/app/models/language_schemas.py`) to expose `grammar_targets` and `vocab_targets` on the response, mapped from the underlying columns.
- [x] Update the TS interface `DailyExercise` in `clients/web/src/lib/api.ts` to match.
- [x] **Validate**: `cd api && pytest tests/test_daily_exercises.py` — existing tests still pass (they should; we're additive at the API layer).

### Batch 3: Generator refactor (effort: medium)

Goal: ship the Batch 1 prompt as the real `generate_batch_exercises` path.

- [x] In `language_service.py`, replace the exercise-type-driven prompt in `_build_batch_prompt` (around line 238) with the Batch 1 prompt, wrapped for the batch case.
- [x] Generator input now consists of: (a) list of topics from review queue + new topics, (b) for each topic, 2–3 grammar targets pulled from the chapter's `book_content.key_concepts`, (c) 4–6 vocab targets from the same chapter.
- [x] Generator output must include `grammar_targets: []` and `vocab_targets: []` per exercise. Validate the response with Pydantic and fall back to `_build_fallback_exercises` on parse failure.
- [x] Hard-cap `count_per_day` at 3. Delete the multi-tier loop that assembles `quick + short + extended + free_form`.
- [x] **Validate**:
  - `cd api && pytest tests/test_daily_exercises.py -k generate` passes.
  - Manually: `POST /language/{user_id}/daily-exercises/regenerate` returns exactly 3 exercises, each with `response_format == "long_text"` or `"free_form"`, each with non-empty `grammar_targets`.

### Batch 4: Grader refactor to 4-dimension rubric (effort: medium)

Goal: grading should match the richness of the prompt. Mirror the oral rubric.

- [x] Add `WrittenGrading` Pydantic model to `language_schemas.py` mirroring `OralGrading`:
  - `scores: dict[str, DimensionScore]` with keys `grammar`, `lexical`, `discourse`, `task`.
  - Each dimension has `score: float`, `evidence: list[{quote, analysis}]`, `summary: str`.
  - Top-level `overall_score`, `verdict` (`strong|developing|needs_work`), `feedback`, `grammar_target_hits: list[{target, used: bool, correct: bool, evidence: str}]`, `vocab_target_hits: list[str]`.
- [x] In `language_service.py`, replace `_build_grading_prompt` with a new prompt that takes `(question_text, grammar_targets, vocab_targets, response_text, focus_area, book_context)` and asks Gemini to output the `WrittenGrading` JSON shape.
- [x] Update the `POST /language/daily-exercises/{id}/submit` endpoint to persist the new grading shape. Keep backward-compat on the legacy fields (`score`, `verdict`, `feedback`, `corrections`, `missed_concepts`) by deriving them from the new shape so existing UI continues to render while Batch 5 is in flight.
- [x] **Validate**:
  - `cd api && pytest tests/test_daily_exercises.py -k grade` passes.
  - Submit a test response via curl against a locally-generated prompt; inspect returned JSON — all 4 dimensions present, each with ≥1 evidence quote, `grammar_target_hits` marks each target.

### Batch 5: Frontend card redesign (effort: medium)

Goal: written cards look like typed twins of oral cards. Same chip palette, same card shell, same expand/collapse behavior. No single-line branch.

- [x] In `DailyExerciseCard.tsx`:
  - Delete the `single_line` code path entirely (the `<input type="text">` branch at lines 319-357). Textarea is now the only input.
  - Default `responseFormat` fallback changes from `'single_line'` to `'long_text'`.
  - Default `TEXTAREA_ROWS` for long_text = 6, free_form = 10.
  - Add two chip rows under the prompt text: `grammar_targets` (accent color, like oral's blue chips) and `vocab_targets` (muted yellow, like oral's vocab chips). Match the exact classes used in `OralPromptCard.tsx` so palettes are visually identical.
  - Word count indicator becomes a thin progress bar under the textarea showing `wordCount / word_target`, fills as user types. Caps at 120% fill.
  - The graded-state expanded view adds a "Grammaire visée" section listing each `grammar_target_hit` with ✓ / ✗, and a "Lexique utilisé" section showing which `vocab_targets` appeared.
- [x] In `ExerciseDashboard.tsx`: no layout changes (the `grid-cols-[3fr_2fr]` stays). Just update the `DailyExercise` interface to add `grammar_targets?: string[]` and `vocab_targets?: string[]`. The "8 écrits · 3 oraux" count line at the bottom of the header card now reads "3 écrits · 3 oraux".
- [ ] Take a before/after screenshot with Playwright — save to `.playwright-mcp/written-redesign-before.png` (already exists: `language-page-current.png` can stand in) and `.playwright-mcp/written-redesign-after.png`. Eyeball that the two columns are symmetric.
- [x] **Validate**:
  - `pnpm --filter @leetloop/web lint && pnpm --filter @leetloop/web typecheck` pass.
  - `pnpm dev:web`; visit `/language`; see 3 written cards, each with grammar + vocab chips, each with a textarea (not a single-line input). Submit one, see the 4-dimension grading in the expanded view.

### Batch 6: Regenerate button + count update (effort: low)

- [x] `Régénérer` button behavior unchanged, but the resulting batch is now 3 cards.
- [x] Remove any stale copy that references "8 exercices" if present. (None found — count is dynamic via `{totalCount}`)
- [x] **Validate**: click Régénérer; new 3 prompts appear; header count reads `0/3`.

## Verification

After each batch:
1. `pnpm --filter @leetloop/web lint && pnpm --filter @leetloop/web typecheck`
2. `cd api && pytest tests/test_daily_exercises.py`
3. No regressions in `clients/web/tests/` Playwright suites related to `/language`.

After all batches:
- Manual: full loop on `/language` — 3 written cards generated, grammar chips visible, submit a French response, 4-dimension grading appears, oral column unchanged.
- `clients/web/tests/daily-exercises.spec.ts` updated expectations for 3 cards and textarea-only inputs still pass.

## Completion Promise

Done when:
1. `.claude/specs/written-prompt-eval.md` shows ≥80% grammar-target hit rate.
2. `/language` renders 3 open-ended written cards with `grammar_targets` + `vocab_targets` chips, textarea input only, in the existing `3fr_2fr` two-column layout.
3. Submitting a response returns a 4-dimension rubric grading, rendered in the expanded card view.
4. `cd api && pytest tests/test_daily_exercises.py` and `pnpm --filter @leetloop/web typecheck` both pass.
5. Oral column is byte-identical to before.

Emit `<promise>COMPLETE</promise>` when all five hold.
