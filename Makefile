.PHONY: setup-env dev dev-web dev-api build lint typecheck db-push db-reset

# GCP Project
GCP_PROJECT := leetloop-485404

# Pull secrets from GCP and create .env files
setup-env:
	@echo "Pulling secrets from GCP..."
	@gcloud config set project $(GCP_PROJECT) > /dev/null 2>&1
	@SUPABASE_URL=$$(gcloud secrets versions access latest --secret=supabase-url) && \
	SUPABASE_ANON_KEY=$$(gcloud secrets versions access latest --secret=supabase-anon-key) && \
	SUPABASE_SERVICE_ROLE_KEY=$$(gcloud secrets versions access latest --secret=supabase-service-role-key) && \
	GOOGLE_API_KEY=$$(gcloud secrets versions access latest --secret=google-api-key 2>/dev/null || echo "") && \
	API_URL=$$(gcloud secrets versions access latest --secret=api-url) && \
	echo "# Supabase Configuration\nSUPABASE_URL=$$SUPABASE_URL\nSUPABASE_ANON_KEY=$$SUPABASE_ANON_KEY" > .env && \
	echo "# LeetLoop Backend Environment Variables\n\n# Application\nENVIRONMENT=development\nDEBUG=true\n\n# Supabase\nSUPABASE_URL=$$SUPABASE_URL\nSUPABASE_KEY=$$SUPABASE_SERVICE_ROLE_KEY\n\n# Google AI (Gemini)\nGOOGLE_API_KEY=$$GOOGLE_API_KEY\n\n# Server\nPORT=8080\n\n# CORS (JSON array format)\nALLOWED_ORIGINS=[\"http://localhost:3000\",\"http://localhost:3001\"]" > api/.env && \
	echo "# Supabase\nNEXT_PUBLIC_SUPABASE_URL=$$SUPABASE_URL\nNEXT_PUBLIC_SUPABASE_ANON_KEY=$$SUPABASE_ANON_KEY\n\n# Backend API\nNEXT_PUBLIC_API_URL=http://localhost:8080" > clients/web/.env && \
	echo "Created .env files:"
	@echo "  - .env (root)"
	@echo "  - api/.env"
	@echo "  - clients/web/.env"

# Development
dev:
	pnpm dev

dev-web:
	pnpm dev:web

dev-api:
	pnpm dev:api

# Building
build:
	pnpm build

build-web:
	pnpm build:web

build-extension:
	pnpm build:extension

# Code Quality
lint:
	pnpm lint

typecheck:
	pnpm typecheck

# Database
db-push:
	pnpm db:push

db-reset:
	pnpm db:reset

db-diff:
	pnpm db:diff
