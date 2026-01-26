# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

LeetLoop is a personal learning system that captures LeetCode problem-solving behavior and uses spaced repetition to strengthen weak areas. Philosophy: "Most tools celebrate wins. LeetLoop learns from struggle."

## Commands

```bash
# Development
pnpm dev              # Run all packages in dev mode
pnpm dev:web          # Web dashboard on port 3001
pnpm dev:api          # FastAPI backend on port 8080 (requires: cd api && pip install -r requirements.txt)

# Building
pnpm build            # Build all packages
pnpm build:web        # Build web dashboard
pnpm build:extension  # Build Chrome extension

# Code Quality
pnpm lint             # Lint all packages
pnpm typecheck        # Type check all TypeScript

# Database (Supabase)
pnpm db:push          # Push migrations
pnpm db:reset         # Reset database
pnpm db:diff          # Show pending migrations

# Extension Development
cd clients/extension && pnpm dev     # Watch mode
cd clients/extension && pnpm test    # Playwright tests
```

## Architecture

**Monorepo with pnpm workspaces:**

```
clients/
  extension/    # Chrome Extension (Manifest V3) - captures LeetCode submissions
  web/          # Next.js 14 dashboard - displays progress, skills, reviews
  telegram/     # Telegram bot (planned)
api/            # FastAPI backend - recommendations, AI coaching, stats
packages/
  shared/       # TypeScript types shared across clients
supabase/       # PostgreSQL migrations and RLS policies
```

**Data Flow:**
1. Chrome extension intercepts LeetCode API responses via fetch override
2. Extension syncs submissions to Supabase
3. FastAPI queries Supabase for stats, computes skill scores and recommendations
4. Web dashboard queries FastAPI and displays progress

## Tech Stack

- **Web**: Next.js 14, React 18, Tailwind CSS, Recharts
- **Extension**: Chrome Manifest V3, esbuild bundler, Playwright tests
- **API**: FastAPI, Uvicorn, Google Generative AI (Gemini), Pydantic
- **Database**: Supabase (PostgreSQL) with Row-Level Security
- **Deployment**: Google Cloud Run (API + web), Google Secrets Manager

## Key Patterns

**Chrome Extension** uses dual content script pattern:
- `interceptor.ts` (MAIN world): Overrides `window.fetch` to capture LeetCode API
- `content.ts` (ISOLATED world): Scrapes DOM for problem metadata
- `background.ts`: Service worker for storage and Supabase sync

**API Structure:**
- `routers/` - FastAPI endpoints (health, progress, reviews, recommendations, coaching)
- `services/` - Business logic (gemini_gateway, code_analyzer, recommendation_engine)
- `models/schemas.py` - Pydantic request/response models

**Spaced Repetition Algorithm:**
- Initial review: 1 day after failure
- Success: interval doubles (max 30 days)
- Failure: resets to 1 day

## Environment Variables

Extension and web use `SUPABASE_URL` and `SUPABASE_ANON_KEY`. API additionally needs `GOOGLE_API_KEY` for AI features. See `.env.example`.

## Deployment

**Infrastructure:** All services deployed to Google Cloud Run.

**Secrets Management:** Environment variables are stored in Google Secrets Manager and pulled at deploy time. Never hardcode secrets in Dockerfiles or commit `.env` files.

```bash
# Deploy web dashboard (from monorepo root)
gcloud builds submit --tag gcr.io/$PROJECT_ID/leetloop-web --file clients/web/Dockerfile .
gcloud run deploy leetloop-web \
  --image gcr.io/$PROJECT_ID/leetloop-web \
  --region $REGION \
  --allow-unauthenticated \
  --port 3000 \
  --update-secrets="NEXT_PUBLIC_SUPABASE_URL=supabase-url:latest" \
  --update-secrets="NEXT_PUBLIC_SUPABASE_ANON_KEY=supabase-anon-key:latest" \
  --update-secrets="NEXT_PUBLIC_API_URL=api-url:latest"

# Deploy API (from api/ directory)
gcloud builds submit --tag gcr.io/$PROJECT_ID/leetloop-api .
gcloud run deploy leetloop-api \
  --image gcr.io/$PROJECT_ID/leetloop-api \
  --region $REGION \
  --allow-unauthenticated \
  --port 8080 \
  --update-secrets="SUPABASE_URL=supabase-url:latest" \
  --update-secrets="SUPABASE_KEY=supabase-key:latest" \
  --update-secrets="GOOGLE_API_KEY=google-api-key:latest"
```

**Required Secrets in Google Secrets Manager:**
- `supabase-url` - Supabase project URL
- `supabase-anon-key` - Supabase anonymous key (for web)
- `supabase-key` - Supabase service key (for API)
- `google-api-key` - Gemini API key
- `api-url` - Deployed API Cloud Run URL

## Code Style

- Never add Claude Code attribution to commits, PRs, or code comments (no "Co-Authored-By: Claude" or similar)
- Never commit the CLAUDE.md file
