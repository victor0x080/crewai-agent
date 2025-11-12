#!/usr/bin/env bash
set -euo pipefail

# Usage:
#   scripts/test_query.sh "<message>" [maxWaitTimeMs] [baseUrl]
# Example:
#   scripts/test_query.sh "How does price elasticity affect weekly sales for SKU electric_car_SKU?" 120000 http://localhost:3001

MESSAGE="${1:-How does price elasticity affect weekly sales for SKU electric_car_SKU?}"
MAX_WAIT_MS="${2:-120000}"
BASE_URL="${3:-http://localhost:3001}"

if ! command -v curl >/dev/null 2>&1; then
  echo "curl is required" >&2
  exit 1
fi

HAS_JQ=0
if command -v jq >/dev/null 2>&1; then
  HAS_JQ=1
fi

if [ "$HAS_JQ" -eq 1 ]; then
  JSON_PAYLOAD=$(jq -n --arg msg "$MESSAGE" --argjson wait "$MAX_WAIT_MS" '{message: $msg, maxWaitTime: $wait}')
else
  # Minimal fallback (unsafe if MESSAGE contains quotes). jq is strongly recommended.
  JSON_PAYLOAD="{\"message\":\"$MESSAGE\",\"maxWaitTime\":$MAX_WAIT_MS}"
fi

RESP_FILE="/tmp/ims_agent_test_response.json"

HTTP_STATUS=$(curl -s -o "$RESP_FILE" -w "%{http_code}" \
  -X POST "$BASE_URL/api/process-message" \
  -H 'Content-Type: application/json' \
  -d "$JSON_PAYLOAD")

echo "HTTP $HTTP_STATUS"
echo "Saved response: $RESP_FILE"

if [ "$HAS_JQ" -eq 1 ]; then
  echo "\n📊 Confidence Scores:"
  jq -r '
    (.agentResults.discovery // {})
    | if .confidenceScores and (.confidenceScores | length > 0) then
        "Selected Agents Confidence:",
        (.confidenceScores[] | "  - \(.agentName // .agentId): \(.confidence // "N/A" | tostring | .[0:5])"),
        ""
      elif .topConfidenceScores and (.topConfidenceScores | length > 0) then
        "Top 5 Agent Confidence Scores:",
        (.topConfidenceScores[] | "  - \(.agentName // .agentId): \(.confidence | tostring | .[0:5])"),
        ""
      else
        "  (No confidence scores available)"
      end,
    if .threshold then "Threshold: \(.threshold)", "" else "" end,
    if .maxConfidence then "Max Confidence: \(.maxConfidence | tostring | .[0:5])", "" else "" end,
    if .dynamicAgentCreated then
      "\n🔧 Dynamic Agent Created:",
      "  Agent ID: \(.agentId // "N/A")",
      "  Agent Name: \(.agentSpec.agentName // "N/A")",
      "  Role: \(.agentSpec.role // "N/A")",
      "  Goal: \(.agentSpec.goal // "N/A")",
      "  Capabilities: \(.agentSpec.capabilities // [] | join(", "))",
      "",
      "  Algorithms (\(.agentSpec.algorithms | length)):",
      (.agentSpec.algorithms // [] | .[] | "    - \(.name): \(.description // "")"),
      "",
      "  Expected Insights:",
      (.agentSpec.expectedInsights // [] | .[] | "    - \(.)"),
      ""
    else "" end
  ' "$RESP_FILE"

  echo "\nAgents used:"
  jq -r '
    def ok(b): if b then "OK" else "ERR" end;
    (.agentResults.results // [])
    | map("  - " + ((.agentName//.agentId)//"-") + " [" + ok(.success) + "] (taskId: " + ((.taskId//.result.task_id)//"-") + ")")
    | .[]
  ' "$RESP_FILE"

  echo "\nAgent results (full outputs):"
  jq -r '
    def ok(b): if b then "OK" else "ERR" end;
    (.agentResults.results // [])
    | .[]
    | "--------------------------------------------------------------------------------",
      "Agent: " + ((.agentName//.agentId)//"-"),
      "Status: " + ok(.success),
      "TaskId: " + ((.taskId//.result.task_id)//"-"),
      "Output:\n" +
        (
          (.result.output // .result.answer // .result.summary // (.result | tostring) // "-")
        )
  ' "$RESP_FILE"

  echo "\nFinal response:"
  jq -r '
    .agentResults.summary.synthesizedAnswer // .response // .conversationalResponse // "-"
  ' "$RESP_FILE"

  echo "\nRequest info:"
  jq -r '
    {requestId, processedAt, timeout: (.agentResults.timeout // false), numResults: ((.agentResults.results // []) | length)}
  ' "$RESP_FILE"
else
  python3 - <<'PY'
import json
p="/tmp/ims_agent_test_response.json"
try:
  d=json.load(open(p))
except Exception as e:
  print("Failed to read response:", e)
  raise SystemExit(0)
results=(d.get("agentResults") or {}).get("results") or []
discovery=(d.get("agentResults") or {}).get("discovery") or {}
print("\n📊 Confidence Scores:")
if discovery.get("confidenceScores"):
  print("Selected Agents Confidence:")
  for cs in discovery["confidenceScores"]:
    name=cs.get("agentName") or cs.get("agentId") or "-"
    conf=cs.get("confidence")
    print(f"  - {name}: {conf:.3f}" if conf is not None else f"  - {name}: N/A")
  print()
elif discovery.get("topConfidenceScores"):
  print("Top 5 Agent Confidence Scores:")
  for cs in discovery["topConfidenceScores"]:
    name=cs.get("agentName") or cs.get("agentId") or "-"
    conf=cs.get("confidence")
    print(f"  - {name}: {conf:.3f}" if conf is not None else f"  - {name}: N/A")
  print()
else:
  print("  (No confidence scores available)")
  print()
if discovery.get("threshold"):
  print(f"Threshold: {discovery['threshold']}")
  print()
if discovery.get("maxConfidence") is not None:
  print(f"Max Confidence: {discovery['maxConfidence']:.3f}")
  print()

# Display dynamic agent information if created
if discovery.get("dynamicAgentCreated"):
  print("\n🔧 Dynamic Agent Created:")
  print(f"  Agent ID: {discovery.get('agentId', 'N/A')}")
  agent_spec = discovery.get("agentSpec", {})
  print(f"  Agent Name: {agent_spec.get('agentName', 'N/A')}")
  print(f"  Role: {agent_spec.get('role', 'N/A')}")
  print(f"  Goal: {agent_spec.get('goal', 'N/A')}")
  capabilities = agent_spec.get('capabilities', [])
  print(f"  Capabilities: {', '.join(capabilities) if capabilities else 'N/A'}")
  print()
  algorithms = agent_spec.get('algorithms', [])
  print(f"  Algorithms ({len(algorithms)}):")
  for algo in algorithms:
    print(f"    - {algo.get('name', 'Unknown')}: {algo.get('description', '')[:80]}")
  print()
  insights = agent_spec.get('expectedInsights', [])
  if insights:
    print("  Expected Insights:")
    for insight in insights:
      print(f"    - {insight}")
    print()

print("\nAgents used:")
for r in results:
  name=r.get("agentName") or r.get("agentId") or "-"
  status="OK" if r.get("success") else "ERR"
  taskId=r.get("taskId") or ((r.get("result") or {}).get("task_id")) or "-"
  print(f"  - {name} [{status}] (taskId: {taskId})")
print("\nAgent results (full outputs):")
for r in results:
  name=r.get("agentName") or r.get("agentId") or "-"
  status="OK" if r.get("success") else "ERR"
  taskId=r.get("taskId") or ((r.get("result") or {}).get("task_id")) or "-"
  out=(r.get("result") or {})
  output = out.get("output") or out.get("answer") or out.get("summary") or json.dumps(out, ensure_ascii=False)
  print("-"*80)
  print(f"Agent: {name}")
  print(f"Status: {status}")
  print(f"TaskId: {taskId}")
  print("Output:")
  print(output)
print("\nFinal response:")
resp=(d.get("agentResults") or {}).get("summary",{}).get("synthesizedAnswer") \
     or d.get("response") or d.get("conversationalResponse") or "-"
print(resp)
print("\nRequest info:")
info={
  "requestId": d.get("requestId"),
  "processedAt": d.get("processedAt"),
  "timeout": (d.get("agentResults") or {}).get("timeout") or False,
  "numResults": len(results)
}
print(json.dumps(info))
PY
fi


