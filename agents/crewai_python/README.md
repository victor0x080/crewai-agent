# Python CrewAI Agents - Complete Rewrite

## Overview
All 32 agents rewritten as **Python CrewAI framework** agents following Redis Streams + CloudEvents pattern.

## Architecture

### Agents (32 Total)

**Skill Agents (11):**
1. SDA - Semantic Data Agent
2. FQA - Forecast Q&A Agent (coupled with DemandForecastSignalAgent)
3. CAA - Causal & Attribution Agent
4. SSA - Scenario Simulator Agent
5. IRA - Inventory Risk Agent
6. OPT - Optimizer Agent
7. ASA - Answer Synthesis Agent
8. Marketing Plan Agent
9. Sales Pipeline Agent
10. Elasticity & Uplift Agent
11. Campaign→SKU Mapper Agent

**MCO Agents (21):**
12-32. Full MCO pipeline (Ingress, Catalog, Feature, Attribution, Opportunity, Cost, Budget, Bid, Creative, Platform, QRP, Validator, Router, Guardrail, Safeguard, Gap, Policy, Experiment, RCA, Triage, Translator)

### Components

```
crewai_python/
├── tools/
│   └── redis_streams_tools.py      # CloudEvents pub/sub tools
├── agents/
│   ├── skill_agents.py             # 11 skill agents
│   └── mco_agents.py               # 21 MCO agents
├── crews/
│   └── orchestration.py            # Multi-agent crews
├── runners/
│   ├── skill_runners.py            # Skill agent runners
│   └── mco_runners.py              # MCO agent runners
├── base_runner.py                  # Base consumer loop
├── start_all.py                    # Start all agents
└── requirements.txt
```

## Installation

```bash
cd src/agents/crewai_python
pip install -r requirements.txt
```

## Usage

### Start All Agents
```bash
python start_all.py
```

### Start Individual Agent
```bash
# Skill agents
python runners/skill_runners.py sda
python runners/skill_runners.py fqa

# MCO agents
python runners/mco_runners.py ingress
python runners/mco_runners.py translator
```

## Redis Streams Pattern

Each agent:
1. **Consumes** from input stream via consumer group
2. **Processes** event through CrewAI Task
3. **Publishes** result as CloudEvent to output stream
4. **Acks** original message (or sends to DLQ on failure)

### Example Flow
```
stream:mco:plan:step → [SDA Agent] → stream:mco:event:observation
```

## CloudEvents Compliance

All events follow CloudEvents 1.0:
- Stored in RedisJSON at `event:{id}`
- Stream contains pointer with metadata
- Validated against JSON Schema

## Tools

Agents use these CrewAI tools:
- `publish_cloudevent` - Publish to stream
- `fetch_cloudevent` - Retrieve event by ID
- `fetch_schema` - Get JSON Schema from registry
- `validate_against_schema` - Validate data

## Orchestration

### Sequential Crew (Query→Answer)
```python
from crews.orchestration import query_answer_crew
# QRP → SDA → FQA → CAA → SSA → IRA → OPT → ASA
```

### Hierarchical Crew (Full MCO)
```python
from crews.orchestration import mco_pipeline_crew
# QRP as manager, delegates to 21 agents
```

## Migration from TypeScript

This replaces all TypeScript `BaseCrewAIAgent` classes with true Python CrewAI framework agents.

**Key Differences:**
- ✅ True `Agent`, `Task`, `Crew` from CrewAI
- ✅ Python-based LLM integration
- ✅ Same Redis Streams + CloudEvents pattern
- ✅ Same stream keys and schemas

**Compatibility:**
- Can run alongside TypeScript agents
- Uses same Redis instance
- Same event schemas

## Monitoring

Check consumer groups:
```bash
redis-cli XINFO GROUPS stream:mco:plan:step
redis-cli XPENDING stream:mco:plan:step sda-semantic-data
```

Check DLQ:
```bash
redis-cli XLEN stream:dlq
redis-cli XRANGE stream:dlq - + COUNT 10
```

## Next Steps

1. Test individual agents
2. Validate event schemas
3. Monitor DLQ for errors
4. Tune LLM prompts per agent
5. Add agent-specific tools
6. Implement full Crew workflows
