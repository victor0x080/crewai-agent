# Generic Agents Heartbeat Fix

## Problem
Generic agents (plan_review, data_query, stream_capture, system_call_zapier) were not sending heartbeats to the Node.js backend, so they weren't counted as "active" agents.

## Solution
Added heartbeat functionality to all 4 generic agents:

1. **data_query_agent.py** ✅
   - Added `send_heartbeat()` function
   - Added heartbeat tracking variables
   - Sends heartbeat every 30 seconds in main loop

2. **plan_review_agent.py** ✅
   - Added `send_heartbeat()` function
   - Added heartbeat tracking variables
   - Sends heartbeat every 30 seconds in main loop

3. **stream_capture_agent.py** ✅
   - Added `send_heartbeat()` function
   - Added heartbeat tracking variables
   - Sends heartbeat in both monitor loops

4. **system_call_zapier_agent.py** ✅
   - Added `send_heartbeat()` function
   - Added heartbeat tracking variables
   - Sends heartbeat every 30 seconds in main loop

## Heartbeat Implementation
Each agent now:
- Imports `os` and `requests` for API calls
- Defines `send_heartbeat(agent_id)` function that POSTs to `/api/managers/{agent_id}/heartbeat`
- Tracks `last_heartbeat` time and sends heartbeat every 30 seconds
- Uses `API_URL` environment variable (defaults to `http://localhost:3001`)

## Agent IDs Used
- `data-query` (from AGENT_REGISTRY_ENTRY['id'])
- `plan-review` (from AGENT_REGISTRY_ENTRY['id'])
- `stream-capture` (from AGENT_REGISTRY_ENTRY['id'])
- `system-call-zapier` (from AGENT_REGISTRY_ENTRY['id'])

## Next Steps
Restart all agents to apply the heartbeat fixes:
```bash
./restart-agents.sh
```

After restart, all 54 agents should be active (currently 45 + 4 generic = 49, but we expect 54 total).

