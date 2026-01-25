#!/bin/bash
# Setup GCP Secrets Manager for LeetLoop Backend
# Project: 693222603964 (leetloop-485404)

set -e

PROJECT_ID="693222603964"
SECRETS=(
    "supabase-url:Supabase project URL (e.g., https://xxx.supabase.co)"
    "supabase-anon-key:Supabase anonymous/public key"
    "supabase-service-role-key:Supabase service role key (admin access)"
    "google-api-key:Google AI (Gemini) API key"
)

echo "=== LeetLoop GCP Secrets Setup ==="
echo "Project: ${PROJECT_ID}"
echo ""

# Set project
echo "Setting GCP project..."
gcloud config set project ${PROJECT_ID}

# Function to create secret if it doesn't exist
create_secret_if_needed() {
    local secret_name=$1

    if gcloud secrets describe ${secret_name} &>/dev/null; then
        echo "  Secret '${secret_name}' already exists"
        return 0
    else
        echo "  Creating secret '${secret_name}'..."
        gcloud secrets create ${secret_name} --replication-policy="automatic"
        return 1
    fi
}

# Function to add secret value
add_secret_value() {
    local secret_name=$1
    local description=$2

    echo ""
    echo "Enter value for ${secret_name}"
    echo "  (${description})"
    echo -n "  Value: "
    read -s secret_value
    echo ""

    if [ -z "${secret_value}" ]; then
        echo "  Skipped (empty value)"
        return
    fi

    echo -n "${secret_value}" | gcloud secrets versions add ${secret_name} --data-file=-
    echo "  Secret value added successfully"
}

echo ""
echo "Step 1: Creating secrets..."
echo ""

for secret_info in "${SECRETS[@]}"; do
    IFS=':' read -r name description <<< "${secret_info}"
    create_secret_if_needed "${name}"
done

echo ""
echo "Step 2: Adding secret values..."
echo "(Press Enter to skip a secret)"
echo ""

for secret_info in "${SECRETS[@]}"; do
    IFS=':' read -r name description <<< "${secret_info}"
    add_secret_value "${name}" "${description}"
done

echo ""
echo "=== Setup Complete ==="
echo ""
echo "Verify secrets:"
echo "  gcloud secrets list"
echo ""
echo "Grant Cloud Run access (if needed):"
echo "  gcloud secrets add-iam-policy-binding SECRET_NAME \\"
echo "    --member='serviceAccount:SERVICE_ACCOUNT' \\"
echo "    --role='roles/secretmanager.secretAccessor'"
echo ""
echo "Next steps:"
echo "  1. Deploy: ./deploy.sh"
echo "  2. Test: ./scripts/test-connections.sh"
