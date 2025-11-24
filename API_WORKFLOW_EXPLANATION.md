# Complete API Workflow Explanation

## Overview

This document explains the complete workflow when calling the `/api/process-message` endpoint in the IMS Agent Backend. The system processes user queries through multiple stages: intent classification, template discovery, agent orchestration, and response synthesis.

---

## 🔄 Complete Workflow Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│                   1. API REQUEST RECEIVED                          │
│                   POST /api/process-message                         │
│                   { message, conversationId, context }              │
└───────────────────────────────┬─────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────────┐
│                   2. REQUEST VALIDATION                            │
│                   • Validate JSON structure                         │
│                   • Check required fields (message, conversationId) │
│                   • Extract userId, tenantId from context            │
└───────────────────────────────┬─────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────────┐
│             3. INTENT CLASSIFICATION (Step 1)                       │
│             ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━│
│             Service: IntentRouter                                   │
│             • Load prompt from Supabase (or hardcoded fallback)    │
│             • Call OpenAI GPT-4 for classification                │
│             • Timeout: 5 seconds (race condition)                  │
│             • Fallback: Keyword-based classification if timeout    │
│             ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━│
│             Output: {                                              │
│               type: "market-analysis",                             │
│               intent: "QUESTION",                                  │
│               confidence: 0.75,                                     │
│               keywords: ["demand forecast"],                       │
│               entities: {},                                        │
│               category: "market_analysis"                           │
│             }                                                       │
│             Time: ~500-3000ms (or timeout fallback)               │
└───────────────────────────────┬─────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────────┐
│             4. MEMORY RETRIEVAL (Step 2)                            │
│             ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━│
│             Service: MemoryService                                  │
│             • Retrieve conversation history                         │
│             • Get previous query results                            │
│             • Load working memory, short-term, long-term memory    │
│             • Enrich context with past interactions                │
│             ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━│
│             Output: {                                              │
│               workingMemory: [...],                                │
│               shortTermMemory: [...],                               │
│               conversationHistory: [...]                           │
│             }                                                       │
│             Time: ~50-200ms                                         │
└───────────────────────────────┬─────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────────┐
│             5. TEMPLATE DISCOVERY (Step 3)                          │
│             ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━│
│             Service: TemplateEngine                                │
│             • Semantic search in Supabase                           │
│             • Match templates by intent + keywords                 │
│             • Score templates by relevance (0.0-1.0)              │
│             • Return top matching templates                         │
│             ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━│
│             Output: [                                              │
│               {                                                     │
│                 id: "36fe464f-...",                                │
│                 name: "Quick Question Answering",                 │
│                 domain: "general",                                │
│                 relevance: 0.7,                                   │
│                 schema: { agents: ["fqa", "asa"], ... }           │
│               },                                                    │
│               ... (more templates)                                │
│             ]                                                       │
│             Time: ~200-500ms                                        │
└───────────────────────────────┬─────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────────┐
│             6. WAIT FOR RESULTS CHECK (Step 4)                      │
│             ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━│
│             • Check requestData.waitForResults                      │
│             • Default: true (wait for agent results)               │
│             • maxWaitTime: 120000ms (2 minutes) default             │
│             ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━│
│             Decision:                                              │
│             • waitForResults=true  → Execute agents & wait         │
│             • waitForResults=false → Return immediately,           │
│                                       agents run in background     │
└───────────────────────────────┬─────────────────────────────────────┘
                                │
                    ┌───────────┴───────────┐
                    │                       │
          waitForResults=true      waitForResults=false
                    │                       │
                    ▼                       ▼
┌─────────────────────────────────┐  ┌─────────────────────────────────┐
│  7A. AGENT ORCHESTRATION        │  │  7B. BACKGROUND PROCESSING      │
│  (Step 5 - Wait Mode)           │  │  (Step 5 - Background Mode)     │
│  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━│  │  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━│
│  Service: AgentOrchestrator      │  │  • Start orchestration async    │
│                                  │  │  • Return response immediately  │
│  Sub-steps:                      │  │  • Agents run in background    │
│  7A.1 Agent Discovery            │  │  • Results stored in memory     │
│  7A.2 Agent Selection            │  │                                  │
│  7A.3 Agent Execution            │  │  (See 7A for orchestration flow) │
│  7A.4 Result Aggregation          │  │                                  │
│  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━│  │  Time: ~500-3000ms (immediate)  │
│  Time: 5-30 seconds              │  └─────────────────────────────────┘
└───────────┬───────────────────────┘
            │
            ▼
┌─────────────────────────────────────────────────────────────────────┐
│         7A.1 AGENT DISCOVERY (UnifiedAgentDiscoveryService)         │
│         ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━│
│         • Semantic agent discovery with confidence scoring          │
│         • Multi-factor scoring (keywords, intent, capabilities)   │
│         • Threshold: 0.72 (configurable)                           │
│         • If confidence >= 0.72: Use existing agent                │
│         • If confidence < 0.72: Generate dynamic agent spec        │
│         ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━│
│         Output: {                                                  │
│           discovered: [...],      // All agents with scores        │
│           highConfidence: [...],  // Agents >= threshold           │
│           dynamicAgentSpec: {...} // If no high-confidence match  │
│         }                                                           │
└───────────┬─────────────────────────────────────────────────────────┘
            │
            ▼
┌─────────────────────────────────────────────────────────────────────┐
│         7A.2 AGENT SELECTION                                         │
│         ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━│
│         Priority Order:                                              │
│         1. High-confidence agents (from discovery)                  │
│         2. Agents from templates (template.schema.agents)           │
│         3. Default agents (based on intent)                         │
│         4. Dynamic agent creation (if spec available)               │
│         ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━│
│         Example:                                                     │
│         • High-confidence: ["fqa"] (confidence: 0.84)              │
│         • Templates: ["fqa", "asa", "sda", ...]                     │
│         • Selected: ["fqa"] (highest confidence)                    │
└───────────┬─────────────────────────────────────────────────────────┘
            │
            ▼
┌─────────────────────────────────────────────────────────────────────┐
│         7A.3 AGENT EXECUTION                                         │
│         ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━│
│         Service: AgentOrchestrator.executeAgents()                   │
│                                                                      │
│         Decision: Real Agents vs Simulated                          │
│         • Check: crewAIBridge.isHealthy() && Redis available       │
│         • Check: Active agents available                            │
│         • If YES: Execute real Python CrewAI agents via Redis      │
│         • If NO:  Execute simulated agents (fallback)               │
│         ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━│
│                                                                      │
│         ┌────────────────────────────────────────────────────────┐ │
│         │ 7A.3.1 REAL AGENT EXECUTION (via Redis)                │ │
│         │ ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━│ │
│         │ Service: CrewAIBridgeService                            │ │
│         │                                                         │ │
│         │ For each agent:                                         │ │
│         │   1. Create task with unique taskId                     │ │
│         │   2. Build CloudEvent with task details                │ │
│         │   3. Store event in Redis: event:{eventId}              │ │
│         │   4. Publish to Redis Stream:                          │ │
│         │      stream:agent:{agentId}:in                          │ │
│         │   5. Start monitoring output stream:                   │ │
│         │      stream:agent:{agentId}:out                         │ │
│         │   6. Wait for Python agent to consume & execute        │ │
│         │   7. Match response by taskId                           │ │
│         │   8. Return result                                      │ │
│         │                                                         │ │
│         │ Python Agent Side:                                      │ │
│         │   • base_runner.py consumes from input stream           │ │
│         │   • Executes CrewAI agent                               │ │
│         │   • Publishes result to output stream                   │ │
│         │   • Includes taskId for matching                       │ │
│         │                                                         │ │
│         │ Time: 5-30 seconds per agent                           │ │
│         └────────────────────────────────────────────────────────┘ │
│                                                                      │
│         ┌────────────────────────────────────────────────────────┐ │
│         │ 7A.3.2 SIMULATED AGENT EXECUTION (fallback)          │ │
│         │ ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━│ │
│         │ • Used when Redis/agents unavailable                   │ │
│         │ • Returns simulated responses based on agent type      │ │
│         │ • Fast response (~100ms)                              │ │
│         │ • No actual agent execution                            │ │
│         └────────────────────────────────────────────────────────┘ │
└───────────┬─────────────────────────────────────────────────────────┘
            │
            ▼
┌─────────────────────────────────────────────────────────────────────┐
│         7A.4 RESULT AGGREGATION                                      │
│         ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━│
│         • Combine results from all agents                           │
│         • Synthesize final answer                                   │
│         • Calculate metrics (success rate, timing)                  │
│         • Build summary with synthesized answer                      │
│         ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━│
│         Output: {                                                  │
│           agents: ["Forecast Q&A Agent"],                          │
│           results: [{ agentId, success, result, ... }],            │
│           summary: {                                               │
│             synthesizedAnswer: "...",                              │
│             agentsInvolved: 1,                                     │
│             successCount: 1,                                       │
│             processingTime: 50641                                  │
│           },                                                        │
│           metrics: { totalTime, agentsInvolved, successRate },     │
│           discovery: { confidenceScores, ... }                     │
│         }                                                           │
└───────────┬─────────────────────────────────────────────────────────┘
            │
            ▼
┌─────────────────────────────────────────────────────────────────────┐
│         8. STORE RESULTS IN MEMORY (if waitForResults=true)         │
│         ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━│
│         Service: MemoryService.storeExecution()                     │
│         • Store agent results for future context                    │
│         • Add to conversation history                               │
│         • Update working memory                                     │
│         ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━│
│         Time: ~50-100ms                                              │
└───────────┬─────────────────────────────────────────────────────────┘
            │
            ▼
┌─────────────────────────────────────────────────────────────────────┐
│         9. BUILD RESPONSE (Step 6)                                   │
│         ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━│
│         Service: ResponseBuilder                                     │
│                                                                      │
│         Build TurnEnvelope structure:                               │
│         • ack: Acknowledgment message                                │
│         • plan: {                                                    │
│             declarative: [templates],  // What to do               │
│             procedural: [tasks]       // How to do it             │
│           }                                                          │
│         • ask: Clarification questions (if needed)                  │
│         • memory: Memory context                                    │
│         • delta: Agent results (if available)                      │
│         • meta: Metadata (concepts, provenance, etc.)               │
│         ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━│
│         Full Response Structure:                                    │
│         {                                                            │
│           query: "...",                                             │
│           intentClassification: {...},                             │
│           conversationalResponse: "...",                            │
│           response: "...",                                         │
│           turnEnvelope: {...},                                     │
│           agentResults: {...},  // If available                    │
│           processedAt: "...",                                       │
│           requestId: "...",                                         │
│           conversationId: "...",                                   │
│           templates: [...]                                         │
│         }                                                           │
│         ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━│
│         Time: ~10-50ms                                               │
└───────────┬─────────────────────────────────────────────────────────┘
            │
            ▼
┌─────────────────────────────────────────────────────────────────────┐
│         10. SEND HTTP RESPONSE                                       │
│         ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━│
│         • HTTP 200 OK                                                │
│         • Content-Type: application/json                            │
│         • Body: Complete response JSON                              │
│         ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━│
│         Total Time:                                                  │
│         • Immediate mode: 500-3000ms                                │
│         • With agents: 5-30 seconds (or timeout)                     │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 📋 Detailed Step-by-Step Flow

### Step 1: Request Reception & Validation

**Location**: `src/server.js:54-78`

```javascript
// 1. Generate unique request ID
const requestId = `req-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;

// 2. Parse request body
const requestData = JSON.parse(body);

// 3. Validate request structure
const validation = validateProcessMessageRequest(requestData);
// Checks: message (required), conversationId (required), context (optional)

// 4. Extract context
const { message, conversationId, context } = requestData;
const userId = context?.userId || 'anonymous';
const tenantId = context?.tenantId || 'default';
```

**Required Fields**:
- `message`: User query string
- `conversationId`: Unique conversation identifier

**Optional Fields**:
- `context.userId`: User identifier
- `context.tenantId`: Tenant identifier
- `waitForResults`: Boolean (default: true)
- `maxWaitTime`: Number in milliseconds (default: 120000)

---

### Step 2: Intent Classification

**Location**: `src/server.js:92-122`  
**Service**: `IntentRouter.classifyIntent()`

**Process**:
1. Load classification prompt from Supabase (or use fallback)
2. Call OpenAI GPT-4 with user message
3. Parse response: `{ intent, confidence, keywords, entities, category }`
4. Timeout: 5 seconds (race condition)
5. Fallback: Keyword-based classification if timeout

**Output Example**:
```json
{
  "type": "market-analysis",
  "intent": "QUESTION",
  "confidence": 0.75,
  "keywords": ["demand forecast"],
  "entities": {},
  "category": "market_analysis"
}
```

**Time**: ~500-3000ms (or 5s timeout)

---

### Step 3: Memory Retrieval

**Location**: `src/server.js:124-129`  
**Service**: `MemoryService.getContext()`

**Process**:
1. Retrieve conversation history for `conversationId`
2. Get previous query results
3. Load working memory, short-term memory, long-term memory
4. Enrich context with past interactions

**Output**:
```json
{
  "workingMemory": [...],
  "shortTermMemory": [...],
  "conversationHistory": [...]
}
```

**Time**: ~50-200ms

---

### Step 4: Template Discovery

**Location**: `src/server.js:131-143`  
**Service**: `TemplateEngine.discoverTemplates()`

**Process**:
1. Semantic search in Supabase `workflow_templates` table
2. Match templates by:
   - Intent type
   - Keywords
   - Domain category
3. Score templates by relevance (0.0-1.0)
4. Return top matching templates (sorted by relevance)

**Output Example**:
```json
[
  {
    "id": "36fe464f-bc4e-4ebc-a4d1-ea0976ca0ca1",
    "name": "Quick Question Answering",
    "domain": "general",
    "relevance": 0.7,
    "schema": {
      "agents": ["fqa", "asa"],
      "steps": [...]
    }
  },
  ...
]
```

**Time**: ~200-500ms

---

### Step 5: Agent Orchestration (if `waitForResults=true`)

**Location**: `src/server.js:152-211`  
**Service**: `AgentOrchestrator.orchestrate()`

#### 5.1 Agent Discovery

**Service**: `UnifiedAgentDiscoveryService.discoverAndExecuteAgents()`

**Process**:
1. Semantic agent discovery with confidence scoring
2. Multi-factor scoring:
   - Keyword matching
   - Intent alignment
   - Capability matching
   - Entity relevance
   - Domain matching
3. Threshold: 0.72 (configurable)
4. If confidence >= 0.72: Use existing agent
5. If confidence < 0.72: Generate dynamic agent spec (via OpenAI)

**Output**:
```json
{
  "discovered": [
    {
      "id": "fqa",
      "name": "Forecast Q&A Agent",
      "confidence": 0.84,
      "reasons": "keyword_match:2, capability_match:0.18, intent_match:question"
    }
  ],
  "highConfidence": [
    {
      "id": "fqa",
      "name": "Forecast Q&A Agent",
      "confidence": 0.84
    }
  ],
  "dynamicAgentSpec": null  // Only if no high-confidence match
}
```

#### 5.2 Agent Selection

**Priority Order**:
1. **High-confidence agents** (from discovery, confidence >= 0.72)
2. **Template agents** (from `template.schema.agents`)
3. **Default agents** (based on intent type)
4. **Dynamic agent** (if spec generated)

**Example**:
- Discovery found: `fqa` with confidence 0.84
- Templates suggest: `["fqa", "asa", "sda"]`
- **Selected**: `["fqa"]` (highest confidence)

#### 5.3 Agent Execution

**Decision**: Real vs Simulated

**Real Agent Execution** (via Redis):
1. **CrewAIBridgeService.executeAgent()**:
   - Create unique `taskId`
   - Build CloudEvent with task details
   - Store in Redis: `event:{eventId}`
   - Publish to: `stream:agent:{agentId}:in`
   - Monitor: `stream:agent:{agentId}:out`

2. **Python Agent** (`base_runner.py`):
   - Consumes task from Redis stream
   - Executes CrewAI agent
   - Publishes result to output stream
   - Includes `taskId` for matching

3. **Backend**:
   - Monitors output stream
   - Matches response by `taskId`
   - Returns result

**Simulated Agent Execution** (fallback):
- Used when Redis/agents unavailable
- Returns simulated responses
- Fast (~100ms)

**Time**: 5-30 seconds per agent

#### 5.4 Result Aggregation

**Process**:
1. Combine results from all agents
2. Synthesize final answer
3. Calculate metrics
4. Build summary

**Output**:
```json
{
  "agents": ["Forecast Q&A Agent"],
  "results": [
    {
      "agentId": "fqa",
      "agentName": "Forecast Q&A Agent",
      "success": true,
      "result": {
        "output": "...",
        "taskId": "..."
      },
      "executionTime": 50641,
      "mode": "real_python_crewai"
    }
  ],
  "summary": {
    "synthesizedAnswer": "...",
    "agentsInvolved": 1,
    "successCount": 1,
    "processingTime": 50641
  },
  "metrics": {
    "totalTime": 52553,
    "agentsInvolved": 1,
    "successRate": 1
  },
  "discovery": {
    "confidenceScores": [...],
    "threshold": 0.72,
    "maxConfidence": 0.84
  }
}
```

---

### Step 6: Response Building

**Location**: `src/server.js:251-260`  
**Service**: `ResponseBuilder.buildResponse()`

**Process**:
1. Build acknowledgment message
2. Create declarative plan (templates)
3. Create procedural plan (agent tasks)
4. Build clarification questions (if needed)
5. Construct TurnEnvelope structure
6. Include agent results (if available)

**TurnEnvelope Structure**:
```json
{
  "ack": "I'm analyzing your question...",
  "plan": {
    "declarative": [
      {
        "action": "execute_template_...",
        "templateId": "...",
        "templateName": "Quick Question Answering",
        "domain": "general",
        "relevance": 0.7,
        "direction": "user_directed"
      }
    ],
    "procedural": [
      {
        "id": "task-...",
        "title": "Activate fqa for analysis",
        "service": "fqa",
        "capability": "general_analysis",
        "direction": "system_directed",
        "deps": []
      }
    ]
  },
  "ask": [],
  "memory": {
    "workingMemory": [...],
    "retrieved": 0,
    "conversationTurns": 1
  },
  "delta": {
    "agentResults": [...],
    "summary": {...},
    "metrics": {...}
  },
  "meta": {
    "concepts": ["QUESTION", "demand forecast"],
    "provenance": "OpenAI-GPT4",
    "processingMode": "complete_with_results",
    "templatesUsed": [...]
  }
}
```

**Time**: ~10-50ms

---

## 🔀 Execution Modes

### Mode 1: Wait for Results (`waitForResults: true`)

**Flow**:
1. Execute all steps sequentially
2. Wait for agent execution to complete
3. Include agent results in response
4. Store results in memory

**Response Time**: 5-30 seconds (or timeout)

**Response Includes**:
- ✅ Full agent results
- ✅ Synthesized answer
- ✅ Agent execution details
- ✅ Discovery confidence scores

### Mode 2: Background Processing (`waitForResults: false`)

**Flow**:
1. Execute steps 1-4 (intent, memory, templates)
2. Start agent orchestration in background
3. Return response immediately (without agent results)
4. Agents continue processing in background
5. Results stored in memory for future context

**Response Time**: 500-3000ms (immediate)

**Response Includes**:
- ✅ Intent classification
- ✅ Templates discovered
- ✅ Execution plan
- ❌ No agent results (yet)
- ❌ No synthesized answer (yet)

---

## 🎯 Key Decision Points

### 1. Agent Selection Strategy

```
High-confidence agents (>= 0.72)?
  ├─ YES → Use discovered agents
  └─ NO  → Templates available?
            ├─ YES → Use template agents
            └─ NO  → Dynamic agent spec?
                      ├─ YES → Create dynamic agent
                      └─ NO  → Use default agents
```

### 2. Execution Mode

```
Redis available && Agents active?
  ├─ YES → Real Python CrewAI agents (via Redis)
  └─ NO  → Simulated agents (fallback)
```

### 3. Dynamic Agent Creation

```
No high-confidence agents found?
  ├─ YES → Generate dynamic agent spec (OpenAI)
  │         → Create agent via Python factory
  │         → Start runner process
  │         → Execute dynamic agent
  └─ NO  → Use existing agents
```

---

## ⏱️ Timing Breakdown

| Step | Service | Time | Notes |
|------|---------|------|-------|
| 1. Request Validation | Server | <10ms | Fast validation |
| 2. Intent Classification | IntentRouter | 500-3000ms | OpenAI API call (5s timeout) |
| 3. Memory Retrieval | MemoryService | 50-200ms | Supabase query |
| 4. Template Discovery | TemplateEngine | 200-500ms | Supabase semantic search |
| 5. Agent Orchestration | AgentOrchestrator | 5-30s | Depends on agents |
| 5.1 Agent Discovery | UnifiedAgentDiscovery | 100-500ms | Confidence scoring |
| 5.2 Agent Selection | AgentOrchestrator | <10ms | Fast lookup |
| 5.3 Agent Execution | CrewAIBridge | 5-30s per agent | Redis + Python agents |
| 5.4 Result Aggregation | AgentOrchestrator | 50-200ms | Synthesize results |
| 6. Response Building | ResponseBuilder | 10-50ms | Build TurnEnvelope |
| **Total (immediate)** | | **500-3000ms** | Without waiting for agents |
| **Total (with agents)** | | **5-30 seconds** | With agent execution |

---

## 🔧 Services Involved

| Service | Responsibility | Dependencies |
|---------|---------------|--------------|
| **Server** | HTTP request handling, routing | All services |
| **IntentRouter** | Intent classification | OpenAI, PromptService |
| **MemoryService** | Context retrieval & storage | Supabase |
| **TemplateEngine** | Template discovery | Supabase |
| **UnifiedAgentDiscoveryService** | Agent discovery & dynamic creation | OpenAI, AgentRegistry |
| **AgentOrchestrator** | Agent selection & orchestration | CrewAIBridge, DiscoveryService |
| **CrewAIBridgeService** | Redis communication with Python agents | Redis |
| **ResponseBuilder** | Response construction | PromptService |

---

## 📊 Response Structure

The final response includes:

```json
{
  "query": "What is the demand forecast?",
  "intentClassification": {...},
  "conversationalResponse": "...",
  "response": "...",
  "turnEnvelope": {
    "ack": "...",
    "plan": {
      "declarative": [...],
      "procedural": [...]
    },
    "ask": [],
    "memory": {...},
    "delta": {...},
    "meta": {...}
  },
  "agentResults": {
    "agents": [...],
    "results": [...],
    "summary": {...},
    "metrics": {...},
    "discovery": {...}
  },
  "processedAt": "2025-11-13T21:16:16.924Z",
  "requestId": "req-...",
  "conversationId": "test-1",
  "templates": [...]
}
```

---

## 🚨 Error Handling

### Intent Classification Timeout
- **Fallback**: Keyword-based classification
- **Impact**: Lower confidence, but continues processing

### Template Discovery Failure
- **Fallback**: Empty templates array
- **Impact**: Uses default agents based on intent

### Agent Execution Failure
- **Fallback**: Simulated agents (if Redis unavailable)
- **Impact**: Returns simulated responses

### Agent Timeout
- **Behavior**: Returns partial results or timeout flag
- **Impact**: Response includes timeout indicator

---

## 🔍 Debugging Tips

1. **Check logs** for each step:
   ```bash
   tail -f logs/node-backend.log | grep -E "STEP|Classifying|Discovering|Executing"
   ```

2. **Monitor Redis streams**:
   ```bash
   redis-cli XREAD STREAMS stream:agent:fqa:in 0
   redis-cli XREAD STREAMS stream:agent:fqa:out 0
   ```

3. **Check agent health**:
   ```bash
   curl http://localhost:3002/api/health
   ```

4. **Verify agent discovery**:
   - Check `agentResults.discovery.confidenceScores`
   - Verify threshold (default: 0.72)
   - Check if dynamic agent was created

---

This workflow ensures intelligent query processing with fallbacks at every stage, providing reliable responses even when external services are unavailable.

