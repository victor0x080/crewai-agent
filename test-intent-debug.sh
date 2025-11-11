#!/bin/bash

# Intent Classification Debug Script
# Tests why intent classification is failing

echo "=========================================="
echo "Intent Classification Debug"
echo "=========================================="
echo ""

BASE_URL="${1:-http://localhost:3001}"

# Test 1: Check server health
echo "1. Checking server health..."
HEALTH=$(curl -s "$BASE_URL/api/health" 2>/dev/null)
if [ $? -eq 0 ]; then
    echo "   ✅ Server is responding"
    echo "$HEALTH" | jq '.' 2>/dev/null || echo "$HEALTH"
else
    echo "   ❌ Server not responding"
    echo "   Check if server is running: npm start"
    exit 1
fi
echo ""

# Test 2: Check if OpenAI is configured
echo "2. Testing OpenAI configuration..."
TEST_QUERY="What is the demand forecast?"
echo "   Query: \"$TEST_QUERY\""
echo "   Sending request..."
START_TIME=$(date +%s%N)
START_TIME_MS=$((START_TIME / 1000000))

RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "$BASE_URL/api/process-message" \
    -H "Content-Type: application/json" \
    -d "{\"message\": \"$TEST_QUERY\", \"conversationId\": \"debug-$(date +%s)\", \"userId\": \"debug-user\"}" \
    --max-time 10)

HTTP_CODE=$(echo "$RESPONSE" | tail -n1)
RESPONSE_BODY=$(echo "$RESPONSE" | sed '$d')

END_TIME=$(date +%s%N)
END_TIME_MS=$((END_TIME / 1000000))
DURATION=$((END_TIME_MS - START_TIME_MS))

if [ "$HTTP_CODE" -ne 200 ]; then
    echo "   ❌ Request failed with HTTP $HTTP_CODE"
    echo "$RESPONSE_BODY"
    exit 1
fi

echo "   ✅ Request successful (${DURATION}ms)"
echo ""

# Test 3: Analyze intent classification result
echo "3. Intent Classification Analysis:"
INTENT=$(echo "$RESPONSE_BODY" | jq -r '.intentClassification.intent // "N/A"')
CONFIDENCE=$(echo "$RESPONSE_BODY" | jq -r '.intentClassification.confidence // "N/A"')
EXPLANATION=$(echo "$RESPONSE_BODY" | jq -r '.intentClassification.explanation // "N/A"')
TYPE=$(echo "$RESPONSE_BODY" | jq -r '.intentClassification.type // "N/A"')

echo "   Intent: $INTENT"
echo "   Confidence: $CONFIDENCE"
echo "   Type: $TYPE"
echo "   Explanation: $EXPLANATION"
echo ""

if [ "$CONFIDENCE" = "0.5" ] && echo "$EXPLANATION" | grep -q "Timeout\|fallback"; then
    echo "   ⚠️  ISSUE DETECTED: Using fallback (timeout or error)"
    echo ""
    echo "   Possible causes:"
    echo "   1. Server not restarted after timeout change"
    echo "   2. OpenAI API call failing (>5s)"
    echo "   3. Prompt not found in Supabase"
    echo "   4. OpenAI initialization failed"
    echo ""
    echo "   Next steps:"
    echo "   1. Restart server: npm start"
    echo "   2. Check server logs for errors"
    echo "   3. Verify OpenAI API key is valid"
    echo "   4. Check Supabase for 'intent_classifier' prompt"
else
    echo "   ✅ Intent classification working (confidence: $CONFIDENCE)"
fi

echo ""
echo "=========================================="
echo "Full Response (intent section):"
echo "=========================================="
echo "$RESPONSE_BODY" | jq '.intentClassification' 2>/dev/null || echo "$RESPONSE_BODY"

