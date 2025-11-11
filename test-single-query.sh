#!/bin/bash

# ============================================================================
# Quick Single Query Test
# Usage: ./test-single-query.sh [--query "Your business question here"] [--url "http://localhost:3001"]
# ============================================================================

# Default values
QUERY="${1:-What is the demand forecast for Q3 2025?}"
BASE_URL="${2:-http://localhost:3001}"

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --query|-q)
            QUERY="$2"
            shift 2
            ;;
        --url|-u)
            BASE_URL="$2"
            shift 2
            ;;
        *)
            # If first arg doesn't start with --, treat it as query
            if [[ ! "$1" =~ ^-- ]]; then
                QUERY="$1"
            fi
            shift
            ;;
    esac
done

echo ""
echo "Testing Query: \"$QUERY\""
echo ""

START_TIME=$(date +%s%N)
START_TIME_MS=$((START_TIME / 1000000))

# Generate conversation ID
CONV_ID="test-$(date +%Y%m%d%H%M%S)"

# Prepare JSON body
JSON_BODY=$(cat <<EOF
{
  "message": "$QUERY",
  "conversationId": "$CONV_ID",
  "userId": "test-user"
}
EOF
)

# Send request
echo "Sending request..."
RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "$BASE_URL/api/process-message" \
    -H "Content-Type: application/json" \
    -d "$JSON_BODY" \
    --max-time 30)

# Extract HTTP status code (last line)
HTTP_CODE=$(echo "$RESPONSE" | tail -n1)
RESPONSE_BODY=$(echo "$RESPONSE" | sed '$d')

END_TIME=$(date +%s%N)
END_TIME_MS=$((END_TIME / 1000000))
DURATION=$((END_TIME_MS - START_TIME_MS))

# Check if request was successful
if [ "$HTTP_CODE" -ne 200 ]; then
    echo ""
    echo "[ERROR] Request failed with HTTP $HTTP_CODE" >&2
    echo "$RESPONSE_BODY" >&2
    echo ""
    echo "Is the backend running?" >&2
    echo "Start it with: npm start" >&2
    echo ""
    exit 1
fi

echo "[OK] Response received in ${DURATION}ms"
echo ""

# Check if jq is available for JSON parsing
if command -v jq &> /dev/null; then
    # Use jq for better JSON parsing
    echo "=========================================="
    echo "RESULTS"
    echo "=========================================="
    echo ""
    
    # Intent Classification
    echo "Intent Classification:"
    INTENT_TYPE=$(echo "$RESPONSE_BODY" | jq -r '.intentClassification.type // "N/A"')
    INTENT=$(echo "$RESPONSE_BODY" | jq -r '.intentClassification.intent // "N/A"')
    CONFIDENCE=$(echo "$RESPONSE_BODY" | jq -r '.intentClassification.confidence // "N/A"')
    EXPLANATION=$(echo "$RESPONSE_BODY" | jq -r '.intentClassification.explanation // "N/A"')
    echo "   Type: $INTENT_TYPE"
    echo "   Intent: $INTENT"
    echo "   Confidence: $CONFIDENCE"
    echo "   Explanation: $EXPLANATION"
    echo ""
    
    # Templates Used
    TEMPLATE_COUNT=$(echo "$RESPONSE_BODY" | jq '.templates | length')
    if [ "$TEMPLATE_COUNT" -gt 0 ]; then
        echo "Templates Used: $TEMPLATE_COUNT"
        echo "$RESPONSE_BODY" | jq -r '.templates[]? | "   • \(.name) (Relevance: \(.relevance), ID: \(.id))"'
        echo ""
    fi
    
    # Agents Used (from procedural tasks)
    UNIQUE_AGENTS=$(echo "$RESPONSE_BODY" | jq -r '[.turnEnvelope.plan.procedural[]?.service] | unique | sort')
    AGENT_COUNT=$(echo "$UNIQUE_AGENTS" | jq 'length')
    TOTAL_TASKS=$(echo "$RESPONSE_BODY" | jq '.turnEnvelope.plan.procedural | length')
    if [ "$AGENT_COUNT" -gt 0 ]; then
        echo "Agents Used: $AGENT_COUNT unique agents ($TOTAL_TASKS total task executions)"
        echo "$UNIQUE_AGENTS" | jq -r '.[]' | sed 's/^/   • /' | sed 's/-/ /g' | sed 's/\b\(.\)/\u\1/g'
        echo ""
    fi
    
    # Turn Envelope - Acknowledgment
    ACK=$(echo "$RESPONSE_BODY" | jq -r '.turnEnvelope.ack // empty')
    if [ -n "$ACK" ] && [ "$ACK" != "null" ]; then
        echo "Acknowledgment:"
        echo "   $ACK"
        echo ""
    fi
    
    # Plan (from turnEnvelope)
    HAS_DECLARATIVE=$(echo "$RESPONSE_BODY" | jq -r '.turnEnvelope.plan.declarative // [] | length')
    HAS_PROCEDURAL=$(echo "$RESPONSE_BODY" | jq -r '.turnEnvelope.plan.procedural // [] | length')
    if [ "$HAS_DECLARATIVE" -gt 0 ] || [ "$HAS_PROCEDURAL" -gt 0 ]; then
        echo "Execution Plan:"
        if [ "$HAS_DECLARATIVE" -gt 0 ]; then
            echo "   Declarative Actions ($HAS_DECLARATIVE):"
            echo "$RESPONSE_BODY" | jq -r '.turnEnvelope.plan.declarative[]? | "      • \(.templateName) (\(.domain), Relevance: \(.relevance))"'
        fi
        if [ "$HAS_PROCEDURAL" -gt 0 ]; then
            echo "   Procedural Tasks ($HAS_PROCEDURAL):"
            echo "$RESPONSE_BODY" | jq -r '.turnEnvelope.plan.procedural[]? | "      • \(.title) [\(.service)] - Deps: \(.deps | join(", ") // "none")"'
        fi
        echo ""
    fi
    
    # Memory (from turnEnvelope)
    MEMORY_RETRIEVED=$(echo "$RESPONSE_BODY" | jq -r '.turnEnvelope.memory.retrieved // 0')
    MEMORY_TURNS=$(echo "$RESPONSE_BODY" | jq -r '.turnEnvelope.memory.conversationTurns // 0')
    if [ "$MEMORY_RETRIEVED" -gt 0 ] || [ "$MEMORY_TURNS" -gt 0 ]; then
        echo "Memory Context:"
        echo "   Retrieved: $MEMORY_RETRIEVED"
        echo "   Conversation Turns: $MEMORY_TURNS"
        echo ""
    fi
    
    # Clarification Questions (ask)
    ASK_COUNT=$(echo "$RESPONSE_BODY" | jq '.turnEnvelope.ask // [] | length')
    if [ "$ASK_COUNT" -gt 0 ]; then
        echo "Clarification Questions:"
        echo "$RESPONSE_BODY" | jq -r '.turnEnvelope.ask[]? | "   • \(.question) (Reason: \(.reason), Confidence: \(.confidence))"'
        echo ""
    fi
    
    # Metadata
    echo "Metadata:"
    TURN_ID=$(echo "$RESPONSE_BODY" | jq -r '.turnEnvelope.meta.provenance // "N/A"')
    CONV_ID_RESP=$(echo "$RESPONSE_BODY" | jq -r '.conversationId // "N/A"')
    PROCESSED_AT=$(echo "$RESPONSE_BODY" | jq -r '.processedAt // "N/A"')
    PROCESSING_MODE=$(echo "$RESPONSE_BODY" | jq -r '.turnEnvelope.meta.processingMode // "N/A"')
    echo "   Conversation ID: $CONV_ID_RESP"
    echo "   Request ID: $(echo "$RESPONSE_BODY" | jq -r '.requestId // "N/A"')"
    echo "   Processed At: $PROCESSED_AT"
    echo "   Processing Mode: $PROCESSING_MODE"
    echo "   Provenance: $TURN_ID"
    echo "   Total Execution Time: ${DURATION}ms"
    echo ""
    
    # Concepts
    CONCEPTS=$(echo "$RESPONSE_BODY" | jq -r '.turnEnvelope.meta.concepts // [] | join(", ")')
    if [ -n "$CONCEPTS" ] && [ "$CONCEPTS" != "" ]; then
        echo "Concepts Detected:"
        echo "   $CONCEPTS"
        echo ""
    fi
    
    echo "=========================================="
    echo ""
    echo "Full Response (JSON):"
    echo "$RESPONSE_BODY" | jq '.' | sed 's/^/   /'
    echo ""
    
else
    # Fallback: just show raw JSON if jq is not available
    echo "=========================================="
    echo "RESULTS (JSON)"
    echo "=========================================="
    echo ""
    echo "$RESPONSE_BODY" | python3 -m json.tool 2>/dev/null || echo "$RESPONSE_BODY"
    echo ""
    echo "Note: Install 'jq' for better formatted output: sudo apt-get install jq"
    echo ""
fi

echo "[OK] Test completed successfully!"

