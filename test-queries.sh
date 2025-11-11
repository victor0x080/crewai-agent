#!/bin/bash
# Query Test Script - Shows detailed results for different query types

API_URL="http://localhost:3001"

echo "=========================================="
echo "  Query Test Results"
echo "=========================================="
echo ""

# Function to format and display query results
run_query() {
    local query="$1"
    local description="$2"
    
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "📝 Query: $description"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "💬 \"$query\""
    echo ""
    
    RESPONSE=$(curl -s -X POST "$API_URL/api/process-message" \
        -H "Content-Type: application/json" \
        -d "{
            \"message\": \"$query\",
            \"conversationId\": \"test-$(date +%s)\",
            \"context\": {
                \"userId\": \"test-user\",
                \"tenantId\": \"default\"
            }
        }")
    
    # Extract key information
    INTENT=$(echo "$RESPONSE" | python3 -c "import sys, json; d=json.load(sys.stdin); print(d.get('intentClassification', {}).get('intent', 'UNKNOWN'))" 2>/dev/null)
    CONFIDENCE=$(echo "$RESPONSE" | python3 -c "import sys, json; d=json.load(sys.stdin); print(d.get('intentClassification', {}).get('confidence', 0))" 2>/dev/null)
    ACK=$(echo "$RESPONSE" | python3 -c "import sys, json; d=json.load(sys.stdin); print(d.get('turnEnvelope', {}).get('ack', ''))" 2>/dev/null)
    TEMPLATE_COUNT=$(echo "$RESPONSE" | python3 -c "import sys, json; d=json.load(sys.stdin); print(len(d.get('turnEnvelope', {}).get('plan', {}).get('declarative', [])))" 2>/dev/null)
    AGENT_COUNT=$(echo "$RESPONSE" | python3 -c "import sys, json; d=json.load(sys.stdin); procs=d.get('turnEnvelope', {}).get('plan', {}).get('procedural', []); agents=set(); [agents.add(t.get('service', '')) for t in procs]; print(len(agents))" 2>/dev/null)
    
    echo "✅ Intent Classification:"
    echo "   Type: $INTENT"
    echo "   Confidence: ${CONFIDENCE:-0.0}"
    echo ""
    
    echo "📋 Templates Discovered: $TEMPLATE_COUNT"
    echo "$RESPONSE" | python3 -c "
import sys, json
try:
    d = json.load(sys.stdin)
    templates = d.get('turnEnvelope', {}).get('plan', {}).get('declarative', [])
    for i, t in enumerate(templates[:5], 1):
        print(f'   {i}. {t.get(\"templateName\", \"Unknown\")} (relevance: {t.get(\"relevance\", 0):.2f})')
except:
    pass
" 2>/dev/null
    echo ""
    
    echo "🤖 Agents Selected: $AGENT_COUNT"
    echo "$RESPONSE" | python3 -c "
import sys, json
try:
    d = json.load(sys.stdin)
    procs = d.get('turnEnvelope', {}).get('plan', {}).get('procedural', [])
    agents = set()
    for t in procs:
        service = t.get('service', '')
        if service:
            agents.add(service)
    for i, agent in enumerate(sorted(agents)[:10], 1):
        print(f'   {i}. {agent}')
    if len(agents) > 10:
        print(f'   ... and {len(agents) - 10} more')
except:
    pass
" 2>/dev/null
    echo ""
    
    echo "💬 Response:"
    echo "   $ACK" | fold -w 80 -s | sed 's/^/   /'
    echo ""
    echo ""
}

# Test different query types
run_query "What is the sales forecast for next quarter?" "Sales Forecast Query"
run_query "How should I allocate my marketing budget?" "Budget Allocation Query"
run_query "What are the inventory risks for product X?" "Inventory Risk Query"
run_query "Run a scenario simulation for pricing strategy" "Scenario Simulation Query"

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ All queries completed!"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

