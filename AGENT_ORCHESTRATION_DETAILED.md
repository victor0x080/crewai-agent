# Agent Orchestration Sub-Steps - Detailed Explanation

## Overview

The agent orchestration process consists of 4 main sub-steps that work together to intelligently select and execute the best agents for a given query. This document provides detailed explanations of each sub-step with code examples, algorithms, and flow diagrams.

---

## 🔍 5.1 Agent Discovery - Confidence Scoring

### Purpose

**Agent Discovery** is the first step that evaluates all available agents against the user query to determine which agents are most suitable. It uses a sophisticated multi-factor scoring algorithm to calculate confidence scores (0.0-1.0) for each agent.

### Location

**Service**: `UnifiedAgentDiscoveryService`  
**Method**: `semanticAgentDiscovery()`  
**File**: `src/services/UnifiedAgentDiscoveryService.js`

### Algorithm: Multi-Factor Confidence Scoring

The confidence score is calculated using **4 weighted factors**:

#### Factor 1: Keyword Matching (0-0.45 weight, 45% max)

**Process**:
1. Extract keywords from query (remove stop words, minimum 3 characters)
2. Build agent text corpus: `[id, name, role, capabilities, tools, category]`
3. Match keywords against agent corpus using fuzzy matching
4. Score based on match location and quality

**Scoring Details**:
```javascript
// Exact match in name/role: 0.20 points per keyword
// Exact match in agent ID: 0.15 points per keyword
// Exact match in capabilities/tools: 0.10 points per keyword
// Partial match (4+ chars): 0.60 × base score

// Multi-keyword boost: score × (1 + matchedKeywords × 0.12)
// Domain term boost: score × 1.1 (if domain-specific terms found)

// Maximum: 0.45 (capped)
```

**Example**:
```
Query: "What is the demand forecast?"
Keywords: ["demand", "forecast"]

Agent: "Forecast Q&A Agent" (fqa)
- "forecast" matches name → 0.20
- "demand" matches capabilities → 0.10
- Multi-keyword boost: (0.20 + 0.10) × (1 + 2 × 0.12) = 0.30 × 1.24 = 0.372
- Domain boost: 0.372 × 1.1 = 0.409
- Final keyword score: 0.409 (capped at 0.45)
```

#### Factor 2: Capability Matching (0-0.4 weight, 40% max)

**Process**:
1. Map query keywords to capability categories
2. Check if agent has matching capabilities
3. Score based on capability relevance

**Capability Keywords Mapping**:
```javascript
{
  keywords: ['forecast', 'forecasting', 'demand', 'prediction'],
  caps: ['forecasting', 'demand_prediction', 'pipeline_forecasting']
},
{
  keywords: ['marketing', 'mix', 'mmm', 'media', 'campaign'],
  caps: ['campaign_planning', 'budget_allocation', 'channel_selection']
},
{
  keywords: ['elasticity', 'uplift', 'price', 'pricing'],
  caps: ['price_elasticity', 'promo_uplift', 'elasticity']
},
// ... 8 more categories
```

**Scoring**:
```javascript
// If query keyword matches capability keyword:
//   - Agent has matching capability: +0.15 per match
//   - Multiple matches: cumulative (max 0.4)
//   - Intent alignment bonus: +0.05 if intent matches

// Example:
Query: "demand forecast"
- "forecast" → matches 'forecasting' capability → +0.15
- "demand" → matches 'demand_prediction' capability → +0.15
- Intent: QUESTION → matches forecasting intent → +0.05
- Total capability score: 0.35
```

#### Factor 3: Intent Alignment (0-0.1 weight, 10% max)

**Process**:
1. Check if agent's typical use cases align with query intent
2. Score based on intent type (QUESTION, ANALYSIS, OPTIMIZATION, etc.)

**Scoring**:
```javascript
// Intent type matching:
//   - Perfect match: +0.10
//   - Partial match: +0.05
//   - No match: 0

// Example:
Query intent: "QUESTION"
Agent typical use: "QUESTION" → +0.10
```

#### Factor 4: Entity Relevance (0-0.05 weight, 5% max)

**Process**:
1. Extract entities from query (dates, numbers, categories, etc.)
2. Check if agent can handle those entity types
3. Score based on entity relevance

**Scoring**:
```javascript
// Entity matching:
//   - Agent handles entity type: +0.05
//   - Multiple entities: cumulative (max 0.05)

// Example:
Entities: { period: "Q4 2024", category: "electronics" }
Agent handles: ["period", "category"] → +0.05
```

### Confidence Threshold

**Default Threshold**: `0.72` (72%)

**Meaning**:
- **Confidence >= 0.72**: High-confidence match → Use existing agent
- **Confidence < 0.72**: Low-confidence match → Consider dynamic agent creation

### Output Structure

```javascript
{
  discovered: [
    {
      id: "fqa",
      name: "Forecast Q&A Agent",
      confidence: 0.84,  // Combined score from all factors
      reasons: "keyword_match:2, capability_match:0.18, intent_match:question",
      matchedKeywords: 2,
      category: "skill"
    },
    {
      id: "sda",
      name: "Semantic Data Agent",
      confidence: 0.45,
      reasons: "keyword_match:1, capability_match:0.10",
      matchedKeywords: 1,
      category: "skill"
    }
    // ... more agents
  ],
  highConfidence: [
    {
      id: "fqa",
      name: "Forecast Q&A Agent",
      confidence: 0.84
    }
    // Only agents with confidence >= 0.72
  ],
  dynamicAgentSpec: null  // Only if no high-confidence matches
}
```

### Dynamic Agent Spec Generation

**When Triggered**: No agents have confidence >= 0.72

**Process**:
1. Call OpenAI GPT-4 with query, intent, entities
2. Generate agent specification:
   - Agent name, role, goal
   - Capabilities required
   - Algorithms to use
   - Expected insights
   - Tools needed
3. Return spec for dynamic agent creation

**Example Spec**:
```json
{
  "agentName": "Custom Demand Forecasting Specialist",
  "agentType": "forecasting_analyst",
  "role": "Demand Forecasting Analyst",
  "goal": "Analyze demand patterns and provide accurate forecasts",
  "capabilities": ["demand_prediction", "time_series_analysis"],
  "algorithms": [
    {
      "name": "ARIMA",
      "description": "AutoRegressive Integrated Moving Average"
    }
  ],
  "expectedInsights": [
    "Demand trends over time",
    "Seasonal patterns",
    "Confidence intervals"
  ]
}
```

### Code Flow

```javascript
// 1. Extract query components
const queryLower = query.toLowerCase();
const intentType = intent.intent.toLowerCase();
const queryWords = extractKeywords(query);

// 2. Score each agent
const scored = agentRegistry.map(agent => {
  let confidence = 0;
  
  // Factor 1: Keyword matching (0-0.45)
  const keywordScore = calculateKeywordScore(queryWords, agent);
  confidence += keywordScore;
  
  // Factor 2: Capability matching (0-0.4)
  const capabilityScore = calculateCapabilityScore(queryWords, agent);
  confidence += capabilityScore;
  
  // Factor 3: Intent alignment (0-0.1)
  const intentScore = calculateIntentScore(intent, agent);
  confidence += intentScore;
  
  // Factor 4: Entity relevance (0-0.05)
  const entityScore = calculateEntityScore(entities, agent);
  confidence += entityScore;
  
  return {
    id: agent.id,
    name: agent.name,
    confidence: Math.min(1.0, confidence),  // Cap at 1.0
    reasons: buildReasons(keywordScore, capabilityScore, intentScore, entityScore)
  };
});

// 3. Filter high-confidence agents
const highConfidence = scored.filter(a => a.confidence >= threshold);

// 4. If no high-confidence, generate dynamic spec
if (highConfidence.length === 0) {
  const dynamicAgentSpec = await generateDynamicAgentConfig(query, intent, entities);
  return { discovered: scored, highConfidence: [], dynamicAgentSpec };
}

return { discovered: scored, highConfidence, dynamicAgentSpec: null };
```

---

## 🎯 5.2 Agent Selection - Priority-Based Selection

### Purpose

**Agent Selection** determines which agents to actually execute based on a priority hierarchy. It ensures the most appropriate agents are chosen while maintaining fallback options.

### Location

**Service**: `AgentOrchestrator`  
**Method**: `orchestrate()` → `selectAgents()`  
**File**: `src/services/AgentOrchestrator.js`

### Priority Hierarchy

The selection follows this **strict priority order**:

```
1. High-Confidence Agents (from discovery)
   ↓ (if none found)
2. Template Agents (from workflow templates)
   ↓ (if no templates)
3. Default Agents (based on intent type)
   ↓ (if no defaults)
4. Dynamic Agent Creation (if spec available)
```

### Selection Logic

#### Priority 1: High-Confidence Agents

**Condition**: `discovery.highConfidence.length > 0`

**Process**:
```javascript
if (discovery.highConfidence.length > 0) {
  // Get agent IDs from high-confidence list
  const ids = new Set(discovery.highConfidence.map(a => a.id.toLowerCase()));
  
  // Filter agent registry to get full agent objects
  selectedAgents = agentRegistry.filter(a => ids.has(a.id.toLowerCase()));
  
  logger.info(`🔎 Discovery selected ${selectedAgents.length} high-confidence agent(s)`);
}
```

**Example**:
```
Discovery found:
  - fqa: confidence 0.84 (>= 0.72) ✓
  - sda: confidence 0.45 (< 0.72) ✗

Selected: [fqa]  // Only high-confidence agents
```

#### Priority 2: Template Agents

**Condition**: `highConfidence.length === 0 && templates.length > 0`

**Process**:
```javascript
if (templates && templates.length > 0) {
  // Extract agents from template schemas
  selectedAgents = this.selectAgents(templates, intent);
  
  // selectAgents() method:
  // 1. Extract all agents from template.schema.agents
  // 2. Remove duplicates
  // 3. Filter by intent compatibility
  // 4. Return unique agent list
}
```

**Template Agent Extraction**:
```javascript
selectAgents(templates, intent) {
  const agentIds = new Set();
  
  // Extract agents from each template
  templates.forEach(template => {
    const agents = template.schema?.agents || [];
    agents.forEach(agentId => {
      agentIds.add(agentId.toLowerCase());
    });
  });
  
  // Get full agent objects from registry
  return agentRegistry.filter(a => agentIds.has(a.id.toLowerCase()));
}
```

**Example**:
```
Templates:
  - Template 1: { schema: { agents: ["fqa", "asa"] } }
  - Template 2: { schema: { agents: ["fqa", "sda"] } }

Selected: [fqa, asa, sda]  // All unique agents from templates
```

#### Priority 3: Default Agents

**Condition**: `highConfidence.length === 0 && templates.length === 0`

**Process**:
```javascript
// Map intent to default agents
const defaultAgents = {
  'QUESTION': ['fqa', 'asa'],
  'ANALYSIS': ['sda', 'ssa', 'ira'],
  'OPTIMIZATION': ['opt', 'ssa'],
  'FORECASTING': ['fqa', 'ssa']
};

selectedAgents = agentRegistry.filter(a => 
  defaultAgents[intent.intent]?.includes(a.id.toLowerCase())
);
```

**Example**:
```
Intent: "QUESTION"
Default agents: ["fqa", "asa"]

Selected: [fqa, asa]  // Default agents for QUESTION intent
```

#### Priority 4: Dynamic Agent Creation

**Condition**: `highConfidence.length === 0 && discovery.dynamicAgentSpec !== null`

**Process**:
```javascript
if (discovery.dynamicAgentSpec) {
  // Skip template/default selection
  selectedAgents = [];  // Clear to trigger dynamic creation
  
  // Will be handled in Step 5.3
  logger.info('🔧 Dynamic agent spec available - skipping templates/defaults');
}
```

**Note**: Dynamic agent creation happens **after** selection, in the execution phase.

### Selection Decision Tree

```
┌─────────────────────────────────────┐
│   Agent Discovery Results           │
└──────────────┬──────────────────────┘
               │
       ┌───────┴────────┐
       │                │
highConfidence > 0?   dynamicAgentSpec?
       │                │
   YES │                │ YES
       │                │
       ▼                ▼
┌──────────────┐  ┌──────────────────┐
│ Use High-    │  │ Skip to Dynamic  │
│ Confidence   │  │ Agent Creation   │
│ Agents       │  │ (Step 5.3)       │
└──────────────┘  └──────────────────┘
       │
    NO │
       │
       ▼
┌─────────────────────┐
│ Templates Available?│
└──────────┬──────────┘
           │
      YES  │  NO
           │   │
           ▼   ▼
    ┌──────────┐  ┌──────────────┐
    │ Use      │  │ Use Default   │
    │ Template │  │ Agents        │
    │ Agents   │  │ (by intent)   │
    └──────────┘  └──────────────┘
```

### Code Flow

```javascript
async orchestrate(params) {
  const { query, intent, templates, ... } = params;
  
  // STEP 1: Agent Discovery
  const discovery = await this.discoveryService.discoverAndExecuteAgents(
    query, intent, entities, templates
  );
  
  // STEP 2: Agent Selection (Priority-based)
  let selectedAgents = [];
  
  if (discovery.highConfidence.length > 0) {
    // Priority 1: High-confidence agents
    const ids = new Set(discovery.highConfidence.map(a => a.id.toLowerCase()));
    selectedAgents = agentRegistry.filter(a => ids.has(a.id));
    
  } else if (discovery.dynamicAgentSpec) {
    // Priority 4: Dynamic agent (skip templates/defaults)
    selectedAgents = [];
    
  } else if (templates && templates.length > 0) {
    // Priority 2: Template agents
    selectedAgents = this.selectAgents(templates, intent);
    
  } else {
    // Priority 3: Default agents
    selectedAgents = this.getDefaultAgents(intent);
  }
  
  // Continue to execution...
}
```

---

## ⚙️ 5.3 Agent Execution - Real vs Simulated

### Purpose

**Agent Execution** runs the selected agents and collects their results. It supports two execution modes: **Real Python CrewAI agents** (via Redis) and **Simulated agents** (fallback).

### Location

**Service**: `AgentOrchestrator`  
**Method**: `executeAgents()`  
**File**: `src/services/AgentOrchestrator.js`

### Execution Mode Decision

```javascript
// Check if real agents are available
const useRealAgents = 
  this.crewAIBridge.isHealthy() &&  // Redis connected
  this.crewAIBridge.hasActiveAgents();  // Agents listening

if (useRealAgents) {
  return await this.executeRealAgents(agents, params);
} else {
  return await this.executeSimulatedAgents(agents, params);
}
```

### Mode 1: Real Agent Execution (via Redis)

**Service**: `CrewAIBridgeService.executeAgent()`

#### Step 1: Create Task

```javascript
const taskId = uuidv4();  // Unique task identifier
const streamName = `stream:agent:${agentId}:in`;  // Input stream for agent
```

#### Step 2: Build CloudEvent

```javascript
const cloudevent = {
  specversion: '1.0',
  id: eventId,
  type: 'crewai.task.request',
  source: `urn:nodejs-backend:${process.pid}`,
  subject: agentId,
  time: new Date().toISOString(),
  data: {
    task_id: taskId,  // Critical for matching response
    agent_id: agentId,
    task_description: task.description,
    inputs: task.inputs || {},
    priority: 'medium',
    timestamp: new Date().toISOString()
  }
};
```

#### Step 3: Publish to Redis Stream

```javascript
// Store full event in Redis
await this.redis.set(`event:${eventId}`, JSON.stringify(cloudevent));

// Add pointer to input stream
await this.redis.xAdd(streamName, '*', {
  event_id: eventId,
  type: cloudevent.type,
  subject: cloudevent.subject
});
```

#### Step 4: Monitor Output Stream

```javascript
// Start monitoring agent's output stream
this.monitorAgentOutputStreams(agentId, taskId, timeout);

// Output stream: stream:agent:{agentId}:out
// Python agent publishes results here
```

#### Step 5: Python Agent Execution

**Python Side** (`base_runner.py`):

```python
# 1. Consume task from Redis stream
msgs = consume_stream(input_stream, group, name)
event = msg['event']  # Full CloudEvent

# 2. Extract task details
task_id = event['data']['task_id']
task_description = event['data']['task_description']

# 3. Execute CrewAI agent
result = crew.kickoff(inputs={'query': task_description})

# 4. Publish result to output stream
publish_cloudevent(
    output_stream,  # stream:agent:{agentId}:out
    'crewai.task.response',
    source,
    {
        'result': str(result),
        'task_id': task_id,  # Critical for matching!
        'status': 'success'
    }
)
```

#### Step 6: Match Response

**Backend Side**:

```javascript
async monitorAgentOutputStreams(agentId, taskId, timeout) {
  const outputStream = `stream:agent:${agentId}:out`;
  
  // Read from output stream
  const messages = await this.redis.xRead([{
    key: outputStream,
    id: lastReadId
  }], { COUNT: 10, BLOCK: 100 });
  
  // For each message
  for (const message of messages) {
    const eventId = message.event_id;
    const eventData = JSON.parse(await this.redis.get(`event:${eventId}`));
    
    // Match by task_id
    if (eventData.data.task_id === taskId) {
      // Found matching response!
      this.pendingTasks.get(taskId).resolve({
        success: true,
        result: eventData.data.result
      });
      return;
    }
  }
}
```

#### Execution Flow Diagram

```
┌─────────────────────────────────────────────────────────┐
│ Node.js Backend                                         │
│ 1. Create taskId                                        │
│ 2. Build CloudEvent                                     │
│ 3. Store in Redis: event:{eventId}                      │
│ 4. Publish to: stream:agent:{agentId}:in                │
│ 5. Monitor: stream:agent:{agentId}:out                 │
└──────────────────┬──────────────────────────────────────┘
                   │
                   │ Redis Stream
                   │
                   ▼
┌─────────────────────────────────────────────────────────┐
│ Python Agent (base_runner.py)                           │
│ 1. Consume from: stream:agent:{agentId}:in              │
│ 2. Load event: event:{eventId}                          │
│ 3. Extract task_id                                      │
│ 4. Execute CrewAI agent                                 │
│ 5. Publish to: stream:agent:{agentId}:out               │
│    - Include task_id for matching                       │
└──────────────────┬──────────────────────────────────────┘
                   │
                   │ Redis Stream
                   │
                   ▼
┌─────────────────────────────────────────────────────────┐
│ Node.js Backend                                         │
│ 1. Read from: stream:agent:{agentId}:out                │
│ 2. Load event: event:{eventId}                         │
│ 3. Match by task_id                                     │
│ 4. Resolve promise with result                          │
└─────────────────────────────────────────────────────────┘
```

### Mode 2: Simulated Agent Execution (Fallback)

**When Used**: Redis unavailable or no active agents

**Process**:
```javascript
async executeSimulatedAgents(agents, params) {
  return await Promise.all(agents.map(async (agent) => {
    // Simulate processing time
    await new Promise(resolve => setTimeout(resolve, 500 + Math.random() * 1000));
    
    // Generate agent-specific simulated response
    const simulatedOutput = this.simulateAgentExecution(agent, query, intent, context);
    
    return {
      agentId: agent.id,
      agentName: agent.name,
      success: true,
      result: {
        output: `[SIMULATED] ${simulatedOutput}`,
        confidence: 0.7 + Math.random() * 0.2
      },
      executionTime: 500 + Math.random() * 1000,
      mode: 'simulated'
    };
  }));
}
```

**Simulated Responses by Agent Type**:

```javascript
// Forecast Q&A Agent (fqa)
"Based on historical trends and current market indicators, 
 the forecast shows moderate growth potential..."

// Semantic Data Agent (sda)
"Semantic analysis of the query reveals key entities: 
 {entities}. Data retrieval suggests relevant datasets..."

// Scenario Simulator Agent (ssa)
"Scenario simulation indicates multiple possible outcomes.
 Best case: positive trend with 15-20% growth..."

// ... agent-specific responses
```

### Dynamic Agent Execution

**When**: Dynamic agent was created (from Step 5.1)

**Process**:
```javascript
// 1. Create dynamic agent via Python factory
const agentCreationResult = await this.createDynamicAgent(discovery.dynamicAgentSpec);
// Returns: { agent_id, agent_name, capabilities, ... }

// 2. Start runner process
const runnerResult = await this.startDynamicAgentRunner(agentCreationResult.agent_id);
// Spawns: python3 dynamic_runner.py {agent_id}

// 3. Wait for runner to initialize
await new Promise(resolve => setTimeout(resolve, 2000));

// 4. Execute via Redis (same as real agents)
const dynamicAgent = {
  id: agentCreationResult.agent_id,
  name: agentCreationResult.agent_name,
  capabilities: agentCreationResult.capabilities
};

const agentResults = await this.executeAgents([dynamicAgent], params);
```

**Dynamic Agent Creation Flow**:

```
┌─────────────────────────────────────────────────────────┐
│ Node.js: createDynamicAgent()                          │
│ 1. Call Python factory: create_dynamic_agent.py      │
│ 2. Pass agent spec (from OpenAI)                       │
└──────────────────┬──────────────────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────────────────┐
│ Python Factory                                           │
│ 1. Parse agent spec                                      │
│ 2. Create AgentSpec object                              │
│ 3. Select tools from registry                           │
│ 4. Generate algorithms                                  │
│ 5. Create CrewAI Agent instance                        │
│ 6. Save config to Redis: dynamic_agent:config:{id}      │
│ 7. Return agent_id, agent_name                          │
└──────────────────┬──────────────────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────────────────┐
│ Node.js: startDynamicAgentRunner()                     │
│ 1. Spawn: python3 dynamic_runner.py {agent_id}         │
│ 2. Runner loads config from Redis                       │
│ 3. Runner connects to Redis streams                     │
│ 4. Runner ready to receive tasks                        │
└──────────────────┬──────────────────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────────────────┐
│ Execute via Redis (same as real agents)                │
│ 1. Publish task to stream:agent:{dynamic_id}:in         │
│ 2. Dynamic runner consumes and executes                 │
│ 3. Publish result to stream:agent:{dynamic_id}:out       │
│ 4. Backend matches and returns result                   │
└─────────────────────────────────────────────────────────┘
```

### Execution Result Structure

```javascript
{
  agentId: "fqa",
  agentName: "Forecast Q&A Agent",
  success: true,
  result: {
    output: "A demand forecast is an estimate...",
    agent: "fqa",
    eventId: "3cdb04e2-...",
    taskId: "4b37c896-..."
  },
  executionTime: 50641,  // milliseconds
  mode: "real_python_crewai"  // or "simulated"
}
```

---

## 📊 5.4 Result Aggregation - Combining & Synthesizing

### Purpose

**Result Aggregation** combines results from multiple agents into a unified response. It synthesizes a final answer, calculates metrics, and structures the output for the API response.

### Location

**Service**: `AgentOrchestrator`  
**Method**: `aggregateResults()` → `synthesizeAnswer()`  
**File**: `src/services/AgentOrchestrator.js`

### Aggregation Process

#### Step 1: Filter Successful Results

```javascript
const successful = agentResults.filter(r => r.success);
const failed = agentResults.filter(r => !r.success);
```

#### Step 2: Calculate Metrics

```javascript
const metrics = {
  agentsInvolved: agentResults.length,
  successCount: successful.length,
  failureCount: failed.length,
  averageConfidence: successful.reduce((sum, r) => 
    sum + (r.result?.confidence || 0), 0
  ) / successful.length || 0,
  processingTime: agentResults.reduce((sum, r) => 
    sum + r.executionTime, 0
  )
};
```

#### Step 3: Extract Outputs

```javascript
const outputs = successful.map(r => ({
  agent: r.agentName,
  output: r.result?.output || r.result?.answer || r.result?.summary,
  confidence: r.result?.confidence
}));
```

#### Step 4: Synthesize Final Answer

```javascript
synthesizeAnswer(successfulResults, query) {
  if (successfulResults.length === 0) {
    return 'Unable to generate insights at this time.';
  }

  const outputs = successfulResults
    .map(r => r.result?.output)
    .filter(Boolean);
  
  // Simple synthesis (in production, would use ASA - Answer Synthesis Agent)
  return `Based on analysis from ${successfulResults.length} agents, 
          here are the insights for "${query.slice(0, 60)}...":\n\n` +
         outputs.map((o, i) => `${i + 1}. ${o}`).join('\n\n');
}
```

### Aggregation Output Structure

```javascript
{
  query: "What is the demand forecast?",
  intent: "QUESTION",
  agentsInvolved: 1,
  successCount: 1,
  failureCount: 0,
  averageConfidence: 0.84,
  outputs: [
    {
      agent: "Forecast Q&A Agent",
      output: "A demand forecast is an estimate...",
      confidence: 0.84
    }
  ],
  synthesizedAnswer: "Based on analysis from 1 agents, 
    here are the insights for \"What is the demand forecast?...\":\n\n
    1. A demand forecast is an estimate...",
  processingTime: 50641
}
```

### Multi-Agent Aggregation Example

**Input** (3 agents executed):
```javascript
[
  {
    agentName: "Forecast Q&A Agent",
    success: true,
    result: { output: "Demand forecast shows 15% growth..." }
  },
  {
    agentName: "Semantic Data Agent",
    success: true,
    result: { output: "Relevant data sources identified..." }
  },
  {
    agentName: "Scenario Simulator Agent",
    success: false,
    error: "Timeout"
  }
]
```

**Output**:
```javascript
{
  agentsInvolved: 3,
  successCount: 2,
  failureCount: 1,
  outputs: [
    { agent: "Forecast Q&A Agent", output: "Demand forecast shows 15% growth..." },
    { agent: "Semantic Data Agent", output: "Relevant data sources identified..." }
  ],
  synthesizedAnswer: "Based on analysis from 2 agents, 
    here are the insights for \"What is the demand forecast?...\":\n\n
    1. Demand forecast shows 15% growth...\n\n
    2. Relevant data sources identified..."
}
```

### Final Orchestration Response

The aggregated results are combined with discovery metadata:

```javascript
{
  agents: ["Forecast Q&A Agent"],
  results: [
    {
      agentId: "fqa",
      agentName: "Forecast Q&A Agent",
      success: true,
      result: { ... },
      executionTime: 50641,
      mode: "real_python_crewai"
    }
  ],
  summary: {
    query: "...",
    intent: "QUESTION",
    agentsInvolved: 1,
    successCount: 1,
    synthesizedAnswer: "...",
    processingTime: 50641
  },
  metrics: {
    totalTime: 52553,
    agentsInvolved: 1,
    successRate: 1.0
  },
  discovery: {
    used: true,
    highConfidence: [...],
    confidenceScores: [
      { agentId: "fqa", agentName: "Forecast Q&A Agent", confidence: 0.84 }
    ],
    threshold: 0.72,
    maxConfidence: 0.84
  }
}
```

---

## 🔄 Complete Flow Example

### Example Query: "What is the demand forecast?"

#### Step 5.1: Agent Discovery

```
Input: query="What is the demand forecast?", intent="QUESTION"

Discovery Results:
  - fqa: confidence 0.84 (>= 0.72) ✓ HIGH CONFIDENCE
  - sda: confidence 0.45 (< 0.72) ✗
  - asa: confidence 0.30 (< 0.72) ✗

Output:
  highConfidence: [{ id: "fqa", name: "Forecast Q&A Agent", confidence: 0.84 }]
  dynamicAgentSpec: null
```

#### Step 5.2: Agent Selection

```
Priority Check:
  1. High-confidence agents? YES → [fqa]
  2. Skip templates/defaults

Selected: [fqa]
```

#### Step 5.3: Agent Execution

```
Mode: Real agents (Redis available)

Execution:
  1. Create taskId: "4b37c896-..."
  2. Publish to: stream:agent:fqa:in
  3. Python agent consumes and executes
  4. Python agent publishes to: stream:agent:fqa:out
  5. Backend matches by taskId
  6. Return result

Result:
  {
    agentId: "fqa",
    success: true,
    result: { output: "A demand forecast is..." },
    executionTime: 50641ms
  }
```

#### Step 5.4: Result Aggregation

```
Input: 1 successful result

Aggregation:
  - agentsInvolved: 1
  - successCount: 1
  - synthesizedAnswer: "Based on analysis from 1 agents..."

Output:
  {
    summary: { synthesizedAnswer: "...", ... },
    metrics: { totalTime: 52553, successRate: 1.0 },
    discovery: { confidenceScores: [{ agentId: "fqa", confidence: 0.84 }] }
  }
```

---

## 📈 Performance Characteristics

| Step | Time | Notes |
|------|------|-------|
| 5.1 Agent Discovery | 100-500ms | Confidence scoring (CPU-bound) |
| 5.2 Agent Selection | <10ms | Fast lookup |
| 5.3 Agent Execution | 5-30s per agent | Redis + Python CrewAI |
| 5.4 Result Aggregation | 50-200ms | Synthesize results |

**Total Orchestration Time**: 5-30 seconds (depending on agent execution time)

---

## 🎯 Key Takeaways

1. **Discovery uses multi-factor scoring** (keywords, capabilities, intent, entities)
2. **Selection follows strict priority** (high-confidence → templates → defaults → dynamic)
3. **Execution supports two modes** (real Python agents via Redis, or simulated fallback)
4. **Aggregation combines results** into unified response with metrics

The orchestration system ensures intelligent agent selection while maintaining reliability through fallbacks at every step.

