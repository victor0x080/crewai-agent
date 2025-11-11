# Agent Stream Name Mismatch Issue

## Problem
Backend publishes to: `stream:crewai:tasks:{agentId}`
But agents listen to: `stream:mco:plan:step`, `stream:mco:event:query`, etc.

Result: Tasks are published but no agents pick them up → timeout → successCount: 0

## Root Cause
The architecture expects agents to listen to workflow streams (like `stream:mco:plan:step`), not agent-specific streams. But the backend is using agent-specific streams.

## Solution Options
1. Change backend to publish to `stream:mco:plan:step` for agents that listen to that stream
2. Create adapter agents that listen to `stream:crewai:tasks:*` and forward to `stream:mco:*`
3. Update agents to listen to `stream:crewai:tasks:{agentId}`

## Current Status
- Agents are running and sending heartbeats ✅
- Backend detects agents ✅  
- Tasks are published but not consumed ❌
- Agents timeout after 30 seconds ❌
