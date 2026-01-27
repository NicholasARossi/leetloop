#!/bin/bash
# Deploy LeetLoop (Unified Web + API) to Google Cloud Run

set -e

# Configuration
PROJECT_ID="${GCP_PROJECT_ID:-leetloop-485404}"
REGION="${GCP_REGION:-us-central1}"
SERVICE_NAME="leetloop"
IMAGE_NAME="gcr.io/${PROJECT_ID}/${SERVICE_NAME}"

echo "=== LeetLoop Unified Deployment ==="
echo "Project: ${PROJECT_ID}"
echo "Region: ${REGION}"
echo "Service: ${SERVICE_NAME}"
echo ""

# Build and push using Cloud Build (avoids local Docker auth issues)
echo "Building container image with Cloud Build..."
gcloud builds submit --config=cloudbuild.yaml --project ${PROJECT_ID}

# Deploy to Cloud Run
# Note: Cloud Run only exposes one port, so we use 8080 (API) as the main port
# and configure the web app to be proxied through nginx or accessed separately
echo "Deploying to Cloud Run..."
gcloud run deploy ${SERVICE_NAME} \
    --image ${IMAGE_NAME}:latest \
    --region ${REGION} \
    --platform managed \
    --allow-unauthenticated \
    --cpu 2 \
    --memory 4Gi \
    --min-instances 0 \
    --max-instances 10 \
    --timeout 300 \
    --port 8080 \
    --set-env-vars "ENVIRONMENT=production,DEBUG=false" \
    --set-secrets "SUPABASE_URL=supabase-url:latest,SUPABASE_ANON_KEY=supabase-anon-key:latest,SUPABASE_SERVICE_ROLE_KEY=supabase-service-role-key:latest,GOOGLE_API_KEY=google-api-key:latest"

# Get the service URL
SERVICE_URL=$(gcloud run services describe ${SERVICE_NAME} --region ${REGION} --format 'value(status.url)')

echo ""
echo "=== Deployment Complete ==="
echo "Service URL: ${SERVICE_URL}"
echo ""
echo "API endpoints:"
echo "  Health: ${SERVICE_URL}/health"
echo "  Docs:   ${SERVICE_URL}/docs (if debug enabled)"
echo ""
echo "To update extension, set API_URL to: ${SERVICE_URL}"
echo ""
echo "Test with:"
echo "  curl ${SERVICE_URL}/health"
echo "  curl ${SERVICE_URL}/api/recommendations/{user_id}"
