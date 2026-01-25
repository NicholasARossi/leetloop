# LeetLoop

A personal learning system that captures LeetCode problem-solving behavior and uses spaced repetition to strengthen weak areas.

**Philosophy:** Most tools celebrate wins. LeetLoop learns from struggle.

## Features

- **Passive Capture**: Chrome extension intercepts all LeetCode submissions (pass or fail)
- **Rich Metadata**: Captures problem details, timing, attempt count, and full code
- **Cloud Sync**: Optional Supabase backend for persistent storage
- **Spaced Repetition**: Automatically queues failed problems for review
- **Skill Tracking**: ELO-like scoring for each topic/tag
- **AI Coach**: Gemini-powered coaching chat and code analysis
- **Web Dashboard**: Visualize progress, manage reviews, chat with AI coach

## Project Structure

```
leetloop/
├── clients/                 # Things that connect TO the backend
│   ├── extension/           # Chrome extension (Manifest V3)
│   ├── web/                 # Next.js web dashboard
│   └── telegram/            # Telegram bot (coming soon)
├── api/                     # Core backend service (FastAPI)
│   ├── app/
│   │   ├── main.py          # FastAPI app
│   │   ├── routers/         # API endpoints
│   │   └── services/        # Business logic
│   ├── Dockerfile
│   └── requirements.txt
├── packages/
│   └── shared/              # Shared TypeScript types/utilities
├── supabase/
│   └── migrations/          # SQL migrations
├── package.json             # Workspace root
└── pnpm-workspace.yaml
```

## Quick Start

### Prerequisites

- Node.js 18+
- pnpm 8+
- Python 3.11+ (for backend)
- Chrome browser

### Installation

```bash
# Install dependencies
pnpm install

# Build the extension
pnpm build:extension

# Install backend dependencies
cd api
pip install -r requirements.txt
```

### Run the Backend

```bash
# From project root
pnpm dev:api

# Or directly
cd api
uvicorn app.main:app --reload --port 8080
```

### Run the Web Dashboard

```bash
# From project root
pnpm dev:web

# Or directly
cd clients/web
pnpm dev
```

### Load Extension in Chrome

1. Open Chrome and go to `chrome://extensions`
2. Enable "Developer mode" (toggle in top right)
3. Click "Load unpacked"
4. Select the `clients/extension/dist` folder

### Configure Supabase

1. Create a free project at [supabase.com](https://supabase.com)
2. Run the migrations from `supabase/migrations/` in the SQL Editor
3. Copy your Project URL and anon key

**For the extension:**
- Click the LeetLoop extension icon → right-click → "Options"
- Enter your Supabase credentials

**For the backend:**
Create `api/.env`:
```
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_ANON_KEY=your-anon-key
GOOGLE_API_KEY=your-google-api-key  # Optional, for AI features
```

**For the web dashboard:**
Create `clients/web/.env.local`:
```
NEXT_PUBLIC_SUPABASE_URL=https://your-project.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=your-anon-key
NEXT_PUBLIC_API_URL=http://localhost:8080
```

## How It Works

### Submission Capture

The extension uses a dual content script pattern:

1. **Interceptor** (`world: "MAIN"`): Overrides `window.fetch` to capture LeetCode API responses
2. **Content Script**: Extracts problem metadata from the page DOM
3. **Background Worker**: Stores submissions locally and syncs to Supabase

### Data Captured

For each submission:
- Problem: slug, title, difficulty, tags
- Result: status, runtime, memory, percentiles
- Context: attempt number, time elapsed, language, full code
- Session: groups attempts on the same problem

### Spaced Repetition

When you fail a problem:
1. It's added to your review queue
2. Initial review: next day
3. On success: interval doubles (max 30 days)
4. On failure: resets to 1 day

### AI Coaching

- Chat with an AI coach about algorithms and problems
- Get personalized tips based on your weak areas
- Analyze your code for issues and improvements

## API Endpoints

| Endpoint | Description |
|----------|-------------|
| `GET /health` | Health check |
| `GET /api/progress/{user_id}` | User stats, skills, trends |
| `GET /api/recommendations/{user_id}` | Personalized problem recommendations |
| `GET /api/reviews/{user_id}` | Due review items |
| `POST /api/reviews/{id}/complete` | Mark review as done |
| `POST /api/coaching/chat` | AI coaching chat |
| `POST /api/coaching/analyze` | Code analysis |

## Development

```bash
# Watch mode for extension
cd clients/extension
pnpm dev

# Watch mode for web dashboard
pnpm dev:web

# Run backend with hot reload
pnpm dev:api

# Type checking
pnpm typecheck
```

## Deployment

### Backend (Google Cloud Run)

```bash
cd api
./deploy.sh
```

### Web Dashboard (Vercel)

```bash
cd clients/web
vercel
```

## Database Schema

See `supabase/migrations/` for full schema. Key tables:

- `submissions`: Every captured submission with full details
- `skill_scores`: Aggregated skill level per tag
- `review_queue`: Spaced repetition schedule
- `user_settings`: Preferences and integrations

## Privacy

- All data is stored locally by default
- Cloud sync is opt-in and uses your own Supabase project
- No data is sent to third parties
- Your LeetCode credentials are never accessed

## License

MIT
