#!/bin/bash
# Test LeetLoop API connections and integrations

API_URL="${1:-http://localhost:8080}"
TEST_USER_ID="${2:-test-user-$(date +%s)}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "=== LeetLoop API Connection Tests ==="
echo "API URL: ${API_URL}"
echo "Test User ID: ${TEST_USER_ID}"
echo ""

# Check if jq is available
if command -v jq &> /dev/null; then
    JQ_AVAILABLE=true
else
    JQ_AVAILABLE=false
    echo -e "${YELLOW}Note: 'jq' not found. Install for prettier output.${NC}"
    echo ""
fi

format_json() {
    if [ "$JQ_AVAILABLE" = true ]; then
        echo "$1" | jq . 2>/dev/null || echo "$1"
    else
        echo "$1"
    fi
}

# Helper to extract body and code from curl response
# Works on both macOS and Linux
extract_response() {
    local response="$1"
    local line_count=$(echo "$response" | wc -l)
    RESPONSE_CODE=$(echo "$response" | tail -1)
    if [ "$line_count" -gt 1 ]; then
        RESPONSE_BODY=$(echo "$response" | sed '$d')
    else
        RESPONSE_BODY=""
    fi
}

# Test 1: Health Check
echo "1. Testing health endpoint..."
echo "   GET ${API_URL}/health"
HEALTH_RESPONSE=$(curl -s -w "\n%{http_code}" "${API_URL}/health" 2>/dev/null || echo -e "\n000")
extract_response "$HEALTH_RESPONSE"
HEALTH_CODE="$RESPONSE_CODE"
HEALTH_BODY="$RESPONSE_BODY"

if [ "$HEALTH_CODE" = "200" ]; then
    echo -e "   ${GREEN}PASS${NC} (HTTP ${HEALTH_CODE})"
    echo "   Response: $(format_json "$HEALTH_BODY")"
elif [ "$HEALTH_CODE" = "000" ]; then
    echo -e "   ${RED}FAIL${NC} - Connection refused (is the server running?)"
else
    echo -e "   ${RED}FAIL${NC} (HTTP ${HEALTH_CODE})"
    echo "   Response: $HEALTH_BODY"
fi
echo ""

# Exit early if server is not running
if [ "$HEALTH_CODE" = "000" ]; then
    echo -e "${RED}Server not reachable at ${API_URL}${NC}"
    echo ""
    echo "To start the server locally:"
    echo "  cd api && uvicorn app.main:app --reload --port 8080"
    exit 1
fi

# Test 2: Root Endpoint
echo "2. Testing root endpoint..."
echo "   GET ${API_URL}/"
ROOT_RESPONSE=$(curl -s -w "\n%{http_code}" "${API_URL}/")
extract_response "$ROOT_RESPONSE"
ROOT_CODE="$RESPONSE_CODE"
ROOT_BODY="$RESPONSE_BODY"

if [ "$ROOT_CODE" = "200" ]; then
    echo -e "   ${GREEN}PASS${NC} (HTTP ${ROOT_CODE})"
    echo "   Response: $(format_json "$ROOT_BODY")"
else
    echo -e "   ${RED}FAIL${NC} (HTTP ${ROOT_CODE})"
    echo "   Response: $ROOT_BODY"
fi
echo ""

# Test 3: Supabase Connection (via progress endpoint)
echo "3. Testing Supabase connection..."
echo "   GET ${API_URL}/api/progress/${TEST_USER_ID}"
PROGRESS_RESPONSE=$(curl -s -w "\n%{http_code}" "${API_URL}/api/progress/${TEST_USER_ID}")
extract_response "$PROGRESS_RESPONSE"
PROGRESS_CODE="$RESPONSE_CODE"
PROGRESS_BODY="$RESPONSE_BODY"

if [ "$PROGRESS_CODE" = "200" ] || [ "$PROGRESS_CODE" = "404" ]; then
    echo -e "   ${GREEN}PASS${NC} (HTTP ${PROGRESS_CODE} - Supabase responding)"
    echo "   Response: $(format_json "$PROGRESS_BODY")"
elif [ "$PROGRESS_CODE" = "500" ]; then
    echo -e "   ${RED}FAIL${NC} (HTTP ${PROGRESS_CODE} - Check Supabase credentials)"
    echo "   Response: $(format_json "$PROGRESS_BODY")"
else
    echo -e "   ${YELLOW}WARN${NC} (HTTP ${PROGRESS_CODE})"
    echo "   Response: $(format_json "$PROGRESS_BODY")"
fi
echo ""

# Test 4: Recommendations Endpoint
echo "4. Testing recommendations endpoint..."
echo "   GET ${API_URL}/api/recommendations/${TEST_USER_ID}"
REC_RESPONSE=$(curl -s -w "\n%{http_code}" "${API_URL}/api/recommendations/${TEST_USER_ID}")
extract_response "$REC_RESPONSE"
REC_CODE="$RESPONSE_CODE"
REC_BODY="$RESPONSE_BODY"

if [ "$REC_CODE" = "200" ]; then
    echo -e "   ${GREEN}PASS${NC} (HTTP ${REC_CODE})"
    # Truncate if response is long
    if [ ${#REC_BODY} -gt 500 ]; then
        echo "   Response: (truncated) $(echo "$REC_BODY" | head -c 500)..."
    else
        echo "   Response: $(format_json "$REC_BODY")"
    fi
else
    echo -e "   ${YELLOW}WARN${NC} (HTTP ${REC_CODE})"
    echo "   Response: $(format_json "$REC_BODY")"
fi
echo ""

# Test 5: Gemini/AI Connection (via coaching endpoint)
echo "5. Testing AI/Gemini connection..."
echo "   POST ${API_URL}/api/coaching/chat"
AI_RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "${API_URL}/api/coaching/chat" \
    -H "Content-Type: application/json" \
    -d "{\"user_id\": \"${TEST_USER_ID}\", \"message\": \"Hello, can you help me?\"}")
extract_response "$AI_RESPONSE"
AI_CODE="$RESPONSE_CODE"
AI_BODY="$RESPONSE_BODY"

if [ "$AI_CODE" = "200" ]; then
    echo -e "   ${GREEN}PASS${NC} (HTTP ${AI_CODE} - AI responding)"
    # Truncate if response is long
    if [ ${#AI_BODY} -gt 500 ]; then
        echo "   Response: (truncated) $(echo "$AI_BODY" | head -c 500)..."
    else
        echo "   Response: $(format_json "$AI_BODY")"
    fi
elif [ "$AI_CODE" = "503" ] || [ "$AI_CODE" = "500" ]; then
    echo -e "   ${YELLOW}WARN${NC} (HTTP ${AI_CODE} - AI may be disabled or misconfigured)"
    echo "   Response: $(format_json "$AI_BODY")"
else
    echo -e "   ${YELLOW}INFO${NC} (HTTP ${AI_CODE})"
    echo "   Response: $(format_json "$AI_BODY")"
fi
echo ""

# Summary
echo "=== Test Summary ==="
echo "Health:          HTTP ${HEALTH_CODE}"
echo "Root:            HTTP ${ROOT_CODE}"
echo "Supabase:        HTTP ${PROGRESS_CODE}"
echo "Recommendations: HTTP ${REC_CODE}"
echo "AI/Gemini:       HTTP ${AI_CODE}"
echo ""

# Overall status
if [ "$HEALTH_CODE" = "200" ]; then
    echo -e "${GREEN}API is running and healthy!${NC}"
else
    echo -e "${RED}API health check failed.${NC}"
    exit 1
fi
