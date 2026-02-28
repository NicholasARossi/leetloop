# Daily Language Exercise Dashboard - Product Spec

## Vision
Transform the `/language` page from a multi-step exercise flow (select track > pick topic > choose type > answer > grade) into a **daily exercise dashboard** where 5-10 short-answer cards appear directly on the page with inline text inputs. Users complete their daily practice without navigating away. The system adapts to weaknesses and organically reviews via spaced repetition.

## Why This Works (Lessons from LeetCode Dashboard)
The LeetCode mission dashboard succeeds because:
1. **Zero-decision daily start**: Open the page, exercises are already waiting
2. **Approachable batch size**: 5-10 items feels doable, not overwhelming
3. **Inline completion**: Answer right there, no modal/page navigation
4. **Adaptive selection**: LLM picks exercises based on weak areas + track progression + review queue
5. **Progress visibility**: Clear "4/8 done" indicator creates momentum

## Core Experience

### Page Load
1. Call `GET /api/language/{user_id}/daily-exercises`
2. If no exercises exist for today, backend generates a batch of 5-10 via Gemini
3. Display exercises as a vertical stack of compact cards
4. Show progress header: "Today's Exercises: 4/8"

### Exercise Card States
Each card has 4 states:
- **pending**: Shows question text, exercise type tag, focus area. Text input visible but empty. Submit button disabled.
- **answering**: User is typing. Submit button enabled when text is non-empty.
- **submitting**: Input disabled, "Grading..." shown. Spinner on submit button.
- **graded**: Input replaced by score badge + brief feedback. Card visually collapses. Click to expand full feedback/corrections.

### Card Layout (Compact)
```
┌─────────────────────────────────────────────────┐
│ [CONJUGATION]  [Review]       Passé Composé     │
│                                                  │
│ Conjuguez le verbe "aller" au passé composé     │
│ pour "nous":                                     │
│                                                  │
│ ┌─────────────────────────────────────────────┐ │
│ │ nous sommes allés                            │ │
│ └─────────────────────────────────────────────┘ │
│                                     [Submit ▶]  │
└─────────────────────────────────────────────────┘
```

### Graded Card (Collapsed)
```
┌─────────────────────────────────────────────────┐
│ [CONJUGATION]  Passé Composé    8.5/10 [PASS] ▼│
└─────────────────────────────────────────────────┘
```

### Graded Card (Expanded)
```
┌─────────────────────────────────────────────────┐
│ [CONJUGATION]  Passé Composé    8.5/10 [PASS] ▲│
│                                                  │
│ Q: Conjuguez le verbe "aller" au passé composé  │
│    pour "nous":                                  │
│ A: nous sommes allés                             │
│                                                  │
│ Feedback: Très bien ! L'accord du participe...  │
│ Correction: —                                    │
└─────────────────────────────────────────────────┘
```

### All Done State
```
┌─────────────────────────────────────────────────┐
│         Today's exercises complete!              │
│                                                  │
│  8/8 exercises  |  Avg: 7.8/10  |  3 reviews    │
│                                                  │
│  Come back tomorrow for new exercises.           │
│            [Regenerate Exercises]                 │
└─────────────────────────────────────────────────┘
```

## Exercise Generation Algorithm

### Daily Batch Composition (8 exercises default)
The LLM generates exercises in a single batch call:

1. **Review exercises (2-3)**: Pull topics from `language_review_queue` where `next_review <= NOW()`. These are marked with a "Review" badge. Exercise types vary (don't repeat the same type that originally failed).

2. **New content exercises (5-6)**: From the active track, select the next uncompleted topics in order. Mix exercise types across the batch:
   - 2x conjugation or fill_blank (quick, concrete)
   - 1x vocabulary (word usage in context)
   - 1x grammar (sentence correction or completion)
   - 1x sentence_construction (open-ended, creative)

3. **Adaptation rules**:
   - If user scored < 5 on a topic recently, add an extra exercise for that topic
   - Pull book_content context for each topic to ground exercises in textbook material
   - Include user's weak areas (from last 5 graded attempts' missed_concepts)

### Batch Gemini Prompt
Instead of generating exercises one at a time, send a single prompt that generates all 5-10 exercises at once. This reduces API calls and allows the LLM to ensure variety across the batch.

## Data Model

### New Table: `language_daily_exercises`
```sql
CREATE TABLE language_daily_exercises (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL,
  track_id UUID REFERENCES language_tracks(id),
  generated_date DATE NOT NULL DEFAULT CURRENT_DATE,
  sort_order INTEGER NOT NULL DEFAULT 0,
  -- Exercise content
  topic TEXT NOT NULL,
  exercise_type TEXT NOT NULL,
  question_text TEXT NOT NULL,
  expected_answer TEXT,
  focus_area TEXT,
  key_concepts TEXT[] DEFAULT '{}',
  -- User response & grading
  response_text TEXT,
  word_count INTEGER DEFAULT 0,
  score NUMERIC(4,2),
  verdict TEXT,
  feedback TEXT,
  corrections TEXT,
  missed_concepts TEXT[] DEFAULT '{}',
  -- Status
  status TEXT NOT NULL DEFAULT 'pending',
  is_review BOOLEAN DEFAULT FALSE,
  review_topic_reason TEXT,
  -- Timestamps
  created_at TIMESTAMPTZ DEFAULT NOW(),
  completed_at TIMESTAMPTZ,
  UNIQUE(user_id, generated_date, sort_order)
);
```

## API Endpoints

### GET /api/language/{user_id}/daily-exercises
Returns today's exercise batch. Generates if not exists.

Response:
```json
{
  "generated_date": "2026-02-18",
  "exercises": [...],
  "completed_count": 4,
  "total_count": 8,
  "average_score": 7.2
}
```

### POST /api/language/daily-exercises/{exercise_id}/submit
Submit answer and get inline grade.

Request: `{ "response_text": "nous sommes allés" }`
Response: `{ "score": 8.5, "verdict": "pass", "feedback": "...", "corrections": null, "missed_concepts": [] }`

### POST /api/language/{user_id}/daily-exercises/regenerate
Delete pending exercises, keep completed, generate new ones for remaining slots.

## Frontend Components

### ExerciseDashboard (page-level)
- Fetches daily exercises on mount
- Shows progress header with completion count
- Renders DailyExerciseCard for each exercise
- Sections: "Reviews" (is_review=true) then "New Exercises"
- Shows completion summary when all done

### DailyExerciseCard (per-exercise)
- Compact card with inline text input (1-2 lines, not a large textarea)
- Card-level state machine: pending > answering > submitting > graded
- Graded cards collapse to single line, expandable
- Review exercises get a visual "Review" badge
- Score uses existing color scheme: coral >= 7, gray 5-7, black < 5

## Design System (Match Existing)
- Cards: `border-2 border-black` (active) or `border-gray-200` (pending)
- Accent: `var(--accent-color)` / coral for pass scores and review badges
- Tags: `.tag` and `.tag-accent` classes
- Font: Geist Mono for scores, system font for text
- Section headers: `.section-title` (uppercase, bordered)
- Inputs: `border-2 border-black`, `font-mono text-sm`
- Submit button: `.btn .btn-primary`

## Behavior Notes
- Track selection remains accessible via sidebar or a settings dropdown in the header, but is NOT the primary flow
- The `/language/reviews` page continues to exist for manual review management
- Daily exercises integrate with the existing `language_attempts` table for history tracking (create an attempt record when submitting)
- Cache daily exercises for the day - don't regenerate on page refresh
- Regenerate button only replaces pending (unanswered) exercises
