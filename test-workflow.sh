#!/bin/bash

# ============================================================================
# Complete Workflow Test Suite
# Tests: Health → Agents → Intent → Templates → Full Queries
# ============================================================================

set -e  # Exit on error

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Configuration
BASE_URL="${1:-http://localhost:3001}"
TOTAL_TESTS=0
PASSED_TESTS=0
FAILED_TESTS=0

# Test results
declare -a TEST_RESULTS

echo ""
echo "============================================"
echo "🧪 Complete Workflow Test Suite"
echo "============================================"
echo ""
echo "Testing against: $BASE_URL"
echo ""

# Helper function to print test result
print_test() {
    local name="$1"
    local status="$2"
    local details="$3"
    
    TOTAL_TESTS=$((TOTAL_TESTS + 1))
    
    if [ "$status" = "PASS" ]; then
        echo -e "${GREEN}✅ PASS${NC}: $name"
        PASSED_TESTS=$((PASSED_TESTS + 1))
    else
        echo -e "${RED}❌ FAIL${NC}: $name"
        FAILED_TESTS=$((FAILED_TESTS + 1))
        if [ -n "$details" ]; then
            echo "   $details"
        fi
    fi
}

# Helper function to make API calls
api_call() {
    local method="$1"
    local endpoint="$2"
    local data="$3"
    
    if [ "$method" = "GET" ]; then
        RESPONSE=$(curl -s -w "\n%{http_code}" "$BASE_URL$endpoint" --max-time 30)
        HTTP_CODE=$(echo "$RESPONSE" | tail -n1)
        RESPONSE_BODY=$(echo "$RESPONSE" | sed '$d')
    else
        RESPONSE=$(curl -s -w "\n%{http_code}" -X "$method" "$BASE_URL$endpoint" \
            -H "Content-Type: application/json" \
            -d "$data" \
            --max-time 30)
        HTTP_CODE=$(echo "$RESPONSE" | tail -n1)
        RESPONSE_BODY=$(echo "$RESPONSE" | sed '$d')
    fi
    
    echo "$HTTP_CODE|$RESPONSE_BODY"
}

# ============================================================================
# TEST 1: Health Check
# ============================================================================

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "TEST 1: Health Check"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

RESULT=$(api_call "GET" "/api/health")
HTTP_CODE=$(echo "$RESULT" | cut -d'|' -f1)
RESPONSE_BODY=$(echo "$RESULT" | cut -d'|' -f2-)

if [ "$HTTP_CODE" = "200" ]; then
    STATUS=$(echo "$RESPONSE_BODY" | jq -r '.status // "unknown"' 2>/dev/null || echo "unknown")
    if [ "$STATUS" = "healthy" ]; then
        print_test "Health endpoint returns healthy status" "PASS"
        
        # Check services
        SERVICES=$(echo "$RESPONSE_BODY" | jq -r '.services // {}' 2>/dev/null || echo "{}")
        echo "$SERVICES" | jq -r 'to_entries[] | "   \(.key): \(if .value then "✅" else "❌" end)"' 2>/dev/null || true
    else
        print_test "Health endpoint returns healthy status" "FAIL" "Status: $STATUS"
    fi
else
    print_test "Health endpoint responds" "FAIL" "HTTP $HTTP_CODE"
fi

echo ""

# ============================================================================
# TEST 2: Agents List
# ============================================================================

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "TEST 2: Agents List"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

RESULT=$(api_call "GET" "/api/agents")
HTTP_CODE=$(echo "$RESULT" | cut -d'|' -f1)
RESPONSE_BODY=$(echo "$RESULT" | cut -d'|' -f2-)

if [ "$HTTP_CODE" = "200" ]; then
    AGENT_COUNT=$(echo "$RESPONSE_BODY" | jq '.agents | length' 2>/dev/null || echo "0")
    if [ "$AGENT_COUNT" -gt 0 ]; then
        print_test "Agents endpoint returns agents" "PASS" "$AGENT_COUNT agents found"
    else
        print_test "Agents endpoint returns agents" "FAIL" "No agents found"
    fi
else
    print_test "Agents endpoint responds" "FAIL" "HTTP $HTTP_CODE"
fi

echo ""

# ============================================================================
# TEST 3: Intent Classification
# ============================================================================

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "TEST 3: Intent Classification"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

TEST_QUERIES=(
    "What is the demand forecast for Q3 2025?"
    "How should I allocate my marketing budget?"
    "Do I have enough inventory for the holiday season?"
)

for QUERY in "${TEST_QUERIES[@]}"; do
    echo "   Testing: \"$QUERY\""
    
    JSON_DATA=$(cat <<EOF
{
  "message": "$QUERY",
  "conversationId": "test-workflow-$(date +%s)",
  "userId": "test-user"
}
EOF
)
    
    RESULT=$(api_call "POST" "/api/process-message" "$JSON_DATA")
    HTTP_CODE=$(echo "$RESULT" | cut -d'|' -f1)
    RESPONSE_BODY=$(echo "$RESULT" | cut -d'|' -f2-)
    
    if [ "$HTTP_CODE" = "200" ]; then
        INTENT=$(echo "$RESPONSE_BODY" | jq -r '.intentClassification.intent // "N/A"' 2>/dev/null)
        CONFIDENCE=$(echo "$RESPONSE_BODY" | jq -r '.intentClassification.confidence // 0' 2>/dev/null)
        
        if [ "$INTENT" != "N/A" ] && [ "$CONFIDENCE" != "0" ]; then
            print_test "Intent classification for: \"$QUERY\"" "PASS" "Intent: $INTENT, Confidence: $CONFIDENCE"
        else
            print_test "Intent classification for: \"$QUERY\"" "FAIL" "Intent: $INTENT, Confidence: $CONFIDENCE"
        fi
    else
        print_test "Intent classification for: \"$QUERY\"" "FAIL" "HTTP $HTTP_CODE"
    fi
    
    echo ""
done

# ============================================================================
# TEST 4: Template Discovery
# ============================================================================

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "TEST 4: Template Discovery"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

JSON_DATA=$(cat <<EOF
{
  "message": "What is the demand forecast for Q3 2025?",
  "conversationId": "test-templates-$(date +%s)",
  "userId": "test-user"
}
EOF
)

RESULT=$(api_call "POST" "/api/process-message" "$JSON_DATA")
HTTP_CODE=$(echo "$RESULT" | cut -d'|' -f1)
RESPONSE_BODY=$(echo "$RESULT" | cut -d'|' -f2-)

if [ "$HTTP_CODE" = "200" ]; then
    TEMPLATE_COUNT=$(echo "$RESPONSE_BODY" | jq '.templates | length' 2>/dev/null || echo "0")
    if [ "$TEMPLATE_COUNT" -gt 0 ]; then
        print_test "Templates discovered" "PASS" "$TEMPLATE_COUNT templates found"
        
        echo "$RESPONSE_BODY" | jq -r '.templates[]? | "   • \(.name) (Relevance: \(.relevance))"' 2>/dev/null || true
    else
        print_test "Templates discovered" "FAIL" "No templates found"
    fi
else
    print_test "Template discovery" "FAIL" "HTTP $HTTP_CODE"
fi

echo ""

# ============================================================================
# TEST 5: Agent Allocation
# ============================================================================

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "TEST 5: Agent Allocation"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

JSON_DATA=$(cat <<EOF
{
  "message": "What is the demand forecast for Q3 2025?",
  "conversationId": "test-agents-$(date +%s)",
  "userId": "test-user"
}
EOF
)

RESULT=$(api_call "POST" "/api/process-message" "$JSON_DATA")
HTTP_CODE=$(echo "$RESULT" | cut -d'|' -f1)
RESPONSE_BODY=$(echo "$RESULT" | cut -d'|' -f2-)

if [ "$HTTP_CODE" = "200" ]; then
    # Count unique agents from procedural tasks
    AGENT_COUNT=$(echo "$RESPONSE_BODY" | jq -r '[.turnEnvelope.plan.procedural[]?.service] | unique | length' 2>/dev/null || echo "0")
    if [ "$AGENT_COUNT" -gt 0 ]; then
        print_test "Agents allocated" "PASS" "$AGENT_COUNT unique agents"
        
        echo "$RESPONSE_BODY" | jq -r '[.turnEnvelope.plan.procedural[].service] | unique[]' 2>/dev/null | sed 's/^/   • /' || true
    else
        print_test "Agents allocated" "FAIL" "No agents allocated"
    fi
else
    print_test "Agent allocation" "FAIL" "HTTP $HTTP_CODE"
fi

echo ""

# ============================================================================
# TEST 6: Execution Plan
# ============================================================================

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "TEST 6: Execution Plan Generation"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

JSON_DATA=$(cat <<EOF
{
  "message": "What is the demand forecast for Q3 2025?",
  "conversationId": "test-plan-$(date +%s)",
  "userId": "test-user"
}
EOF
)

RESULT=$(api_call "POST" "/api/process-message" "$JSON_DATA")
HTTP_CODE=$(echo "$RESULT" | cut -d'|' -f1)
RESPONSE_BODY=$(echo "$RESULT" | cut -d'|' -f2-)

if [ "$HTTP_CODE" = "200" ]; then
    HAS_DECLARATIVE=$(echo "$RESPONSE_BODY" | jq -r '.turnEnvelope.plan.declarative // [] | length' 2>/dev/null || echo "0")
    HAS_PROCEDURAL=$(echo "$RESPONSE_BODY" | jq -r '.turnEnvelope.plan.procedural // [] | length' 2>/dev/null || echo "0")
    HAS_ACK=$(echo "$RESPONSE_BODY" | jq -r '.turnEnvelope.ack // ""' 2>/dev/null || echo "")
    
    if [ "$HAS_DECLARATIVE" -gt 0 ] || [ "$HAS_PROCEDURAL" -gt 0 ]; then
        print_test "Execution plan generated" "PASS" "$HAS_DECLARATIVE declarative, $HAS_PROCEDURAL procedural tasks"
        
        if [ -n "$HAS_ACK" ]; then
            print_test "Acknowledgment message present" "PASS"
        else
            print_test "Acknowledgment message present" "FAIL"
        fi
    else
        print_test "Execution plan generated" "FAIL" "No plan found"
    fi
else
    print_test "Execution plan generation" "FAIL" "HTTP $HTTP_CODE"
fi

echo ""

# ============================================================================
# TEST 7: Response Time Performance
# ============================================================================

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "TEST 7: Response Time Performance"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

JSON_DATA=$(cat <<EOF
{
  "message": "What is the demand forecast for Q3 2025?",
  "conversationId": "test-performance-$(date +%s)",
  "userId": "test-user"
}
EOF
)

START_TIME=$(date +%s%N)
RESULT=$(api_call "POST" "/api/process-message" "$JSON_DATA")
END_TIME=$(date +%s%N)
HTTP_CODE=$(echo "$RESULT" | cut -d'|' -f1)
RESPONSE_BODY=$(echo "$RESULT" | cut -d'|' -f2-)

DURATION_MS=$(( (END_TIME - START_TIME) / 1000000 ))

if [ "$HTTP_CODE" = "200" ]; then
    if [ "$DURATION_MS" -lt 10000 ]; then
        print_test "Response time acceptable" "PASS" "${DURATION_MS}ms (under 10s)"
    else
        print_test "Response time acceptable" "FAIL" "${DURATION_MS}ms (over 10s)"
    fi
else
    print_test "Response time test" "FAIL" "HTTP $HTTP_CODE"
    echo "   Response: $(echo "$RESPONSE_BODY" | head -c 200)"
fi

echo ""

# ============================================================================
# TEST 8: Multiple Query Types
# ============================================================================

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "TEST 8: Multiple Query Types"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

QUERY_TYPES=(
    "Forecasting:What is the demand forecast for Q3 2025?"
    "Marketing:How should I allocate my marketing budget?"
    "Inventory:Do I have enough inventory for the holiday season?"
    "Pricing:What if we reduce prices by 15%?"
    "Sales:What is the revenue forecast for next quarter?"
)

for QUERY_TYPE in "${QUERY_TYPES[@]}"; do
    TYPE=$(echo "$QUERY_TYPE" | cut -d':' -f1)
    QUERY=$(echo "$QUERY_TYPE" | cut -d':' -f2-)
    
    JSON_DATA=$(cat <<EOF
{
  "message": "$QUERY",
  "conversationId": "test-query-$(date +%s)-$RANDOM",
  "userId": "test-user"
}
EOF
)
    
    RESULT=$(api_call "POST" "/api/process-message" "$JSON_DATA")
    HTTP_CODE=$(echo "$RESULT" | cut -d'|' -f1)
    RESPONSE_BODY=$(echo "$RESULT" | cut -d'|' -f2-)
    
    if [ "$HTTP_CODE" = "200" ]; then
        print_test "$TYPE query type" "PASS"
    else
        print_test "$TYPE query type" "FAIL" "HTTP $HTTP_CODE"
    fi
done

echo ""

# ============================================================================
# FINAL SUMMARY
# ============================================================================

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📊 TEST SUMMARY"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "Total Tests: $TOTAL_TESTS"
echo -e "${GREEN}Passed: $PASSED_TESTS${NC}"
echo -e "${RED}Failed: $FAILED_TESTS${NC}"
echo ""

SUCCESS_RATE=$(( PASSED_TESTS * 100 / TOTAL_TESTS ))
echo "Success Rate: $SUCCESS_RATE%"
echo ""

if [ "$FAILED_TESTS" -eq 0 ]; then
    echo -e "${GREEN}✅ All tests passed!${NC}"
    exit 0
else
    echo -e "${RED}❌ Some tests failed${NC}"
    exit 1
fi

