#!/usr/bin/env bash
set -euo pipefail

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
MAGENTA='\033[0;35m'
WHITE='\033[1;37m'
BOLD='\033[1m'
DIM='\033[2m'
NC='\033[0m' # No Color

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

# Color HTTP status
if [ "$HTTP_STATUS" -eq 200 ]; then
  echo -e "${GREEN}✓ HTTP ${HTTP_STATUS}${NC}"
else
  echo -e "${RED}✗ HTTP ${HTTP_STATUS}${NC}"
fi
echo -e "${DIM}Saved response: ${RESP_FILE}${NC}"

if [ "$HAS_JQ" -eq 1 ]; then
  echo -e "\n${BOLD}${CYAN}📊 Confidence Scores:${NC}"
  jq -r --arg green "$GREEN" --arg yellow "$YELLOW" --arg red "$RED" --arg cyan "$CYAN" --arg magenta "$MAGENTA" --arg white "$WHITE" --arg dim "$DIM" --arg nc "$NC" --arg bold "$BOLD" '
    (.agentResults.discovery // {})
    | if .confidenceScores and (.confidenceScores | length > 0) then
        (($bold + "Selected Agents Confidence:" + $nc)),
        (.confidenceScores[] | 
          (if (.confidence // 0) >= 0.72 then $green elif (.confidence // 0) >= 0.5 then $yellow else $red end) +
          "  - \(.agentName // .agentId): \(.confidence // "N/A" | tostring | .[0:5])" + $nc),
        ""
      elif .topConfidenceScores and (.topConfidenceScores | length > 0) then
        (($bold + "Top 5 Agent Confidence Scores:" + $nc)),
        (.topConfidenceScores[] | 
          (if (.confidence // 0) >= 0.72 then $green elif (.confidence // 0) >= 0.5 then $yellow else $red end) +
          "  - \(.agentName // .agentId): \(.confidence | tostring | .[0:5])" + $nc),
        ""
      else
        ("  " + $cyan + "(No confidence scores available)" + $nc)
      end,
    if .threshold then (($cyan + "Threshold: " + $nc) + (.threshold | tostring)), "" else "" end,
    if .maxConfidence then 
      (($cyan + "Max Confidence: " + $nc) + 
       (if .maxConfidence >= 0.72 then $green elif .maxConfidence >= 0.5 then $yellow else $red end) +
       (.maxConfidence | tostring | .[0:5]) + $nc), 
      "" 
    else "" end,
    if .dynamicAgentCreated then
      ("\n" + ($bold + $magenta + "🔧 Dynamic Agent Created:" + $nc)),
      ("  " + $cyan + "Agent ID: " + $nc + (.agentId // "N/A")),
      ("  " + $cyan + "Agent Name: " + $nc + ($white + (.agentSpec.agentName // "N/A") + $nc)),
      ("  " + $cyan + "Role: " + $nc + (.agentSpec.role // "N/A")),
      ("  " + $cyan + "Goal: " + $nc + (.agentSpec.goal // "N/A")),
      ("  " + $cyan + "Capabilities: " + $nc + ($yellow + (.agentSpec.capabilities // [] | join(", ")) + $nc)),
      "",
      ("  " + $bold + $cyan + "Algorithms (" + (.agentSpec.algorithms | length | tostring) + "):" + $nc),
      (.agentSpec.algorithms // [] | .[] | ("    " + $green + "- " + $nc + (.name // "Unknown") + $cyan + ": " + $nc + (.description // ""))),
      "",
      ("  " + $bold + $cyan + "Expected Insights:" + $nc),
      (.agentSpec.expectedInsights // [] | .[] | ("    " + $yellow + "- " + $nc + .)),
      ""
    else "" end
  ' "$RESP_FILE"

  echo -e "\n${BOLD}${BLUE}Agents used:${NC}"
  jq -r --arg green "$GREEN" --arg red "$RED" --arg nc "$NC" '
    def ok(b): if b then ($green + "OK" + $nc) else ($red + "ERR" + $nc) end;
    (.agentResults.results // [])
    | map("  - " + ((.agentName//.agentId)//"-") + " [" + ok(.success) + "] " + $nc + "(taskId: " + ((.taskId//.result.task_id)//"-") + ")")
    | .[]
  ' "$RESP_FILE"

  echo -e "\n${BOLD}${BLUE}Agent results (full outputs):${NC}"
  jq -r --arg green "$GREEN" --arg red "$RED" --arg cyan "$CYAN" --arg white "$WHITE" --arg dim "$DIM" --arg nc "$NC" '
    def ok(b): if b then ($green + "OK" + $nc) else ($red + "ERR" + $nc) end;
    (.agentResults.results // [])
    | .[]
    | ($dim + "────────────────────────────────────────────────────────────────────────────────" + $nc),
      ($cyan + "Agent: " + $nc + ($white + ((.agentName//.agentId)//"-") + $nc)),
      ($cyan + "Status: " + $nc + ok(.success)),
      ($cyan + "TaskId: " + $nc + ((.taskId//.result.task_id)//"-")),
      ($cyan + "Output:" + $nc),
      (
        (.result.output // .result.answer // .result.summary // (.result | tostring) // "-")
      )
  ' "$RESP_FILE"

  echo -e "\n${BOLD}${GREEN}Final response:${NC}"
  jq -r '
    .agentResults.summary.synthesizedAnswer // .response // .conversationalResponse // "-"
  ' "$RESP_FILE"

  echo -e "\n${BOLD}${DIM}Request info:${NC}"
  jq -r '
    {requestId, processedAt, timeout: (.agentResults.timeout // false), numResults: ((.agentResults.results // []) | length)}
  ' "$RESP_FILE"
else
  python3 - <<PY
import json
import sys

# Color codes
RED = '\033[0;31m'
GREEN = '\033[0;32m'
YELLOW = '\033[1;33m'
BLUE = '\033[0;34m'
CYAN = '\033[0;36m'
MAGENTA = '\033[0;35m'
WHITE = '\033[1;37m'
BOLD = '\033[1m'
DIM = '\033[2m'
NC = '\033[0m'

p="/tmp/ims_agent_test_response.json"
try:
  d=json.load(open(p))
except Exception as e:
  print(f"{RED}Failed to read response: {e}{NC}", file=sys.stderr)
  raise SystemExit(0)

results=(d.get("agentResults") or {}).get("results") or []
discovery=(d.get("agentResults") or {}).get("discovery") or {}

print(f"\n{BOLD}{CYAN}📊 Confidence Scores:{NC}")
if discovery.get("confidenceScores"):
  print(f"{BOLD}Selected Agents Confidence:{NC}")
  for cs in discovery["confidenceScores"]:
    name=cs.get("agentName") or cs.get("agentId") or "-"
    conf=cs.get("confidence")
    color = GREEN if conf and conf >= 0.72 else YELLOW if conf and conf >= 0.5 else RED
    print(f"  {color}- {name}: {conf:.3f}{NC}" if conf is not None else f"  - {name}: N/A")
  print()
elif discovery.get("topConfidenceScores"):
  print(f"{BOLD}Top 5 Agent Confidence Scores:{NC}")
  for cs in discovery["topConfidenceScores"]:
    name=cs.get("agentName") or cs.get("agentId") or "-"
    conf=cs.get("confidence")
    color = GREEN if conf and conf >= 0.72 else YELLOW if conf and conf >= 0.5 else RED
    print(f"  {color}- {name}: {conf:.3f}{NC}" if conf is not None else f"  - {name}: N/A")
  print()
else:
  print(f"  {CYAN}(No confidence scores available){NC}")
  print()

if discovery.get("threshold"):
  print(f"{CYAN}Threshold: {discovery['threshold']}{NC}")
  print()

if discovery.get("maxConfidence") is not None:
  max_conf = discovery['maxConfidence']
  color = GREEN if max_conf >= 0.72 else YELLOW if max_conf >= 0.5 else RED
  print(f"{CYAN}Max Confidence: {color}{max_conf:.3f}{NC}")
  print()

# Display dynamic agent information if created
if discovery.get("dynamicAgentCreated"):
  print(f"\n{BOLD}{MAGENTA}🔧 Dynamic Agent Created:{NC}")
  print(f"  {CYAN}Agent ID: {NC}{discovery.get('agentId', 'N/A')}")
  agent_spec = discovery.get("agentSpec", {})
  print(f"  {CYAN}Agent Name: {NC}{WHITE}{agent_spec.get('agentName', 'N/A')}{NC}")
  print(f"  {CYAN}Role: {NC}{agent_spec.get('role', 'N/A')}")
  print(f"  {CYAN}Goal: {NC}{agent_spec.get('goal', 'N/A')}")
  capabilities = agent_spec.get('capabilities', [])
  print(f"  {CYAN}Capabilities: {NC}{YELLOW}{', '.join(capabilities) if capabilities else 'N/A'}{NC}")
  print()
  algorithms = agent_spec.get('algorithms', [])
  print(f"  {BOLD}{CYAN}Algorithms ({len(algorithms)}):{NC}")
  for algo in algorithms:
    print(f"    {GREEN}- {NC}{algo.get('name', 'Unknown')}{CYAN}: {NC}{algo.get('description', '')[:80]}")
  print()
  insights = agent_spec.get('expectedInsights', [])
  if insights:
    print(f"  {BOLD}{CYAN}Expected Insights:{NC}")
    for insight in insights:
      print(f"    {YELLOW}- {NC}{insight}")
    print()

print(f"\n{BOLD}{BLUE}Agents used:{NC}")
for r in results:
  name=r.get("agentName") or r.get("agentId") or "-"
  status=GREEN + "OK" + NC if r.get("success") else RED + "ERR" + NC
  taskId=r.get("taskId") or ((r.get("result") or {}).get("task_id")) or "-"
  print(f"  - {name} [{status}] (taskId: {taskId})")

print(f"\n{BOLD}{BLUE}Agent results (full outputs):{NC}")
for r in results:
  name=r.get("agentName") or r.get("agentId") or "-"
  status=GREEN + "OK" + NC if r.get("success") else RED + "ERR" + NC
  taskId=r.get("taskId") or ((r.get("result") or {}).get("task_id")) or "-"
  out=(r.get("result") or {})
  output = out.get("output") or out.get("answer") or out.get("summary") or json.dumps(out, ensure_ascii=False)
  print(f"{DIM}{'-'*80}{NC}")
  print(f"{CYAN}Agent: {NC}{WHITE}{name}{NC}")
  print(f"{CYAN}Status: {NC}{status}")
  print(f"{CYAN}TaskId: {NC}{taskId}")
  print(f"{CYAN}Output:{NC}")
  print(output)

print(f"\n{BOLD}{GREEN}Final response:{NC}")
resp=(d.get("agentResults") or {}).get("summary",{}).get("synthesizedAnswer") \
     or d.get("response") or d.get("conversationalResponse") or "-"
print(resp)

print(f"\n{BOLD}{DIM}Request info:{NC}")
info={
  "requestId": d.get("requestId"),
  "processedAt": d.get("processedAt"),
  "timeout": (d.get("agentResults") or {}).get("timeout") or False,
  "numResults": len(results)
}
print(json.dumps(info))
PY
fi


