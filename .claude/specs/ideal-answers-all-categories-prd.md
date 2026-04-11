# Ideal Answers for All Question Categories — PRD

## Implementation Status: COMPLETE

All 46 questions populated. Approach changed from PRD: depth and design answers were written directly by Claude Code using LP stories, breadth answers, and context hints as source material (no Gemini script needed).

## Overview

Extend the `ideal_answer` system (currently LP-only) to cover all 37 remaining questions across breadth (20), depth (15), and design (2). LP stories are already done. For breadth, we have 20 fully-written answers in `docs/amazon-prep/02-science-breadth/answers.md` that can be ingested directly. For depth and design, answers were written directly using existing reference material.

## Final State

| Category | Questions | Has `ideal_answer` | Source |
|----------|-----------|-------------------|--------|
| LP | 9 | 9/9 DONE | `onsite-stories.md` — hand-validated STAR stories |
| Breadth | 20 | 20/20 DONE | `02-science-breadth/answers.md` — parsed and ingested |
| Depth | 15 | 15/15 DONE | Written by Claude Code from LP stories + context hints |
| Design | 2 | 2/2 DONE | Written by Claude Code from role docs + context hints |

## Task List

### Batch 1: Breadth — ingest from existing answers.md (effort: medium)

- [x] Parse `answers.md` to extract all 20 answers, matching each to its question UUID via prompt text
- [x] Create migration `supabase/migrations/20260402000000_populate_breadth_ideal_answers.sql` with 20 UPDATE statements
- [x] For each answer: `summary` = first-sentence distillation, `outline` = 3-5 key points, `full_response` = full answer text
- [x] Validate: `npx supabase db push` succeeds, `curl /api/onsite-prep/questions?category=breadth` shows all 20 with `ideal_answer`

### Batch 2: Depth — written directly from project experience (effort: high)

- [x] Write 15 depth answers using LP stories, breadth answers, and context hints as source material
- [x] Create migration `supabase/migrations/20260402000001_populate_depth_ideal_answers.sql`
- [x] Validate: `npx supabase db push` succeeds, `curl /api/onsite-prep/questions?category=depth` shows all 15 with `ideal_answer`

### Batch 3: Design — written directly with role context (effort: high)

- [x] Write 2 design answers using role descriptions and system design patterns
- [x] Create migration `supabase/migrations/20260402000002_populate_design_ideal_answers.sql`
- [x] Validate: `npx supabase db push` succeeds, `curl /api/onsite-prep/questions?category=design` shows both with `ideal_answer`

### Batch 4: Verification — end-to-end check (effort: low)

- [x] `curl /api/onsite-prep/questions` — all 46 questions have `ideal_answer` populated
- [x] Practice page renders ideal answer immediately for all categories (no Gemini spinner)

## Files Changed

| File | Change |
|------|--------|
| `supabase/migrations/20260402000000_populate_breadth_ideal_answers.sql` | NEW — 20 breadth answers from answers.md |
| `supabase/migrations/20260402000001_populate_depth_ideal_answers.sql` | NEW — 15 depth answers written from project experience |
| `supabase/migrations/20260402000002_populate_design_ideal_answers.sql` | NEW — 2 design answers written from role context |
