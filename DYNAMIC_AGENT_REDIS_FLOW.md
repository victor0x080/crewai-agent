# Dynamic Agent Redis Streams Flow

## Complete Flow: Node.js → Redis → Python → Redis → Node.js

### Step-by-Step Flow

```
1. User Query
   ↓
2. Agent Discovery (threshold 0.95)
   ↓
3. No high-confidence agent found
   ↓
4. OpenAI generates dynamic agent spec with algorithms
   ↓
5. Node.js calls Python factory (create_dynamic_agent.py)
   ↓
6. Python factory creates agent and saves config to Redis
   ↓
7. Node.js starts dynamic runner process (dynamic_runner.py)
   ↓
8. Runner loads config from Redis and listens on input stream
   ↓
9. Node.js creates dynamicAgent object and calls executeAgents()
   ↓
10. executeAgents() → executeRealAgents() → crewAIBridge.executeAgentsParallel()
   ↓
11. CrewAIBridgeService.executeAgent() publishes task to Redis
   ↓
12. Runner picks up task from Redis input stream
   ↓
13. Runner executes agent with algorithms
   ↓
14. Runner publishes result to Redis output stream
   ↓
15. Node.js monitors output stream and receives response
   ↓
16. Node.js returns result to user
```

## Critical Stream Name Matching

### Agent ID Format
- Created by Python: `dynamic_{agentType}_{timestamp}`
- Example: `dynamic_marketing_mix_analyst_1762931981685`

### Stream Name Normalization

**Node.js Side (CrewAIBridgeService.js):**
```javascript
getAgentStream(agentId) {
  const normalizedId = agentId.toLowerCase().replace(/[^a-z0-9-]/g, '-');
  // Apply alias mapping if needed
  const idForStreams = aliasMap[normalizedId] || normalizedId;
  return `stream:agent:${idForStreams}:in`;  // Input stream
  // Output: `stream:agent:${idForStreams}:out`
}
```

**Python Side (dynamic_runner.py):**
```python
normalized_id = agent_id.lower().replace(' ', '-').replace('_', '-')
normalized_id = ''.join(c if c.isalnum() or c == '-' else '-' for c in normalized_id)
input_stream = f'stream:agent:{normalized_id}:in'
output_stream = f'stream:agent:{normalized_id}:out'
```

### Potential Mismatch Issue

The normalization logic is **slightly different**:
- Node.js: `replace(/[^a-z0-9-]/g, '-')` - replaces ALL non-alphanumeric (except dash) with dash
- Python: `replace(' ', '-').replace('_', '-')` then filters - only replaces spaces and underscores first

**Example:**
- Agent ID: `dynamic_marketing_mix_analyst_1762931981685`
- Node.js: `dynamic-marketing-mix-analyst-1762931981685` ✅
- Python: `dynamic-marketing-mix-analyst-1762931981685` ✅ (should match)

## Detailed Flow

### Phase 1: Agent Creation

**1. Node.js: Create Dynamic Agent**
```javascript
// AgentOrchestrator.js line 170
const agentCreationResult = await this.createDynamicAgent(discovery.dynamicAgentSpec);
// Returns: { success: true, agent_id: "dynamic_marketing_mix_analyst_1234567890", ... }
```

**2. Python: Save Config to Redis**
```python
# create_dynamic_agent.py
agent_id = f"dynamic_{spec.get('agentType', 'agent').lower().replace(' ', '_')}_{int(time.time())}"
config_key = f"dynamic_agent:config:{agent_id}"
redis_client.set(config_key, json.dumps(agent_config), ex=86400)
```

**3. Node.js: Start Runner**
```javascript
// AgentOrchestrator.js line 179
const runnerResult = await this.startDynamicAgentRunner(agentCreationResult.agent_id);
// Spawns: python3 agents/crewai_python/runners/dynamic_runner.py {agent_id}
```

**4. Python: Runner Loads Config and Listens**
```python
# dynamic_runner.py
agent_config = load_agent_config(agent_id)  # From Redis or file
normalized_id = normalize(agent_id)
input_stream = f'stream:agent:{normalized_id}:in'
output_stream = f'stream:agent:{normalized_id}:out'
runner = AgentRunner(agent=agent, input_stream=input_stream, output_stream=output_stream)
runner.run()  # Blocks and listens on Redis stream
```

### Phase 2: Task Execution

**5. Node.js: Execute Agent**
```javascript
// AgentOrchestrator.js line 203
const agentResults = await this.executeAgents([dynamicAgent], {
  query, intent, context, conversationId, userId, tenantId
});
```

**6. Node.js: Publish Task to Redis**
```javascript
// CrewAIBridgeService.js line 89
async executeAgent(agentId, task, timeout) {
  const taskId = uuidv4();
  const streamName = this.getAgentStream(agentId);  // stream:agent:{normalized_id}:in
  
  // Create CloudEvent
  const cloudevent = {
    id: eventId,
    type: 'crewai.task.request',
    data: {
      task_id: taskId,  // ← Critical for matching response!
      agent_id: agentId,
      task_description: task.description,
      inputs: task.inputs
    }
  };
  
  // Store full event
  await this.redis.set(`event:${eventId}`, JSON.stringify(cloudevent));
  
  // Publish pointer to stream
  await this.redis.xAdd(streamName, '*', {
    event_id: eventId,
    type: cloudevent.type
  });
  
  // Start monitoring output stream
  this.monitorAgentOutputStreams(agentId, taskId, timeout);
}
```

**7. Python: Runner Consumes Task**
```python
# base_runner.py (via AgentRunner)
messages = consume_stream(input_stream, consumer_group, consumer_name)
for message in messages:
    event_id = message['event_id']
    event_data = fetch_cloudevent(event_id)  # From Redis event:{event_id}
    task_id = event_data['data']['task_id']
    
    # Execute agent
    result = agent.execute(task_description)
    
    # Publish result
    publish_cloudevent(
        output_stream,
        'crewai.task.response',
        source='python-agent',
        data={
            'task_id': task_id,  # ← Must match request task_id!
            'result': result,
            'status': 'success'
        }
    )
```

**8. Node.js: Monitor Output Stream**
```javascript
// CrewAIBridgeService.js line 173
async monitorAgentOutputStreams(agentId, taskId, timeout) {
  const outputStream = `stream:agent:${normalizedId}:out`;
  
  // Read from stream
  const messages = await this.redis.xRead([{ key: outputStream, id: lastReadId }]);
  
  for (const message of messages) {
    const eventId = message.event_id;
    const eventData = JSON.parse(await this.redis.get(`event:${eventId}`));
    
    // Match by task_id
    if (eventData.data.task_id === taskId) {
      const pending = this.pendingTasks.get(taskId);
      pending.resolve({ success: true, result: eventData.data.result });
      return;
    }
  }
}
```

## Key Points

1. **Stream Names Must Match**: Both Node.js and Python must normalize agent IDs identically
2. **Task ID Matching**: Responses are matched by `task_id`, not agent_id
3. **CloudEvents Format**: All messages use CloudEvents 1.0 format
4. **Event Storage**: Full events stored in `event:{eventId}`, streams contain pointers
5. **Timeout Handling**: Node.js sets timeout and rejects if no response received

## Fix Required

The normalization logic should be **identical** in both Node.js and Python:

```javascript
// Node.js (CrewAIBridgeService.js)
function normalizeAgentId(agentId) {
  return agentId.toLowerCase()
    .replace(/[^a-z0-9-]/g, '-')  // Replace all non-alphanumeric (except dash) with dash
    .replace(/-+/g, '-')           // Collapse multiple dashes
    .replace(/^-|-$/g, '');        // Remove leading/trailing dashes
}
```

```python
# Python (dynamic_runner.py)
def normalize_agent_id(agent_id):
    normalized = agent_id.lower()
    normalized = ''.join(c if c.isalnum() or c == '-' else '-' for c in normalized)
    normalized = re.sub(r'-+', '-', normalized)  # Collapse multiple dashes
    normalized = normalized.strip('-')  # Remove leading/trailing dashes
    return normalized
```

## Testing

To verify the flow works:

1. Check stream names match:
   ```bash
   # Node.js logs should show:
   # "🤖 Executing CrewAI agent via Redis" { stream: "stream:agent:dynamic-marketing-mix-analyst-123:in" }
   
   # Python logs should show:
   # "Listening on stream:agent:dynamic-marketing-mix-analyst-123:in"
   ```

2. Check task_id matching:
   ```bash
   # Request should include task_id in data
   # Response should include same task_id in data
   ```

3. Monitor Redis streams:
   ```bash
   redis-cli XREAD STREAMS stream:agent:dynamic-marketing-mix-analyst-123:in 0
   redis-cli XREAD STREAMS stream:agent:dynamic-marketing-mix-analyst-123:out 0
   ```

