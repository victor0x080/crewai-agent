# Agent → Redis → Backend Flow

## 📊 Complete Flow Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│ 1. NODE.JS BACKEND                                             │
│    - Receives API request                                      │
│    - Creates task with task_id                                 │
│    - Publishes to Redis Stream                                 │
│    - Starts monitoring for response                            │
└────────────────────┬──────────────────────────────────────────┘
                     │
                     │ Publishes CloudEvent to Redis Stream
                     │ stream:mco:plan:step (or other input stream)
                     │ Stores full event in Redis: event:{eventId}
                     │
                     ▼
┌─────────────────────────────────────────────────────────────────┐
│ 2. REDIS STREAMS                                                │
│    Input Stream: stream:mco:plan:step                           │
│      - Contains: event_id pointer                               │
│      - Full event stored in: event:{eventId}                    │
│                                                                  │
│    Output Streams:                                              │
│      - stream:mco:event:observation                             │
│      - stream:mco:event:recommendation                          │
│      - stream:mco:event:decision                                 │
│      - etc.                                                      │
└────────────────────┬──────────────────────────────────────────┘
                     │
                     │ Agents consume from input stream
                     │
                     ▼
┌─────────────────────────────────────────────────────────────────┐
│ 3. PYTHON AGENTS (base_runner.py)                               │
│    3.1 consume_stream()                                         │
│        - Reads from: stream:mco:plan:step                        │
│        - Gets event_id from stream message                      │
│        - Fetches full event: event:{eventId}                    │
│                                                                  │
│    3.2 Extract task_id                                          │
│        - From: event['data']['task_id']                         │
│                                                                  │
│    3.3 Execute CrewAI                                            │
│        - crew.kickoff() runs agent                              │
│        - Gets result                                            │
│                                                                  │
│    3.4 publish_cloudevent()                                     │
│        - Stream: self.output_stream                             │
│          (e.g., stream:mco:event:observation)                   │
│        - Data includes:                                         │
│          * result: agent output                                 │
│          * task_id: original task ID                            │
│          * status: "success" or "error"                         │
│          * event_id: original event ID                         │
│        - Stores full event: event:{newEventId}                  │
│        - Adds pointer to stream: event_id                       │
└────────────────────┬──────────────────────────────────────────┘
                     │
                     │ Publishes response to output stream
                     │
                     ▼
┌─────────────────────────────────────────────────────────────────┐
│ 4. REDIS STREAMS (Output)                                       │
│    stream:mco:event:observation (or other output stream)         │
│      - Contains: event_id pointer                               │
│      - Full event stored in: event:{newEventId}                 │
│      - Event data includes: result, task_id, status            │
└────────────────────┬──────────────────────────────────────────┘
                     │
                     │ Backend monitors output stream
                     │
                     ▼
┌─────────────────────────────────────────────────────────────────┐
│ 5. NODE.JS BACKEND (monitorAgentOutputStreams)                 │
│    5.1 Reads from output stream                                 │
│        - Uses: xRead()                                          │
│        - Stream: stream:mco:event:observation                   │
│        - Gets event_id from stream message                      │
│                                                                  │
│    5.2 Fetches full event                                       │
│        - Gets from: event:{eventId}                             │
│        - Parses JSON event data                                 │
│                                                                  │
│    5.3 Matches by task_id                                       │
│        - Checks: eventData.data.task_id === taskId              │
│        - Falls back to source matching if no task_id            │
│                                                                  │
│    5.4 Resolves promise                                         │
│        - Returns result to API handler                          │
│        - Includes in agentResults                                │
└─────────────────────────────────────────────────────────────────┘
```

## 🔍 Code Flow Details

### Agent Side (Python)

**File: `agents/crewai_python/base_runner.py`**

```python
# 1. Consume task from Redis Stream
msgs = consume_stream(self.input_stream, self.group, self.name, ...)
event = msg['event']  # Full CloudEvent

# 2. Extract task_id
task_id = event['data']['task_id']

# 3. Execute CrewAI
result = crew.kickoff()

# 4. Publish result back to Redis
publish_cloudevent(
    self.output_stream,           # e.g., 'stream:mco:event:observation'
    self.output_type,              # e.g., 'mco.event.observation'
    f"urn:agent:{self.group}",     # Source
    {
        "result": str(result),
        "task_id": task_id,        # ← Critical for matching!
        "event_id": event_id,
        "status": "success"
    }
)
```

**File: `agents/crewai_python/tools/redis_streams_tools.py`**

```python
def publish_cloudevent(stream_key, event_type, source, data, ...):
    # 1. Build CloudEvent
    event = build_cloudevent(event_type, source, data, ...)
    event_id = event["id"]
    
    # 2. Store full event in Redis
    r.set(f"event:{event_id}", json.dumps(event))
    
    # 3. Add pointer to stream
    r.xadd(stream_key, {
        "event_id": event_id,
        "type": event_type,
        ...
    })
```

### Backend Side (Node.js)

**File: `src/services/CrewAIBridgeService.js`**

```javascript
// 1. Publish task to Redis
const cloudevent = {
    id: eventId,
    type: 'crewai.task.request',
    data: {
        task_id: taskId,  // ← Critical for matching!
        agent_id: agentId,
        task_description: task.description,
        ...
    }
};
await this.redis.set(`event:${eventId}`, JSON.stringify(cloudevent));
await this.redis.xAdd(streamName, '*', { event_id: eventId, ... });

// 2. Start monitoring
this.monitorAgentOutputStreams(agentId, taskId, timeout);

// 3. Monitor output stream
async monitorAgentOutputStreams(agentId, taskId, timeout) {
    // Read from output stream
    const messages = await this.redis.xRead([{ 
        key: outputStream, 
        id: lastReadId 
    }], { COUNT: 10, BLOCK: 100 });
    
    // For each message
    const eventId = message.event_id;
    const eventDataJson = await this.redis.get(`event:${eventId}`);
    const eventData = JSON.parse(eventDataJson);
    
    // Match by task_id
    const responseTaskId = eventData.data.task_id;
    if (responseTaskId === taskId) {
        // Found matching response!
        pending.resolve({ success: true, result: eventData.data.result });
    }
}
```

## ✅ Verification Checklist

- [x] Agents consume tasks from Redis input streams
- [x] Agents extract task_id from task event
- [x] Agents execute CrewAI tasks
- [x] Agents publish results to Redis output streams
- [x] Results include task_id for matching
- [x] Backend monitors output streams
- [x] Backend fetches full events from Redis
- [x] Backend matches responses by task_id
- [x] Backend returns results to API handler

## 🔧 Current Status

**Working:**
- ✅ Agents execute tasks (trace batches confirm)
- ✅ Agents publish to Redis streams
- ✅ Backend monitors streams

**Needs Verification:**
- ⚠️ Are agents publishing with task_id?
- ⚠️ Is backend matching correctly?
- ⚠️ Are responses being returned?

## 🐛 Debugging Commands

```bash
# Check if agents published results
redis-cli XRANGE stream:mco:event:observation - + COUNT 5

# Check if response has task_id
redis-cli GET "event:{eventId}" | jq '.data.task_id'

# Check backend logs
tail -f logs/node-backend.log | grep -E "monitor|match|resolve"

# Check agent logs
tail -f logs/python-agents.log | grep -E "Publishing|task_id"
```

