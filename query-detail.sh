#!/bin/bash
# Detailed Query Result Viewer

API_URL="http://localhost:3001"

if [ -z "$1" ]; then
    echo "Usage: $0 '<your query>'"
    echo ""
    echo "Examples:"
    echo "  $0 'What is the sales forecast for next quarter?'"
    echo "  $0 'How should I allocate my marketing budget?'"
    echo "  $0 'What are the inventory risks for product X?'"
    exit 1
fi

QUERY="$1"

echo "=========================================="
echo "  Query: $QUERY"
echo "=========================================="
echo ""

RESPONSE=$(curl -s -X POST "$API_URL/api/process-message" \
    -H "Content-Type: application/json" \
    -d "{
        \"message\": \"$QUERY\",
        \"conversationId\": \"detailed-$(date +%s)\",
        \"context\": {
            \"userId\": \"test-user\",
            \"tenantId\": \"default\"
        },
        \"waitForResults\": true,
        \"maxWaitTime\": 30000
    }")

# Pretty print full JSON
echo "📄 Full JSON Response:"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "$RESPONSE" | python3 -m json.tool 2>/dev/null || echo "$RESPONSE"
echo ""

# Extract and display key sections
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📊 Summary:"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

INTENT=$(echo "$RESPONSE" | python3 -c "import sys, json; d=json.load(sys.stdin); print(d.get('intentClassification', {}).get('intent', 'UNKNOWN'))" 2>/dev/null)
CONFIDENCE=$(echo "$RESPONSE" | python3 -c "import sys, json; d=json.load(sys.stdin); print(d.get('intentClassification', {}).get('confidence', 0))" 2>/dev/null)
TYPE=$(echo "$RESPONSE" | python3 -c "import sys, json; d=json.load(sys.stdin); print(d.get('intentClassification', {}).get('type', 'unknown'))" 2>/dev/null)
EXPLANATION=$(echo "$RESPONSE" | python3 -c "import sys, json; d=json.load(sys.stdin); print(d.get('intentClassification', {}).get('explanation', ''))" 2>/dev/null)

echo "🎯 Intent Classification:"
echo "   Intent: $INTENT"
echo "   Type: $TYPE"
echo "   Confidence: ${CONFIDENCE:-0.0}"
echo "   Explanation: $EXPLANATION"
echo ""

echo "📋 Templates:"
echo "$RESPONSE" | python3 -c "
import sys, json
try:
    d = json.load(sys.stdin)
    templates = d.get('turnEnvelope', {}).get('plan', {}).get('declarative', [])
    print(f'   Found {len(templates)} templates:')
    for i, t in enumerate(templates, 1):
        print(f'   {i}. {t.get(\"templateName\", \"Unknown\")}')
        print(f'      ID: {t.get(\"templateId\", \"N/A\")}')
        print(f'      Domain: {t.get(\"domain\", \"N/A\")}')
        print(f'      Relevance: {t.get(\"relevance\", 0):.2f}')
        print('')
except Exception as e:
    print(f'   Error parsing templates: {e}')
" 2>/dev/null

echo "🤖 Agents Selected:"
echo "$RESPONSE" | python3 -c "
import sys, json
try:
    d = json.load(sys.stdin)
    procs = d.get('turnEnvelope', {}).get('plan', {}).get('procedural', [])
    agents = {}
    for t in procs:
        service = t.get('service', '')
        if service:
            if service not in agents:
                agents[service] = []
            agents[service].append(t.get('title', ''))
    
    print(f'   Total tasks: {len(procs)}')
    print(f'   Unique agents: {len(agents)}')
    print('')
    for agent, tasks in sorted(agents.items()):
        print(f'   • {agent}')
        for task in tasks[:2]:
            print(f'     - {task}')
        if len(tasks) > 2:
            print(f'     ... and {len(tasks) - 2} more tasks')
        print('')
except Exception as e:
    print(f'   Error parsing agents: {e}')
" 2>/dev/null

echo "💬 Response:"
ACK=$(echo "$RESPONSE" | python3 -c "import sys, json; d=json.load(sys.stdin); print(d.get('turnEnvelope', {}).get('ack', ''))" 2>/dev/null)
echo "   $ACK"
echo ""

echo "🤖 Agent Results:"
echo "$RESPONSE" | python3 -c "
import sys, json
try:
    d = json.load(sys.stdin)
    agent_results = d.get('agentResults', {})
    results = agent_results.get('results', [])
    summary = agent_results.get('summary', {})
    timeout = agent_results.get('timeout', False)
    error = agent_results.get('error')
    
    if timeout:
        print('   ⏱️ TIMEOUT: Agents timed out after 30 seconds')
        print(f'   Error: {error or \"No error message\"}')
        print('')
        print('   This usually means:')
        print('   - Agents are not listening to the correct Redis streams')
        print('   - Stream name mismatch between backend and agents')
        print('   - Agents are processing but taking too long')
        print('')
    
    if not results:
        if timeout:
            print('   No agent results available (timeout occurred)')
        else:
            print('   No agent results available')
            print('   Check if waitForResults was set to true')
    else:
        successful = [r for r in results if r.get('success', False)]
        failed = [r for r in results if not r.get('success', False)]
        
        print(f'   Total Agents: {len(results)}')
        print(f'   Successful: {len(successful)}')
        print(f'   Failed: {len(failed)}')
        print('')
        
        if successful:
            print('   ✅ Successful Agents:')
            for i, r in enumerate(successful, 1):
                agent_name = r.get('agentName', r.get('agentId', 'Unknown'))
                mode = r.get('mode', 'unknown')
                output = r.get('result', {}).get('output', 'No output')
                output_preview = output[:200] + '...' if len(output) > 200 else output
                print(f'   {i}. {agent_name} [{mode}]')
                print(f'      Output: {output_preview}')
                print('')
        
        if failed:
            print('   ❌ Failed Agents:')
            for i, r in enumerate(failed, 1):
                agent_name = r.get('agentName', r.get('agentId', 'Unknown'))
                mode = r.get('mode', 'unknown')
                error_msg = r.get('error', 'Unknown error')
                print(f'   {i}. {agent_name} [{mode}]')
                print(f'      Error: {error_msg}')
                print('')
        
        if summary and summary.get('synthesizedAnswer'):
            print('   📝 Synthesized Answer:')
            print(f'      {summary.get(\"synthesizedAnswer\", \"\")[:500]}...')
            print('')
except Exception as e:
    print(f'   Error parsing agent results: {e}')
    import traceback
    traceback.print_exc()
" 2>/dev/null

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

