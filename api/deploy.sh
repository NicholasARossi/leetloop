#!/bin/bash
# Deploy LeetLoop Backend to Google Cloud Run

set -e

# Configuration
PROJECT_ID="${GCP_PROJECT_ID:-leetloop-485404}"
REGION="${GCP_REGION:-us-central1}"
SERVICE_NAME="leetloop-api"
IMAGE_NAME="gcr.io/${PROJECT_ID}/${SERVICE_NAME}"

echo "=== LeetLoop Backend Deployment ==="
echo "Project: ${PROJECT_ID}"
echo "Region: ${REGION}"
echo "Service: ${SERVICE_NAME}"
echo ""

# Build the container image
echo "Building container image..."
docker build -t ${IMAGE_NAME}:latest .

# Push to Google Container Registry
echo "Pushing to GCR..."
docker push ${IMAGE_NAME}:latest

# Deploy to Cloud Run
echo "Deploying to Cloud Run..."
gcloud run deploy ${SERVICE_NAME} \
    --image ${IMAGE_NAME}:latest \
    --region ${REGION} \
    --platform managed \
    --allow-unauthenticated \
    --cpu 1 \
    --memory 2Gi \
    --min-instances 0 \
    --max-instances 10 \
    --timeout 300 \
    --set-env-vars "ENVIRONMENT=production,DEBUG=false" \
    --set-secrets "SUPABASE_URL=supabase-url:latest,SUPABASE_ANON_KEY=supabase-anon-key:latest,SUPABASE_SERVICE_ROLE_KEY=supabase-service-role-key:latest,GOOGLE_API_KEY=google-api-key:latest"

# Get the service URL
SERVICE_URL=$(gcloud run services describe ${SERVICE_NAME} --region ${REGION} --format 'value(status.url)')

echo ""
echo "=== Deployment Complete ==="
echo "Service URL: ${SERVICE_URL}"
echo ""
echo "Test with:"
echo "  curl ${SERVICE_URL}/health"
echo "  curl ${SERVICE_URL}/api/recommendations/{user_id}"
