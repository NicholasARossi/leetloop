# Language Learning Experience — Implementation PRD

## Reference Mockup
`clients/web/public/language-full-experience.html` — open in a browser to see the target experience. This is the source of truth for layout, visual hierarchy, and interaction patterns.

## Context

The language learning feature already has a working backend (FastAPI at `api/app/routers/language.py`) and partial frontend (`clients/web/src/app/(app)/language/page.tsx` + components in `clients/web/src/components/language/`). The existing design system is in `clients/web/src/app/globals.css` (chamfered cards, IBM Plex Mono, coral accent `#FF8888`).

**What exists:**
- Daily exercise cards with inline answer → grade flow (`DailyExerciseCard`)
- Track selection and switching
- Book progress page (`/language/book-progress`)
- Exercise submission and Gemini grading
- Spaced repetition review queue (backend)
- API calls in `clients/web/src/lib/api.ts`

**What this PRD adds:**
- Unified dashboard that merges reviews + new exercises + adaptive practice into one flow
- Book library view with grid of available books
- Book switcher dropdown in sidebar
- Simplified 3-item navigation (Tableau de bord, Progression, Bibliothèque)
- Full French immersion for all UI labels
- Monochrome accent color palette (no red/green — pass = coral accent, fail = muted gray)
- Exercise grouping by purpose (révisions ciblées → chapitre en cours → pratique adaptée → expression libre)

## Architecture Decisions

- **Framework**: Next.js 14, React 18, Tailwind CSS (existing stack)
- **Routing**: Keep existing `/language` page, add `/language/library` route
- **State**: React state + API calls (no new state management)
- **API**: Use existing endpoints — no new backend work needed
- **Design system**: Use existing `globals.css` component classes (`.card`, `.tag`, `.badge`, `.progress-bar`, `.list-item`, `.btn-primary`, etc.)

## Implementation Phases

### Phase 1: Restructure the Language Page Layout

**File:** `clients/web/src/app/(app)/language/page.tsx`

Replace the current layout with a sidebar + main content area:

**Sidebar (fixed left, 260px):**
1. Book selector dropdown showing active book name, language, level
   - Clicking opens a small overlay listing all tracks from `getLanguageTracks()`
   - Selecting a track calls `setActiveLanguageTrack()` and reloads
2. Navigation links (3 items only):
   - "Tableau de bord" → dashboard view (default)
   - "Progression" → book progress view
   - "Bibliothèque" → library view
3. Bottom stats bar: streak days, average score, completion %
   - Data from the dashboard summary endpoint

**Main content area:** renders one of 3 views based on nav state.

### Phase 2: Unified Dashboard View

**File:** `clients/web/src/components/language/ExerciseDashboard.tsx` (refactor)

The dashboard is the primary experience. It shows today's complete exercise session as a single scrollable list, grouped by purpose:

**Session header card:**
- "Session du jour" heading
- Progress bar: X / Y exercices
- Breakdown: "N nouveaux · N révisions ciblées · N pratique adaptée"
- Average score

**Exercise sections (in order):**

1. **"Révisions ciblées"** — Review exercises come first
   - These are exercises where `is_review === true` from the daily batch
   - Visual: left accent border + "Révision" badge + chapter reference
   - Show which chapter they review (e.g., "Ch. 4", "Ch. 6")

2. **"Chapitre en cours"** — Current chapter exercises
   - Regular exercises from the daily batch where `is_review === false`
   - Grouped under the current chapter name

3. **"Pratique adaptée"** — Adaptive targeted exercises
   - Exercises that target weak areas identified from failed reviews
   - Visual: left muted accent border + "Adapté" badge
   - These are exercises from the daily batch that have `review_topic_reason` set but `is_review === false`

4. **"Expression libre"** — Free-form exercise
   - The `free_form` tier exercise from the batch
   - Always last

**Exercise card states (reuse/refactor `DailyExerciseCard`):**
- **Pending**: muted, shows type tag + question preview + word target
- **Active**: expanded with full question, key concepts, answer textarea, submit button
- **Completed pass**: collapsed single line, accent border, score
- **Completed fail**: collapsed single line, gray/muted, score + "À revoir" badge

**Regenerate button** at the bottom.

### Phase 3: Book Library View

**New file:** `clients/web/src/components/language/BookLibrary.tsx`

A 2-column grid of book cards. Each card shows:
- Colored cover placeholder (gradient background with book initials)
- Book title and subtitle
- Language, CEFR level, chapter count badges
- Publisher
- Progress bar + "X/Y chapitres · Z%" if started
- "Continuer" button if started, "Commencer" if not
- "Actif" badge on the currently active book

Data source: `getLanguageTracks()` returns all tracks. Cross-reference with progress data.

Clicking a book card sets it as active and navigates to the dashboard.

### Phase 4: Book Progress View Refinement

**File:** `clients/web/src/components/language/BookProgressView.tsx` (refactor)

Keep the existing chapter-by-chapter view but update:
- Stats bar: chapitres completed, % complete, score moyen, exercises cette semaine
- Use the `panel-schematic` style for the stats grid
- Chapter rows use accent color for "current", accent-dark for "review due"
- Expandable chapter details: key concepts as chips (got/missed), last practiced date
- Pending chapters shown muted

### Phase 5: Color Palette & French Immersion

**Across all language components:**

Colors — remove all red/green semantic coloring:
- Pass/complete: use `--accent-color` border, `--accent-color-20` bg, `--accent-color-dark` text
- Fail/needs review: use gray (`#b0b0b0` border, `#f5f5f5` bg, `#737373` text)
- Active: accent color

French labels — all user-facing text in the language section must be in French:
- "Réussi" not "Passed", "À revoir" not "Failed"
- "Soumettre" not "Submit", "Passer" not "Skip"
- "Exercices du jour", "Révisions ciblées", "Chapitre en cours"
- "Progression", "Bibliothèque", "Score moyen"
- Navigation, buttons, badges, labels — everything

### Phase 6: Visual Polish

- Topbar: The megaview tab bar should use white bg with subtle border (not dark/black) — update the layout component if the language section shares a top bar
- Sidebar stats: white cells with light gray dividers (no black grid)
- Sidebar border: `border-right: 2px solid #e0e0e0` not black
- Nav active state: accent color left border
- Smooth view transitions (CSS fade-in animation)

## Files to Modify

| File | Change |
|------|--------|
| `clients/web/src/app/(app)/language/page.tsx` | Restructure with sidebar layout, view switching, book selector |
| `clients/web/src/components/language/ExerciseDashboard.tsx` | Refactor to unified dashboard with exercise grouping |
| `clients/web/src/components/language/DailyExerciseCard.tsx` | Update states, colors, French labels |
| `clients/web/src/components/language/BookProgressView.tsx` | Refine visual style, accent-only colors |
| `clients/web/src/components/language/ChapterSection.tsx` | Update colors and expand/collapse behavior |
| `clients/web/src/components/language/index.ts` | Export new components |
| `clients/web/src/lib/api.ts` | Verify all needed endpoints are wired (likely already complete) |

**New files:**
| File | Purpose |
|------|---------|
| `clients/web/src/components/language/BookLibrary.tsx` | Library grid view |
| `clients/web/src/components/language/BookSelector.tsx` | Sidebar dropdown for switching active book |
| `clients/web/src/components/language/LanguageSidebar.tsx` | Sidebar component with nav + stats + book selector |

## Success Criteria & Verification

Every criterion below must pass. Run ALL verification commands and fix any failures before declaring completion.

### V1: Build & Type Safety

```bash
# TypeScript compilation — zero errors
pnpm typecheck

# Production build — must succeed with no errors
pnpm build:web
```

### V2: File Structure

All new files must exist and all new components must be exported from the barrel file.

```bash
# New component files exist
test -f clients/web/src/components/language/BookLibrary.tsx && echo "PASS: BookLibrary.tsx exists" || echo "FAIL: BookLibrary.tsx missing"
test -f clients/web/src/components/language/BookSelector.tsx && echo "PASS: BookSelector.tsx exists" || echo "FAIL: BookSelector.tsx missing"
test -f clients/web/src/components/language/LanguageSidebar.tsx && echo "PASS: LanguageSidebar.tsx exists" || echo "FAIL: LanguageSidebar.tsx missing"

# All new components exported from barrel
grep -q "BookLibrary" clients/web/src/components/language/index.ts && echo "PASS: BookLibrary exported" || echo "FAIL: BookLibrary not exported"
grep -q "BookSelector" clients/web/src/components/language/index.ts && echo "PASS: BookSelector exported" || echo "FAIL: BookSelector not exported"
grep -q "LanguageSidebar" clients/web/src/components/language/index.ts && echo "PASS: LanguageSidebar exported" || echo "FAIL: LanguageSidebar not exported"
```

### V3: Layout Structure

The language page must have a sidebar + main content layout with exactly 3 navigation items.

```bash
# Sidebar component renders 3 nav items (French labels)
grep -c "Tableau de bord\|Progression\|Bibliothèque" clients/web/src/components/language/LanguageSidebar.tsx | xargs -I{} bash -c '[ {} -ge 3 ] && echo "PASS: 3 French nav items found" || echo "FAIL: Missing French nav items (found {})"'

# Sidebar is used in the language page
grep -q "LanguageSidebar\|Sidebar" clients/web/src/app/\(app\)/language/page.tsx && echo "PASS: Sidebar used in page" || echo "FAIL: Sidebar not found in language page"

# Three views exist (dashboard, progress, library)
grep -q "BookLibrary\|Library" clients/web/src/app/\(app\)/language/page.tsx && echo "PASS: Library view wired" || echo "FAIL: Library view not wired in page"
grep -q "BookProgressView\|ProgressView" clients/web/src/app/\(app\)/language/page.tsx && echo "PASS: Progress view wired" || echo "FAIL: Progress view not wired in page"
grep -q "ExerciseDashboard\|Dashboard" clients/web/src/app/\(app\)/language/page.tsx && echo "PASS: Dashboard view wired" || echo "FAIL: Dashboard view not wired in page"
```

### V4: Dashboard Exercise Grouping

The dashboard must group exercises into 4 labeled sections. Verify the grouping logic exists.

```bash
# All 4 section headings present in dashboard component
grep -q "Révisions ciblées" clients/web/src/components/language/ExerciseDashboard.tsx && echo "PASS: Révisions ciblées section" || echo "FAIL: Missing Révisions ciblées"
grep -q "Chapitre en cours" clients/web/src/components/language/ExerciseDashboard.tsx && echo "PASS: Chapitre en cours section" || echo "FAIL: Missing Chapitre en cours"
grep -q "Pratique adaptée" clients/web/src/components/language/ExerciseDashboard.tsx && echo "PASS: Pratique adaptée section" || echo "FAIL: Missing Pratique adaptée"
grep -q "Expression libre" clients/web/src/components/language/ExerciseDashboard.tsx && echo "PASS: Expression libre section" || echo "FAIL: Missing Expression libre"

# Grouping logic uses is_review and review_topic_reason fields
grep -q "is_review" clients/web/src/components/language/ExerciseDashboard.tsx && echo "PASS: is_review used for grouping" || echo "FAIL: is_review not used in dashboard"
grep -q "review_topic_reason" clients/web/src/components/language/ExerciseDashboard.tsx && echo "PASS: review_topic_reason used" || echo "FAIL: review_topic_reason not used in dashboard"
grep -q "free_form" clients/web/src/components/language/ExerciseDashboard.tsx && echo "PASS: free_form tier detected" || echo "FAIL: free_form not handled in dashboard"

# Session header with progress bar exists
grep -q "Session du jour" clients/web/src/components/language/ExerciseDashboard.tsx && echo "PASS: Session header present" || echo "FAIL: Missing Session du jour header"
```

### V5: Exercise Card States

DailyExerciseCard must implement 4 visual states with correct color semantics.

```bash
# Card states exist (pending, answering/active, submitting, graded)
grep -c "pending\|answering\|submitting\|graded" clients/web/src/components/language/DailyExerciseCard.tsx | xargs -I{} bash -c '[ {} -ge 4 ] && echo "PASS: Card states present" || echo "FAIL: Missing card states (found {})"'

# Pass state uses accent color family (not green)
grep -q "accent-color\|accent\|FF8888\|ff8888\|993333" clients/web/src/components/language/DailyExerciseCard.tsx && echo "PASS: Accent color used in card" || echo "FAIL: Accent color not found in card"

# Fail state uses muted gray
grep -q "À revoir" clients/web/src/components/language/DailyExerciseCard.tsx && echo "PASS: À revoir badge present" || echo "FAIL: Missing À revoir badge"

# Review badge present
grep -q "Révision" clients/web/src/components/language/DailyExerciseCard.tsx && echo "PASS: Révision badge" || echo "FAIL: Missing Révision badge"
```

### V6: Book Library

BookLibrary must render a 2-column grid with book cards containing required metadata.

```bash
# Grid layout (2-column)
grep -q "grid-cols-2\|grid.*col.*2\|repeat(2" clients/web/src/components/language/BookLibrary.tsx && echo "PASS: 2-column grid" || echo "FAIL: No 2-column grid in BookLibrary"

# Book card data: title, language, level, chapters, progress
grep -q "chapitres\|chapitre" clients/web/src/components/language/BookLibrary.tsx && echo "PASS: Chapter count in French" || echo "FAIL: Chapter count not in French"

# Action buttons in French
grep -q "Continuer\|Commencer" clients/web/src/components/language/BookLibrary.tsx && echo "PASS: French action buttons" || echo "FAIL: Missing French action buttons (Continuer/Commencer)"

# Active badge
grep -q "Actif" clients/web/src/components/language/BookLibrary.tsx && echo "PASS: Actif badge" || echo "FAIL: Missing Actif badge"

# Uses getLanguageTracks API
grep -q "getLanguageTracks\|LanguageTrackSummary" clients/web/src/components/language/BookLibrary.tsx && echo "PASS: Uses track API" || echo "FAIL: Not using getLanguageTracks"
```

### V7: Book Selector

BookSelector dropdown in sidebar must allow switching between books.

```bash
# BookSelector calls setActiveLanguageTrack
grep -q "setActiveLanguageTrack" clients/web/src/components/language/BookSelector.tsx && echo "PASS: setActiveLanguageTrack called" || echo "FAIL: setActiveLanguageTrack not in BookSelector"

# Shows active book info (name, language, level)
grep -q "language\|level\|langue\|niveau" clients/web/src/components/language/BookSelector.tsx && echo "PASS: Book metadata displayed" || echo "FAIL: Book metadata missing in BookSelector"
```

### V8: Book Progress View

Progress view must display stats and chapter states with correct colors.

```bash
# Stats bar with French labels
grep -q "chapitres\|score moyen\|Score moyen" clients/web/src/components/language/BookProgressView.tsx && echo "PASS: French stats labels" || echo "FAIL: Missing French stats labels in progress view"

# Uses panel-schematic style
grep -q "panel-schematic" clients/web/src/components/language/BookProgressView.tsx && echo "PASS: panel-schematic style used" || echo "FAIL: panel-schematic not used in progress view"

# Chapter states use accent color for current (not green)
grep -q "is_current\|is_completed\|has_review_due" clients/web/src/components/language/BookProgressView.tsx && echo "PASS: Chapter state fields used" || echo "FAIL: Chapter state fields missing"
```

### V9: Color Palette — No Red/Green

Zero red/green semantic colors anywhere in language components. Only coral accent `#FF8888` family + gray.

```bash
# No green hex colors
GREEN_COUNT=$(grep -rn "#22c55e\|#16a34a\|#15803d\|#166534\|#14532d\|#4ade80\|#86efac\|#bbf7d0\|#dcfce7\|#f0fdf4\|#27ae60\|#2ecc71\|#155724\|#d4edda\|#c3e6cb\|#1a5c1a\|#7dcea0\|#4a9d6e\|green-[0-9]" clients/web/src/components/language/ --include="*.tsx" -c 2>/dev/null | awk -F: '{sum+=$2} END {print sum+0}')
[ "$GREEN_COUNT" -eq 0 ] && echo "PASS: No green colors" || echo "FAIL: Found $GREEN_COUNT green color references"

# No red hex colors (except our accent #FF8888 / #993333 / coral)
RED_COUNT=$(grep -rn "#ef4444\|#dc2626\|#b91c1c\|#991b1b\|#7f1d1d\|#f87171\|#fca5a5\|#fecaca\|#fee2e2\|#e74c3c\|#c0392b\|#721c24\|#f8d7da\|red-[0-9]" clients/web/src/components/language/ --include="*.tsx" -c 2>/dev/null | awk -F: '{sum+=$2} END {print sum+0}')
[ "$RED_COUNT" -eq 0 ] && echo "PASS: No red colors (accent coral is fine)" || echo "FAIL: Found $RED_COUNT red color references (not accent)"

# No Tailwind red/green utility classes (text-red-*, bg-green-*, border-green-*, etc.)
RG_TAILWIND=$(grep -rn "text-red-\|bg-red-\|border-red-\|text-green-\|bg-green-\|border-green-" clients/web/src/components/language/ --include="*.tsx" -c 2>/dev/null | awk -F: '{sum+=$2} END {print sum+0}')
[ "$RG_TAILWIND" -eq 0 ] && echo "PASS: No Tailwind red/green classes" || echo "FAIL: Found $RG_TAILWIND Tailwind red/green class references"

# Also check the main language page
RG_PAGE=$(grep -rn "text-red-\|bg-red-\|border-red-\|text-green-\|bg-green-\|border-green-\|#22c55e\|#16a34a\|#ef4444\|#dc2626\|green-600\|red-600" clients/web/src/app/\(app\)/language/page.tsx -c 2>/dev/null || echo 0)
[ "$RG_PAGE" -eq 0 ] && echo "PASS: No red/green in language page" || echo "FAIL: Found $RG_PAGE red/green references in language page"
```

### V10: French Immersion — Zero English UI Strings

All user-facing text in the language section must be in French. Variable names and code comments may remain in English.

```bash
# Must NOT contain these English UI words as user-facing strings (inside quotes or JSX text)
ENGLISH_HITS=$(grep -rn '"Submit"\|"Skip"\|"Retry"\|"Loading"\|"Pass"\|"Fail"\|"Review"\|"Score"\|"Complete"\|>Submit<\|>Skip<\|>Retry<\|>Loading<\|>Review<\|"Dashboard"\|"Library"\|"Progress"\|"chapters"\|"exercises"\|"Average"\|"Streak"\|"Book Progress"\|"Set Active"\|"Choose a Track"\|"Regenerate"\|"completed"\|>Active<\|"Active"\|"Setting\.\.\."\|"Switching\.\.\."' clients/web/src/components/language/ --include="*.tsx" clients/web/src/app/\(app\)/language/page.tsx -l 2>/dev/null)
[ -z "$ENGLISH_HITS" ] && echo "PASS: No English UI strings found" || echo "FAIL: English UI strings found in: $ENGLISH_HITS"

# Must contain these French equivalents somewhere in language components
grep -rq "Soumettre" clients/web/src/components/language/ --include="*.tsx" && echo "PASS: Soumettre present" || echo "FAIL: Missing Soumettre (Submit)"
grep -rq "Passer" clients/web/src/components/language/ --include="*.tsx" && echo "PASS: Passer present" || echo "FAIL: Missing Passer (Skip)"
grep -rq "Réussi\|réussi" clients/web/src/components/language/ --include="*.tsx" && echo "PASS: Réussi present" || echo "FAIL: Missing Réussi (Pass)"
grep -rq "À revoir" clients/web/src/components/language/ --include="*.tsx" && echo "PASS: À revoir present" || echo "FAIL: Missing À revoir (Needs review)"
grep -rq "Score moyen\|score moyen" clients/web/src/components/language/ --include="*.tsx" && echo "PASS: Score moyen present" || echo "FAIL: Missing Score moyen (Average score)"
grep -rq "Régénérer\|régénérer" clients/web/src/components/language/ --include="*.tsx" && echo "PASS: Régénérer present" || echo "FAIL: Missing Régénérer (Regenerate)"
grep -rq "Exercices\|exercices" clients/web/src/components/language/ --include="*.tsx" && echo "PASS: Exercices present" || echo "FAIL: Missing Exercices"
grep -rq "Chargement\|chargement" clients/web/src/components/language/ --include="*.tsx" clients/web/src/app/\(app\)/language/page.tsx && echo "PASS: Chargement present" || echo "FAIL: Missing Chargement (Loading)"
```

### V11: Visual Polish

Sidebar and topbar must follow the mockup's light color scheme — no black/dark backgrounds.

```bash
# Sidebar border should be light (e0e0e0 or gray-200/300), not black
grep -q "e0e0e0\|gray-200\|gray-300" clients/web/src/components/language/LanguageSidebar.tsx && echo "PASS: Light sidebar border" || echo "FAIL: Sidebar may have dark border"

# No black background for sidebar stats (should be white/light)
grep -c "bg-black\|background.*#000\|background.*black" clients/web/src/components/language/LanguageSidebar.tsx | xargs -I{} bash -c '[ {} -eq 0 ] && echo "PASS: No black bg in sidebar" || echo "FAIL: Black background found in sidebar"'

# Nav active state uses accent color
grep -q "accent\|FF8888\|ff8888\|coral" clients/web/src/components/language/LanguageSidebar.tsx && echo "PASS: Accent color in nav" || echo "FAIL: Accent color not found in sidebar nav"
```

### V12: API Integration

All required API endpoints must be called from the correct components.

```bash
# Dashboard uses getDailyExercises and submitDailyExercise
grep -rq "getDailyExercises" clients/web/src/app/\(app\)/language/page.tsx && echo "PASS: getDailyExercises called" || echo "FAIL: getDailyExercises not called"
grep -rq "submitDailyExercise" clients/web/src/app/\(app\)/language/page.tsx clients/web/src/components/language/ --include="*.tsx" && echo "PASS: submitDailyExercise called" || echo "FAIL: submitDailyExercise not called"

# Regenerate wired
grep -rq "regenerateDailyExercises" clients/web/src/app/\(app\)/language/page.tsx clients/web/src/components/language/ --include="*.tsx" && echo "PASS: regenerateDailyExercises called" || echo "FAIL: regenerateDailyExercises not called"

# Book progress uses getBookProgress
grep -rq "getBookProgress" clients/web/src/app/\(app\)/language/page.tsx clients/web/src/components/language/ --include="*.tsx" && echo "PASS: getBookProgress called" || echo "FAIL: getBookProgress not called"

# Library uses getLanguageTracks
grep -rq "getLanguageTracks" clients/web/src/components/language/BookLibrary.tsx clients/web/src/app/\(app\)/language/page.tsx && echo "PASS: getLanguageTracks called" || echo "FAIL: getLanguageTracks not called"

# Book selector uses setActiveLanguageTrack
grep -rq "setActiveLanguageTrack" clients/web/src/components/language/BookSelector.tsx clients/web/src/app/\(app\)/language/page.tsx && echo "PASS: setActiveLanguageTrack called" || echo "FAIL: setActiveLanguageTrack not called"
```

### V13: Design System Consistency

Components must use the existing design system classes from globals.css.

```bash
# Card classes used
grep -rq "card\|card-sm\|card-alt" clients/web/src/components/language/ --include="*.tsx" && echo "PASS: Card classes used" || echo "FAIL: Card classes not used"

# Progress bar classes used
grep -rq "progress-bar\|progress-fill" clients/web/src/components/language/ --include="*.tsx" && echo "PASS: Progress bar classes used" || echo "FAIL: Progress bar classes not used"

# Tag/badge classes used
grep -rq "tag\|badge" clients/web/src/components/language/ --include="*.tsx" && echo "PASS: Tag/badge classes used" || echo "FAIL: Tag/badge classes not used"

# Status light used
grep -rq "status-light" clients/web/src/components/language/ --include="*.tsx" && echo "PASS: Status light classes used" || echo "FAIL: Status light classes not used"
```

### V14: Full Verification Script

Run this single script to execute ALL checks. Every line must say PASS.

```bash
echo "=== V1: Build & Type Safety ==="
pnpm typecheck && echo "PASS: typecheck" || echo "FAIL: typecheck"
pnpm build:web && echo "PASS: build" || echo "FAIL: build"

echo ""
echo "=== V2-V13: Structural & Content Checks ==="
# (Run all the individual check commands from V2-V13 above)

echo ""
echo "=== SUMMARY ==="
echo "If any FAIL appears above, fix it before declaring completion."
echo "Dev complete = ZERO failures across ALL checks."
```

## Completion

When all phases are implemented, all verification commands pass, and the web app builds successfully:

<promise>LANGUAGE EXPERIENCE COMPLETE</promise>
