# IMS Agent Workflow Backend

Clean, production-ready backend implementing the IMS agent workflow system.

## 🏗️ Architecture

```
User Query
    ↓
[Intent Classification] → OpenAI GPT-4
    ↓
[Template Discovery] → Supabase Semantic Search
    ↓
[Agent Orchestration] → CrewAI Python Agents (via Redis/HTTP)
    ↓
[Response Synthesis] → Structured TurnEnvelope
    ↓
Frontend UI
```

## 📦 Components

### 1. **Intent Router** (`src/services/IntentRouter.js`)
- Classifies user intent (ANALYSIS, ACTION, QUESTION, etc.)
- Uses OpenAI GPT-4 for natural language understanding
- Fast response (<3s timeout)

### 2. **Template Engine** (`src/services/TemplateEngine.js`)
- Discovers relevant workflow templates from Supabase
- Semantic search based on intent and keywords
- Template-driven agent orchestration

### 3. **Agent Orchestrator** (`src/services/AgentOrchestrator.js`)
- Manages 55 CrewAI Python agents
- Publishes tasks to Redis Streams (CloudEvents format)
- Handles agent responses and aggregation

### 4. **Memory Service** (`src/services/MemoryService.js`)
- Hierarchical memory (working, short-term, long-term)
- Context enrichment for conversations
- Decision history tracking

### 5. **Response Builder** (`src/services/ResponseBuilder.js`)
- Constructs TurnEnvelope responses
- ACT-R compatible format
- Includes ack, plan, ask, memory, decisions

## 🚀 Quick Start

### Prerequisites
- Node.js 18+
- OpenAI API key
- Supabase account
- Redis (optional, for agent messaging)

### Installation

```bash
cd "New folder"
npm install
cp .env.example .env
# Edit .env with your credentials
```

### Run

```bash
# Development (with hot reload)
npm run dev

# Production
npm start
```

### Test

```bash
curl -X POST http://localhost:3002/api/process-message \
  -H "Content-Type: application/json" \
  -d '{
    "message": "What is the Q4 car market trend?",
    "conversationId": "test-123"
  }'
```

## 📁 Project Structure

```
New folder/
├── src/
│   ├── server.js              # Main HTTP server
│   ├── config/
│   │   └── index.js           # Configuration loader
│   ├── services/
│   │   ├── IntentRouter.js    # Intent classification
│   │   ├── TemplateEngine.js  # Template discovery & execution
│   │   ├── AgentOrchestrator.js # Agent coordination
│   │   ├── MemoryService.js   # Memory management
│   │   └── ResponseBuilder.js # Response construction
│   ├── agents/
│   │   ├── registry.js        # Agent definitions (55 agents)
│   │   └── tools.js           # Agent tools (Redis, Supabase, etc.)
│   └── utils/
│       ├── logger.js          # Logging utility
│       └── validators.js      # Input validation
├── tests/
│   ├── intent-router.test.js
│   ├── template-engine.test.js
│   └── agent-orchestrator.test.js
├── docs/
│   ├── API.md                 # API documentation
│   ├── AGENTS.md              # Agent catalog
│   └── WORKFLOW.md            # Workflow diagrams
├── package.json
├── .env.example
└── README.md
```

## 🎯 API Endpoints

### POST `/api/process-message`
Process user message and return intelligent response.

**Request:**
```json
{
  "message": "What is the Q4 car market trend?",
  "conversationId": "conv-123",
  "context": {
    "userId": "user-456",
    "tenantId": "tenant-789"
  }
}
```

**Response:**
```json
{
  "query": "What is the Q4 car market trend?",
  "intentClassification": {
    "type": "analysis",
    "intent": "MARKET_ANALYSIS",
    "confidence": 0.92
  },
  "turnEnvelope": {
    "ack": "I'm analyzing Q4 car market trends using demand forecast and market data...",
    "plan": {
      "declarative": [
        {
          "action": "analyze_market_trends",
          "params": { "market": "automotive", "period": "Q4" }
        }
      ],
      "procedural": []
    },
    "ask": [],
    "memory": {
      "workingMemory": [...],
      "retrievedContext": [...]
    },
    "decisions": [],
    "meta": {
      "agentsInvolved": ["MarketAnalysisAgent", "DemandForecastAgent"],
      "processingTime": 2847
    }
  },
  "processedAt": "2025-01-04T12:34:56.789Z",
  "requestId": "req-1704372896789"
}
```

### GET `/api/health`
Server health check.

### GET `/api/agents`
List all available agents.

### POST `/api/agents/:agentId/execute`
Execute specific agent directly.

## 🤖 Agent Workflow

### Supported Agent Categories

1. **Skill Agents** (7)
   - SDA (Semantic Data Agent)
   - FQA (Forecast Q&A Agent)
   - CAA (Causal & Attribution Agent)
   - SSA (Scenario Simulator Agent)
   - IRA (Inventory Risk Agent)
   - OPT (Optimizer Agent)
   - ASA (Answer Synthesis Agent)

2. **Demand-Gen Agents** (4)
   - Marketing Plan Agent
   - Sales Pipeline Agent
   - Elasticity & Uplift Agent
   - Campaign→SKU Mapper Agent

3. **S&OP Agents** (7)
   - Inventory Position Agent
   - Capacity & Lead-Time Agent
   - Supply Planning Agent
   - Production Scheduling Agent
   - Procurement Agent
   - Logistics & Allocation Agent
   - ATP/CTP Agent

4. **Governance Agents** (5)
   - Constraint Broadcast Agent
   - Price/Promo Guardrail Agent
   - Policy Elicitation Agent
   - Data Gap & Mapping Agent
   - RCA / Change Detective Agent

5. **MCO Pipeline Agents** (11)
   - Ingress & Normalization Agent
   - Catalog & Schema Agent
   - Feature & Forecast Agent
   - Attribution & Causal Agent
   - Opportunity Scanner Agent
   - Cost & Finance Mapper Agent
   - Budget Optimizer Agent
   - Bid & Target Setter Agent
   - Creative Ops Agent
   - Platform Adapter Agent
   - Question Router & Planner Agent

**Total: 55 Agents** (21 MCO + 34 domain agents)

## 🔄 Data Flow

```
1. User Input → Intent Classification (OpenAI)
2. Intent → Template Discovery (Supabase semantic search)
3. Template → Agent Selection (registry lookup)
4. Agents → Task Execution (Redis Streams / HTTP)
5. Results → Response Synthesis (TurnEnvelope)
6. Response → Frontend UI
```

## 🔧 Configuration

### Environment Variables

- `PORT`: Server port (default: 3002)
- `OPENAI_API_KEY`: Required for intent classification
- `SUPABASE_URL`: Required for template/prompt storage
- `ENABLE_REDIS`: Optional, for agent messaging
- `LOG_LEVEL`: `debug`, `info`, `warn`, `error`

### Agent Configuration

Edit `src/agents/registry.js` to add/modify agents:

```javascript
export const agents = [
  {
    id: 'sda',
    name: 'Semantic Data Agent',
    role: 'Query structured and unstructured data sources',
    capabilities: ['semantic_search', 'data_retrieval'],
    tools: ['vector_search', 'sql_query', 'api_call']
  }
  // ... more agents
];
```

## 📊 Monitoring

Logs are output to console in structured JSON format:

```json
{
  "timestamp": "2025-01-04T12:34:56.789Z",
  "level": "info",
  "service": "IntentRouter",
  "message": "Intent classified",
  "data": {
    "intent": "ANALYSIS",
    "confidence": 0.92,
    "processingTime": 1234
  }
}
```

## 🧪 Testing

```bash
# Run all tests
npm test

# Run specific test
node --test tests/intent-router.test.js
```

## 📚 Documentation

- [API Reference](docs/API.md)
- [Agent Catalog](docs/AGENTS.md)
- [Workflow Diagrams](docs/WORKFLOW.md)

## 🤝 Contributing

1. Fork the repository
2. Create feature branch
3. Add tests
4. Submit pull request

## 📄 License

MIT


