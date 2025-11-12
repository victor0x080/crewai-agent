# Dynamic Agent Creation Implementation

## Overview

Complete implementation of dynamic agent creation flow:
1. **UnifiedAgentDiscoveryService.js** - Semantic discovery with confidence scoring (threshold 0.72)
2. **OpenAI Integration** - Generates agent specifications with capabilities
3. **Python Factory** - Creates CrewAI agents from specs
4. **Tool Registry** - Maps capabilities to tools automatically
5. **Agent Registration** - Registers agents in database

## Flow Diagram

```
User Query
    ↓
UnifiedAgentDiscoveryService.semanticAgentDiscovery()
    ↓
Confidence >= 0.72? 
    ├─ YES → Use existing agent
    └─ NO  → generateDynamicAgentConfig()
                ↓
            OpenAI API Call
                ↓
            Generate Spec (capabilities, algorithms, tools)
                ↓
            AgentOrchestrator.createDynamicAgent()
                ↓
            Python: create_dynamic_agent.py
                ↓
            agent_factory.py + tool_registry.py
                ↓
            Create CrewAI Agent
                ↓
            Save Agent Config to Redis/File
                ↓
            AgentOrchestrator.startDynamicAgentRunner()
                ↓
            Start Python Runner Process (dynamic_runner.py)
                ↓
            Runner loads config and listens on Redis stream
                ↓
            AgentOrchestrator.executeAgents() → CrewAIBridgeService
                ↓
            Publish Task to Redis Stream (stream:agent:{agent_id}:in)
                ↓
            Runner picks up task from Redis
                ↓
            Runner executes agent with task
                ↓
            Runner publishes result to Redis (stream:agent:{agent_id}:out)
                ↓
            Node.js receives result from Redis
                ↓
            Return result to user
```

## Key Files

### Node.js Side

**`src/services/UnifiedAgentDiscoveryService.js`**
- `semanticAgentDiscovery()` - Multi-factor confidence scoring (5 factors)
- `generateDynamicAgentConfig()` - Calls OpenAI to generate agent spec
- `_buildAgentSpecPrompt()` - Builds prompt with available capabilities/tools
- `_validateAgentSpec()` - Validates and normalizes OpenAI response

**`src/services/AgentOrchestrator.js`**
- `createDynamicAgent()` - Calls Python factory via subprocess
- `startDynamicAgentRunner()` - Starts Python runner process for dynamic agent
- Handles dynamic agent execution via Redis Streams after creation

### Python Side

**`agents/crewai_python/factory/create_dynamic_agent.py`**
- Entry point called from Node.js
- Creates AgentSpec from JSON spec
- Calls factory._select_tools() which uses tool_registry
- Instantiates CrewAI Agent
- **Saves agent config to Redis** (`dynamic_agent:config:{agent_id}`)
- **Saves agent config to file system** (`/tmp/dynamic_agents/{agent_id}.json`)
- Registers agent in database

**`agents/crewai_python/runners/dynamic_runner.py`** (NEW)
- Generic runner for dynamically created agents
- Loads agent config from Redis/file storage
- Creates CrewAI Agent from config
- Listens on Redis stream: `stream:agent:{agent_id}:in`
- Publishes results to: `stream:agent:{agent_id}:out`
- Runs continuously, processing tasks as they arrive

**`agents/crewai_python/factory/agent_factory.py`**
- `_select_tools()` - Maps capabilities to tools via tool_registry
- Ensures Redis Streams + CloudEvents + Ontology tools are included
- `_register_agent()` - Registers in Supabase

**`agents/crewai_python/factory/tool_registry.py`**
- `get_tools_for_capabilities()` - Maps capabilities to tool functions
- Provides capability vocabulary for OpenAI prompt

## Capabilities → Tools Mapping

The system uses `tool_registry.py` to automatically select tools based on capabilities:

| Capability | Tools Selected |
|-----------|---------------|
| `forecasting` | fetch_demand_forecast_signal, run_simulation_scenario |
| `campaign` | fetch_campaign_performance, publish_platform_action, validate_against_schema |
| `budget_optimization` | publish_platform_action, validate_against_schema, fetch_campaign_performance |
| `attribution` | fetch_campaign_performance, fetch_demand_forecast_signal |
| `elasticity` | fetch_pricing_promo_data, fetch_demand_forecast_signal, run_simulation_scenario |

**All agents automatically get:**
- Redis Streams tools (redis_publish, redis_ack, redis_xreadgroup)
- CloudEvents tools (publish_cloudevent, fetch_cloudevent, validate_against_schema, fetch_schema)
- Ontology tools (resolve_concept, expand_concepts, map_enum, get_category_constraints)

## Example: Marketing Mix Agent Creation

**Query**: "I want to understand the right marketing mix for my marketing"

**Step 1: Discovery**
- No agent found with confidence >= 0.72
- Triggers dynamic creation

**Step 2: OpenAI Spec Generation**
```json
{
  "agentName": "Marketing Mix Modeling Specialist",
  "agentType": "marketing_mix_analyst",
  "capabilities": ["campaign", "budget_optimization", "attribution", "elasticity"],
  "algorithms": [
    {"name": "RobynMMM", "parameters": ["adstock", "saturation"], "outputs": ["ROAS", "CPA"]},
    {"name": "GeoLift", "parameters": ["treatment_geos", "control_geos"], "outputs": ["incremental_lift"]}
  ]
}
```

**Step 3: Python Factory**
- Creates AgentSpec with capabilities
- tool_registry.py maps capabilities to tools:
  - `campaign` → fetch_campaign_performance, publish_platform_action
  - `budget_optimization` → publish_platform_action, validate_against_schema
  - `attribution` → fetch_campaign_performance, fetch_demand_forecast_signal
  - `elasticity` → fetch_pricing_promo_data, fetch_demand_forecast_signal
- Plus all required Redis/CloudEvents/Ontology tools

**Step 4: Agent Creation**
- CrewAI Agent instantiated with selected tools
- Registered in database
- Ready for execution

## Testing

```bash
# Test query that should trigger dynamic creation
./scripts/test_query.sh "I want to understand the right marketing mix for my marketing"

# Check logs for:
# - "🔧 No suitable agents found above threshold"
# - "🤖 Calling OpenAI to generate dynamic agent specification"
# - "✅ Generated dynamic agent spec"
# - "🐍 Calling Python factory to create dynamic agent"
# - "✅ Dynamic agent created successfully"
```

## Configuration

**Environment Variables:**
- `OPENAI_API_KEY` - Required for dynamic agent generation
- `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY` - For agent registration

**Threshold:**
- Default: 0.72 (configurable in UnifiedAgentDiscoveryService constructor)

## Redis Streams Execution Flow

After creating a dynamic agent, the execution follows this pattern:

1. **Agent Config Storage**: Agent configuration is saved to:
   - Redis: `dynamic_agent:config:{agent_id}` (expires after 24 hours)
   - File system: `/tmp/dynamic_agents/{agent_id}.json`

2. **Runner Process**: Node.js spawns a Python runner process:
   ```bash
   python3 agents/crewai_python/runners/dynamic_runner.py {agent_id}
   ```

3. **Redis Streams**:
   - **Input**: `stream:agent:{agent_id}:in` (Node.js → Python)
   - **Output**: `stream:agent:{agent_id}:out` (Python → Node.js)
   - Uses CloudEvents format with `task_id` for correlation

4. **Execution Flow**:
   - Node.js publishes task via `CrewAIBridgeService.executeAgent()`
   - Runner consumes task from input stream
   - Runner executes agent with task
   - Runner publishes result to output stream
   - Node.js receives result and returns to user

## Next Steps

1. **Algorithm Implementation**: Create actual algorithm tools (RobynMMM, GeoLift, etc.) in `analytics_tools.py`
2. **Caching**: Cache created agents to avoid regenerating for similar queries
3. **Multi-Algorithm Execution**: Implement parallel algorithm execution and comparison
4. **Runner Lifecycle Management**: Implement cleanup for unused dynamic agent runners

