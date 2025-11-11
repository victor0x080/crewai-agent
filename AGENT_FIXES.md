# Agent Crash Fixes Summary

## Issues Fixed

### 1. ✅ MCO Agents - Missing `fetch_schema` import
- **Problem**: `mco_agents.py` was missing `fetch_schema` import
- **Fix**: Added `fetch_schema` and `fetch_cloudevent` to imports from `tools.redis_streams_tools`

### 2. ✅ Import Path Issues - All Agent Files
- **Problem**: All agent files used `sys.path.append('..')` which doesn't work reliably
- **Fix**: Changed to `sys.path.insert(0, str(Path(__file__).parent.parent))` for reliable imports
- **Files Fixed**:
  - `mco_agents.py` ✅
  - `skill_agents.py` ✅ (already fixed)
  - `extended_skill_agents.py` ✅ (already fixed)
  - `governance_agents.py` ✅ (already fixed)
  - `rmn_agents.py` ✅ (already fixed)

### 3. ✅ RMN Agent Name Mismatches
- **Problem**: `start_all_agents.py` tried to start `amazon_rmn`, `walmart_rmn`, etc., but runners expect `portfolio`, `audience`, `attribution`, `catalog`
- **Fix**: Updated `start_all_agents.py` to use correct runner names

### 4. ✅ Platform Agents
- **Problem**: Platform agents (`google_ads`, `meta_ads`, etc.) don't have runners and were crashing
- **Fix**: Commented out platform agent startup to avoid crashes (they're not yet implemented with runners)

### 5. ✅ Generic Agents - Missing Dependencies
- **Problem**: `data_query_agent.py` needs `pandas` module
- **Fix**: Installing pandas and other dependencies from `requirements.txt`

## Expected Agent Count

**Total Expected**: 54 agents (excluding platform agents which aren't implemented yet)
- Generic: 4 agents
- Skill: 3 agents
- Extended Skill: 4 agents
- Demand-Gen: 4 agents
- Supply Chain: 7 agents
- Governance: 5 agents
- MCO: 20 agents
- Interop: 3 agents
- RMN: 4 agents (portfolio, audience, attribution, catalog)

## Next Steps

1. Restart all agents to apply fixes
2. Verify all agents are sending heartbeats
3. Check Redis for active agent count

## Commands to Restart Agents

```bash
# Stop all agents
pkill -f "start_all_agents.py"

# Start agents again
cd /home/KJB
source venv/bin/activate
export API_URL=http://localhost:3001
python agents/start_all_agents.py > logs/python-agents.log 2> logs/python-agents-error.log &
```

After restart, you should see ~54 agents active (instead of 26).

