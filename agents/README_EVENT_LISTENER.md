# CrewAI Semantic Event Listener

Production-ready event listener that captures CrewAI agent activities, filters them through semantic policies, and broadcasts to Redis Streams message bus.

## Architecture

```
CrewAI Agents → Event Bus → Semantic Filter → Redis Streams → Downstream Systems
                                    ↓
                     [Rules + Embeddings + LLM Check]
```

## Components

### 1. Semantic Policy Engine (`semantic_policy_engine.py`)
- **Rule-based filtering**: Fast deterministic checks (event type, agent, task, success, tokens)
- **Embedding similarity**: Semantic matching against policy goal vectors
- **Optional LLM check**: Final arbiter for complex decisions
- **PII redaction**: Removes sensitive data before broadcasting
- **Deduplication**: Drops repeated events within time window

### 2. Event Listener (`crewai_event_listener.py`)
- **BaseEventListener subclass**: Integrates with CrewAI's event system
- **Event normalization**: Standardizes event payloads
- **Non-blocking publisher**: Background thread for Redis publishing
- **CloudEvents compliance**: All published events follow CloudEvents 1.0

### 3. Policy Configuration (`crewai_policies.yaml`)
- **Declarative policies**: Define what to broadcast and when
- **Semantic goals**: Vector-based semantic matching
- **Topic routing**: Route events to different Redis Streams
- **Flexible rules**: Combine deterministic and semantic criteria

## Quick Start

### 1. Install Dependencies
```bash
pip install crewai crewai-tools openai redis pyyaml
```

### 2. Configure Policies
Edit `crewai_policies.yaml` to define your broadcast policies:

```yaml
policies:
  - name: strategic_insights
    description: Broadcast strategic analysis
    topics: ["stream:agents:insights:v1"]
    when:
      event_types: ["agent_execution_completed"]
      agents_allowlist: ["Strategic Plan*", "*Analyst*"]
      require_success: true
      min_tokens: 50
    semantics:
      goal_vectors:
        - "strategic recommendations, business insights"
        - "revenue targets, growth opportunities"
      min_similarity: 0.68
      fields: ["output", "metadata.reasoning_summary"]
    llm_check:
      enabled: true
      prompt: "Return JSON: {broadcast: bool, tags: [], reason: ...}"
```

### 3. Attach to Your Crew
```python
from crewai import Crew, Agent, Task
from crewai.events import CrewAIEventsBus
from crewai_event_listener import SemanticBusListener

# Create your agents and tasks
agent = Agent(role="Analyst", goal="Analyze data", ...)
task = Task(description="Analyze Q4 performance", agent=agent)

# Create crew
crew = Crew(agents=[agent], tasks=[task])

# Attach listener
event_bus = CrewAIEventsBus()
listener = SemanticBusListener("crewai_policies.yaml")
listener.setup_listeners(event_bus)

# Execute - events automatically filtered and broadcast
result = crew.kickoff()
```

## Policy Configuration

### Policy Structure
```yaml
policies:
  - name: policy_name
    description: What this policy does
    topics: ["stream:target:v1"]          # Redis Streams to publish to
    when:                                  # Deterministic filters (fast)
      event_types: ["agent_execution_completed", "task_completed"]
      require_success: true
      agents_allowlist: ["Agent*", "Specific Agent"]
      tasks_allowlist: ["task_pattern*"]
      tools_allowlist: ["tool_*"]
      min_tokens: 50
    semantics:                             # Semantic filters (embeddings)
      goal_vectors:                        # What are we looking for?
        - "business insights, strategic value"
        - "actionable recommendations"
      min_similarity: 0.65                 # Cosine similarity threshold
      fields: ["output", "metadata.reasoning_summary"]
    llm_check:                             # Optional final arbiter
      enabled: true
      prompt: "Does this have strategic value?"
      max_tokens: 100
    novelty:                               # Optional novelty check
      enabled: true
      memory_scope: "entity"
      min_diff_ratio: 0.15
```

### Built-in Policies

1. **strategic_insights**: High-value strategic analysis
2. **data_query_results**: Significant data findings
3. **system_alerts**: Critical system events
4. **system_call_results**: External API call results
5. **tool_analytics**: Tool usage metrics
6. **agent_failures**: Errors and failures
7. **expensive_operations**: High-cost LLM calls

## Event Types Captured

- `crew_started` / `crew_completed`
- `agent_execution_completed`
- `task_completed`
- `tool_usage_finished`

### Event Payload Structure
```json
{
  "type": "agent_execution_completed",
  "timestamp": "2024-10-31T12:00:00Z",
  "crew_run_id": "uuid",
  "agent": {
    "name": "Strategic Plan Analyst",
    "role": "Analyst",
    "goal": "Analyze strategic plan"
  },
  "output": "Q4 revenue target is $45M...",
  "success": true,
  "metadata": {
    "tokens": 150,
    "cost": 0.002,
    "execution_time": 2500,
    "reasoning_summary": "..."
  }
}
```

## Integration Examples

### Example 1: Single Agent
```python
from integrate_event_listener import create_monitored_crew_with_listener
from plan_review_agent import plan_review_agent
from crewai import Task

task = Task(
    description="Review Q4 strategic plan",
    expected_output="Analysis",
    agent=plan_review_agent
)

crew, listener = create_monitored_crew_with_listener(
    agents=[plan_review_agent],
    tasks=[task]
)

result = crew.kickoff()  # Events automatically broadcast
```

### Example 2: Multi-Agent Workflow
```python
# Plan review task
plan_task = Task(
    description="Review strategic plan",
    agent=plan_review_agent
)

# Data query task
data_task = Task(
    description="Query sales data",
    agent=data_query_agent,
    context=[plan_task]
)

crew, listener = create_monitored_crew_with_listener(
    agents=[plan_review_agent, data_query_agent],
    tasks=[plan_task, data_task]
)

result = crew.kickoff()
```

### Example 3: Hierarchical Process
```python
from crewai import Process

manager = Agent(
    role="Manager",
    goal="Coordinate analysis",
    allow_delegation=True
)

crew, listener = create_monitored_crew_with_listener(
    agents=[manager, specialist1, specialist2],
    tasks=[task1, task2]
)

crew.process = Process.hierarchical
crew.manager_agent = manager

result = crew.kickoff()
```

### Example 4: Retrofit Existing Agent
```python
# Add at startup of existing agent script
from crewai.events import CrewAIEventsBus
from crewai_event_listener import SemanticBusListener

event_bus = CrewAIEventsBus()
listener = SemanticBusListener("crewai_policies.yaml")
listener.setup_listeners(event_bus)

# Your existing Redis consumer loop continues as-is
# Events automatically captured and filtered!
```

## Redis Streams Output

### Published CloudEvent Structure
```json
{
  "specversion": "1.0",
  "id": "uuid",
  "source": "urn:crewai:event-listener",
  "type": "com.acme.crewai.agent_execution_completed",
  "subject": "Strategic Plan Analyst",
  "time": "2024-10-31T12:00:00Z",
  "dataschema": "https://schemas.acme.com/crewai/event/1-0-0.json",
  "data": {
    "@context": {
      "@vocab": "https://vocab.acme.com/",
      "crewai": "https://vocab.acme.com/crewai/"
    },
    ... normalized event payload ...
  },
  "meta": {
    "policy": "strategic_insights",
    "similarity": 0.75
  }
}
```

### Consuming from Redis
```python
import redis
r = redis.Redis()

# Read from stream
messages = r.xreadgroup(
    "consumer_group",
    "consumer_1",
    {"stream:agents:insights:v1": ">"},
    count=10,
    block=1000
)

for stream, entries in messages:
    for msg_id, fields in entries:
        event_id = fields["event_id"]
        event = r.json().get(f"event:{event_id}")
        
        # Process event
        print(f"Agent: {event['data']['agent']['name']}")
        print(f"Output: {event['data']['output']}")
        
        # ACK
        r.xack(stream, "consumer_group", msg_id)
```

## Customization

### Custom Embedder
```python
from semantic_policy_engine import Embedder

class CustomEmbedder(Embedder):
    def embed(self, texts):
        # Use your embedding service
        return embeddings

listener = SemanticBusListener("policies.yaml")
listener.policy_engine.embedder = CustomEmbedder()
```

### Custom LLM Judge
```python
from semantic_policy_engine import LLMJudge

class CustomJudge(LLMJudge):
    def check(self, policy_name, payload, prompt, **kwargs):
        # Your LLM logic
        return {"broadcast": True, "tags": [], "reason": "..."}

listener.policy_engine.judge = CustomJudge()
```

### Extend Listener
```python
from crewai_event_listener import SemanticBusListener

class CustomListener(SemanticBusListener):
    def _try_publish(self, payload):
        # Add custom filters
        if self.my_custom_check(payload):
            super()._try_publish(payload)
```

## Testing

### Test Policy Engine
```bash
python crewai_event_listener.py
```

### Test with Mock Event
```python
from crewai_event_listener import SemanticBusListener

listener = SemanticBusListener("crewai_policies.yaml")

mock_event = {
    "type": "agent_execution_completed",
    "agent": {"name": "Test Agent"},
    "output": "Strategic insight...",
    "success": True,
    "metadata": {"tokens": 100}
}

decision = listener.policy_engine.should_broadcast(mock_event)
print("Passes filter:", decision is not None)
```

## Monitoring

### Metrics to Track
- Events captured per agent
- Events broadcast per policy
- Policy match rates
- Embedding similarity distributions
- LLM judge accept/reject rates
- Deduplication hit rate
- Publishing latency

### Logging
```python
# Enable detailed logging
import logging
logging.basicConfig(level=logging.DEBUG)
```

## Best Practices

1. **Keep handlers light**: Event handlers must be non-blocking
2. **Redact early**: PII removed before routing decisions
3. **Dedupe aggressively**: Avoid spammy broadcasts
4. **Tag everything**: Include policy, similarity, agent info
5. **Test policies**: Use mock events to validate filters
6. **Monitor performance**: Track latency and match rates
7. **Version policies**: Policies are code - version control them

## Performance

- **Rule filtering**: <1ms per event
- **Embedding**: ~50ms per event (cached embeddings)
- **LLM check**: ~500ms per event (optional, use sparingly)
- **Redis publish**: <5ms per event (background thread)
- **Total overhead**: ~50-600ms per event depending on config

## Troubleshooting

### Events not broadcasting
1. Check policy `when` rules match event type
2. Verify agent name matches `agents_allowlist`
3. Check embedding similarity threshold
4. Enable debug logging to see filtering decisions

### High latency
1. Reduce number of policies
2. Disable LLM checks for high-volume events
3. Use tighter deterministic filters
4. Increase background publisher queue size

### Redis connection issues
1. Verify Redis is running
2. Check Redis host/port configuration
3. Ensure Redis has JSON module: `redis-cli MODULE LIST`

## Files

- `crewai_policies.yaml` - Policy configuration
- `semantic_policy_engine.py` - Core filtering engine
- `crewai_event_listener.py` - CrewAI integration
- `integrate_event_listener.py` - Integration examples
- `plan_review_agent.py` - Example agent (uses listener)
- `data_query_agent.py` - Example agent (uses listener)
- `stream_capture_agent.py` - Example agent (uses listener)
- `system_call_zapier_agent.py` - Example agent (uses listener)

## License

Production-ready for internal use. Follows all Redis Streams + CloudEvents + CrewAI best practices.
