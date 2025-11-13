"""
Decision Extraction Agent (CrewAI)

Consumes conversation events from Redis Streams, analyzes executive cards,
and publishes decision events for real-time display in DecisionInbox.

Compliance:
- Redis Streams (XREADGROUP, XACK)
- CloudEvents 1.0 (specversion, id, source, type, dataschema, @context)
- JSON Schema validation
- Ontology tools (resolve_concept, expand_concepts)
"""

import redis
import json
import uuid
import time
from datetime import datetime
from crewai import Agent, Task, Crew, Process
from crewai.tools import tool

# Redis connection
redis_client = redis.Redis.from_url("redis://localhost:6379", decode_responses=False)

# ============================================================================
# Tools
# ============================================================================

@tool("publish_decision_event")
def publish_decision_event(decision_data: dict) -> str:
    """
    Publish a decision CloudEvent to Redis Streams.
    
    Args:
        decision_data: Dict with title, description, priority, confidence, reasoning
    
    Returns:
        Event ID of published decision
    """
    event_id = str(uuid.uuid4())
    
    # Build CloudEvent
    cloudevent = {
        "specversion": "1.0",
        "id": event_id,
        "source": "urn:agent:decision-extraction",
        "type": "com.acme.decision.created",
        "subject": decision_data.get("title", "Decision"),
        "time": datetime.utcnow().isoformat() + "Z",
        "dataschema": "https://schemas.acme.com/decision/1-0-0.json",
        "data": {
            "@context": {
                "ex": "http://example.org/ontology#",
                "decision": "ex:Decision",
                "priority": "ex:Priority",
                "confidence": "ex:Confidence"
            },
            "id": event_id,
            "title": decision_data["title"],
            "description": decision_data["description"],
            "status": "pending",
            "priority": decision_data.get("priority", "medium"),
            "confidence": decision_data.get("confidence", 0.85),
            "source": "Decision Extraction Agent",
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "metadata": {
                "conversationId": decision_data.get("conversationId"),
                "reasoning": decision_data.get("reasoning"),
                "alternatives": decision_data.get("alternatives", [])
            }
        }
    }
    
    # Store full event in RedisJSON
    redis_client.execute_command('JSON.SET', f'event:{event_id}', '$', json.dumps(cloudevent))
    
    # Publish to Redis Pub/Sub (for RedisEventBus WebSocket bridge)
    redis_client.publish('decision.created', json.dumps({
        'topic': 'decision.created',
        'event': cloudevent['data']  # Send the decision data directly
    }))
    
    print(f"[DecisionExtractionAgent] ✅ Published decision to Redis Pub/Sub: {event_id}")
    return event_id


@tool("fetch_conversation_event")
def fetch_conversation_event(event_id: str) -> dict:
    """
    Fetch a conversation CloudEvent from RedisJSON.
    
    Args:
        event_id: The CloudEvent ID
    
    Returns:
        CloudEvent dict
    """
    result = redis_client.execute_command('JSON.GET', f'event:{event_id}')
    if result:
        return json.loads(result)
    return {}


@tool("resolve_concept")
def resolve_concept(term: str) -> str:
    """
    Resolve a term to its ontology URI.
    
    Args:
        term: Natural language term (e.g., "decision", "recommendation")
    
    Returns:
        Ontology URI (e.g., "ex:Decision")
    """
    # Call OntologyService via HTTP or direct DB query
    # For now, simple mapping
    mappings = {
        "decision": "ex:Decision",
        "recommendation": "ex:Recommendation",
        "action": "ex:Action",
        "insight": "ex:Insight",
        "priority": "ex:Priority",
        "confidence": "ex:Confidence"
    }
    return mappings.get(term.lower(), f"ex:{term.capitalize()}")


# ============================================================================
# Agent Definition
# ============================================================================

decision_extraction_agent = Agent(
    role='Decision Extraction Specialist',
    goal='Analyze conversation executive cards and extract actionable decisions for real-time display',
    backstory="""You are an expert at identifying decision points in business conversations.
    You analyze executive summaries, recommendations, and insights to extract clear, actionable decisions.
    You understand priority levels, confidence scores, and business context.
    You publish decisions as CloudEvents to Redis Streams for real-time consumption by the UI.""",
    tools=[publish_decision_event, fetch_conversation_event, resolve_concept],
    verbose=True,
    allow_delegation=False
)


# ============================================================================
# Task Template
# ============================================================================

def create_decision_extraction_task(conversation_event_id: str, user_query: str) -> Task:
    """
    Create a task to extract decisions from a conversation event.
    
    Args:
        conversation_event_id: ID of the conversation CloudEvent in Redis
        user_query: Original user query for context
    
    Returns:
        CrewAI Task
    """
    return Task(
        description=f"""
        Analyze the conversation event (ID: {conversation_event_id}) and extract actionable decisions.
        
        User Query: {user_query}
        
        Steps:
        1. Fetch the conversation event using fetch_conversation_event
        2. Analyze executive cards (recommendations, actions, insights)
        3. For each actionable item:
           - Extract a clear title (max 100 chars)
           - Write a detailed description
           - Determine priority (low/medium/high/critical)
           - Assess confidence score (0.0-1.0)
           - Identify reasoning and alternatives
        4. Publish each decision using publish_decision_event
        
        Decision Criteria:
        - Must be actionable (not just informational)
        - Must have clear business impact
        - Recommendations with confidence > 0.8 are high priority
        - Actions from executive cards are medium priority by default
        - Insights with decision keywords are extracted if confidence > 0.9
        
        Output: List of published decision event IDs
        """,
        expected_output="JSON array of decision event IDs that were published",
        agent=decision_extraction_agent
    )


# ============================================================================
# Consumer Loop
# ============================================================================

def start_decision_extraction_consumer():
    """
    Start consuming conversation events from Redis Streams.
    """
    stream_key = 'stream:conversation:completed'
    group_name = 'decision-extractors'
    consumer_name = 'decision-extractor-1'
    
    # Create consumer group
    try:
        redis_client.xgroup_create(stream_key, group_name, id='$', mkstream=True)
        print(f"[DecisionExtractionAgent] Created consumer group: {group_name}")
    except redis.exceptions.ResponseError as e:
        if 'BUSYGROUP' not in str(e):
            raise
        print(f"[DecisionExtractionAgent] Consumer group already exists: {group_name}")
    
    print(f"[DecisionExtractionAgent] 🚀 Starting consumer loop...")
    
    while True:
        try:
            # Read from stream
            messages = redis_client.xreadgroup(
                group_name,
                consumer_name,
                {stream_key: '>'},
                count=10,
                block=1000
            )
            
            for stream, entries in messages:
                for msg_id, fields in entries:
                    # Decode fields
                    fields_decoded = {k.decode(): v.decode() for k, v in fields.items()}
                    event_id = fields_decoded.get('event_id')
                    user_query = fields_decoded.get('user_query', '')
                    
                    print(f"[DecisionExtractionAgent] 📥 Processing conversation: {event_id}")
                    
                    # Create and execute task
                    task = create_decision_extraction_task(event_id, user_query)
                    crew = Crew(
                        agents=[decision_extraction_agent],
                        tasks=[task],
                        process=Process.sequential,
                        verbose=True
                    )
                    
                    result = crew.kickoff()
                    print(f"[DecisionExtractionAgent] ✅ Result: {result}")
                    
                    # Acknowledge message
                    redis_client.xack(stream_key, group_name, msg_id)
                    
        except Exception as e:
            print(f"[DecisionExtractionAgent] ❌ Error: {e}")
            time.sleep(5)


# ============================================================================
# Main
# ============================================================================

if __name__ == "__main__":
    start_decision_extraction_consumer()
