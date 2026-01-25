# LeetLoop Backend Deployment Guide

This guide covers deploying the LeetLoop backend API to Google Cloud Run with GCP Secrets Manager integration.

## Prerequisites

- **gcloud CLI**: Installed and authenticated (`gcloud auth login`)
- **Docker**: Installed and running
- **Python 3.11+**: For local development
- **GCP Access**: Access to project `693222603964` (`leetloop-485404`)

### Verify Prerequisites

```bash
# Check gcloud
gcloud --version

# Check Docker
docker --version

# Check Python
python3 --version

# Authenticate with GCP
gcloud auth login
gcloud config set project 693222603964
```

## GCP Secrets Manager Setup

The backend uses the following secrets stored in GCP Secrets Manager:

| Secret Name | Environment Variable | Required | Description |
|-------------|---------------------|----------|-------------|
| `supabase-url` | `SUPABASE_URL` | Yes | Supabase project URL |
| `supabase-anon-key` | `SUPABASE_ANON_KEY` | Yes | Supabase anonymous key |
| `supabase-service-role-key` | `SUPABASE_SERVICE_ROLE_KEY` | No | Supabase admin key |
| `google-api-key` | `GOOGLE_API_KEY` | No | Gemini API key (AI features disabled if not set) |

### Create Secrets

Use the automated script or run manually:

#### Automated Setup

```bash
cd api
./scripts/setup-secrets.sh
```

#### Manual Setup

```bash
# Set project
gcloud config set project 693222603964

# Create secrets
gcloud secrets create supabase-url --replication-policy="automatic"
gcloud secrets create supabase-anon-key --replication-policy="automatic"
gcloud secrets create supabase-service-role-key --replication-policy="automatic"
gcloud secrets create google-api-key --replication-policy="automatic"

# Add secret values (replace with your actual values)
echo -n "https://your-project.supabase.co" | gcloud secrets versions add supabase-url --data-file=-
echo -n "your-anon-key" | gcloud secrets versions add supabase-anon-key --data-file=-
echo -n "your-service-role-key" | gcloud secrets versions add supabase-service-role-key --data-file=-
echo -n "your-gemini-api-key" | gcloud secrets versions add google-api-key --data-file=-
```

### Verify Secrets

```bash
# List all secrets
gcloud secrets list

# View a secret value (be careful with sensitive data)
gcloud secrets versions access latest --secret=supabase-url
```

## Local Development

### 1. Set Up Environment

```bash
cd api

# Copy environment template
cp .env.example .env

# Edit .env with your development values
# Get values from Supabase dashboard and Google AI Studio
```

### 2. Install Dependencies

```bash
# Create virtual environment (recommended)
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Run Locally

```bash
# Start development server
uvicorn app.main:app --reload --port 8080

# Or with host binding for Docker/network access
uvicorn app.main:app --reload --host 0.0.0.0 --port 8080
```

### 4. Test Local Instance

```bash
# Health check
curl http://localhost:8080/health

# API docs (only available in development mode)
open http://localhost:8080/docs
```

## Cloud Run Deployment

### 1. Ensure Secrets Exist

Before deploying, make sure all required secrets are created in GCP Secrets Manager (see above).

### 2. Deploy

```bash
cd api
./deploy.sh
```

The script will:
1. Build the Docker container
2. Push to Google Container Registry
3. Deploy to Cloud Run with secrets mounted
4. Output the service URL

### 3. Verify Deployment

```bash
# Get service URL
SERVICE_URL=$(gcloud run services describe leetloop-api --region us-central1 --format 'value(status.url)')

# Test health endpoint
curl $SERVICE_URL/health
```

## Connection Testing

Use the test script to verify all integrations:

```bash
cd api

# Test local instance
./scripts/test-connections.sh http://localhost:8080

# Test deployed instance
./scripts/test-connections.sh https://leetloop-api-xxx-uc.a.run.app
```

### Manual Testing

```bash
# Health check - should return {"status": "healthy", "service": "leetloop-api"}
curl https://leetloop-api-xxx.run.app/health

# Test Supabase connection (requires valid user_id)
curl https://leetloop-api-xxx.run.app/api/progress/{user_id}

# Test AI connection
curl -X POST https://leetloop-api-xxx.run.app/api/coaching/chat \
  -H "Content-Type: application/json" \
  -d '{"user_id": "test-user", "message": "Hello"}'

# Get recommendations
curl https://leetloop-api-xxx.run.app/api/recommendations/{user_id}
```

## Troubleshooting

### Secret Access Errors

If you see "Permission denied" errors for secrets:

```bash
# Get the service account
gcloud run services describe leetloop-api --region us-central1 --format 'value(spec.template.spec.serviceAccountName)'

# Grant secret accessor role
gcloud secrets add-iam-policy-binding supabase-url \
  --member="serviceAccount:SERVICE_ACCOUNT_EMAIL" \
  --role="roles/secretmanager.secretAccessor"
```

### Container Build Failures

```bash
# Build locally to debug
docker build -t leetloop-api:test .

# Run locally
docker run -p 8080:8080 --env-file .env leetloop-api:test
```

### View Cloud Run Logs

```bash
gcloud run services logs read leetloop-api --region us-central1 --limit 50
```

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `ENVIRONMENT` | `development` or `production` | `development` |
| `DEBUG` | Enable debug mode | `true` |
| `PORT` | Server port | `8080` |
| `ALLOWED_ORIGINS` | CORS allowed origins (comma-separated) | `http://localhost:3000` |
| `SUPABASE_URL` | Supabase project URL | - |
| `SUPABASE_ANON_KEY` | Supabase anonymous key | - |
| `SUPABASE_SERVICE_ROLE_KEY` | Supabase service role key | - |
| `GOOGLE_API_KEY` | Google AI (Gemini) API key | - |

## Architecture

```
Cloud Run (leetloop-api)
    |
    +-- GCP Secrets Manager (credentials)
    |
    +-- Supabase (database + auth)
    |
    +-- Google AI / Gemini (coaching features)
```
