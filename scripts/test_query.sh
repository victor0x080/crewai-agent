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


