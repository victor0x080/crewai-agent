#!/bin/bash
# Detailed Query Results Analyzer

echo "========================================="
echo "  Detailed Query Results Analysis"
echo "========================================="
echo ""

queries=(
    "What is the sales forecast for next quarter?"
    "How should I allocate my marketing budget?"
    "What are the inventory risks for product X?"
    "Run a scenario simulation for pricing strategy"
)

for i in "${!queries[@]}"; do
    query="${queries[$i]}"
    echo "Query $((i+1)): \"$query\""
    echo "----------------------------------------"
    
    response=$(curl -s -X POST "http://localhost:3001/api/process-message" \
        -H "Content-Type: application/json" \
        -d "{\"message\": \"$query\", \"conversationId\": \"analysis-$(date +%s)\"}" 2>/dev/null)
    
    # Extract key information
    intent=$(echo "$response" | python3 -c "import sys, json; d=json.load(sys.stdin); print(d.get('intentClassification', {}).get('intent', 'N/A'))" 2>/dev/null)
    confidence=$(echo "$response" | python3 -c "import sys, json; d=json.load(sys.stdin); print(d.get('intentClassification', {}).get('confidence', 0))" 2>/dev/null)
    templates=$(echo "$response" | python3 -c "import sys, json; d=json.load(sys.stdin); [print(f\"  - {t['templateName']} (relevance: {t['relevance']})\") for t in d.get('turnEnvelope', {}).get('plan', {}).get('declarative', [])]" 2>/dev/null)
    agents=$(echo "$response" | python3 -c "import sys, json; d=json.load(sys.stdin); agents=[t['service'] for t in d.get('turnEnvelope', {}).get('plan', {}).get('procedural', [])]; print(', '.join(set(agents)) if agents else 'None')" 2>/dev/null)
    
    echo "Intent: $intent"
    echo "Confidence: $confidence"
    echo ""
    echo "Templates Discovered:"
    echo "$templates"
    echo ""
    echo "Agents Selected: $agents"
    echo ""
    echo "Full Response Preview:"
    echo "$response" | python3 -m json.tool | head -40
    echo ""
    echo "========================================="
    echo ""
    
    sleep 1
done

