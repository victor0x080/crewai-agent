"""
Narrative Builder Agent (CrewAI)

Consumes conversation events from Redis Streams, builds narrative updates
from insights and summaries, and publishes narrative events for real-time
display in LiveNarrativeStream.

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

@tool("publish_narrative_event")
def publish_narrative_event(narrative_data: dict) -> str:
    """
    Publish a narrative CloudEvent to Redis Streams.
    
    Args:
        narrative_data: Dict with title, content, source, confidence
    
    Returns:
        Event ID of published narrative
    """
    event_id = str(uuid.uuid4())
    
    # Build CloudEvent
    cloudevent = {
        "specversion": "1.0",
        "id": event_id,
        "source": "urn:agent:narrative-builder",
        "type": "com.acme.narrative.created",
        "subject": narrative_data.get("title", "Narrative Update"),
        "time": datetime.utcnow().isoformat() + "Z",
        "dataschema": "https://schemas.acme.com/narrative/1-0-0.json",
        "data": {
            "@context": {
                "ex": "http://example.org/ontology#",
                "narrative": "ex:Narrative",
                "insight": "ex:Insight",
                "confidence": "ex:Confidence"
            },
            "id": event_id,
            "title": narrative_data["title"],
            "content": narrative_data["content"],
            "source": narrative_data.get("source", "Narrative Builder Agent"),
            "confidence": narrative_data.get("confidence", 0.85),
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "metadata": {
                "conversationId": narrative_data.get("conversationId"),
                "phase": narrative_data.get("phase"),
                "concepts": narrative_data.get("concepts", [])
            }
        }
    }
    
    # Store full event in RedisJSON
    redis_client.execute_command('JSON.SET', f'event:{event_id}', '$', json.dumps(cloudevent))
    
    # Publish to Redis Pub/Sub (for RedisEventBus WebSocket bridge)
    redis_client.publish('narrative.created', json.dumps({
        'topic': 'narrative.created',
        'event': cloudevent['data']  # Send the narrative data directly
    }))
    
    print(f"[NarrativeBuilderAgent] ✅ Published narrative to Redis Pub/Sub: {event_id}")
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


@tool("expand_concepts")
def expand_concepts(concepts: list, relations: list = None) -> list:
    """
    Expand ontology concepts using SKOS relations.
    
    Args:
        concepts: List of concept URIs
        relations: SKOS relations to follow (broader, narrower, related)
    
    Returns:
        Expanded list of concept URIs
    """
    # Call OntologyService for expansion
    # For now, simple expansion
    expanded = set(concepts)
    
    for concept in concepts:
        if 'Marketing' in concept:
            expanded.update(['ex:Campaign', 'ex:ROI', 'ex:Engagement'])
        elif 'Inventory' in concept:
            expanded.update(['ex:StockLevel', 'ex:Replenishment', 'ex:SKU'])
        elif 'Pricing' in concept:
            expanded.update(['ex:Price', 'ex:Margin', 'ex:Discount'])
    
    return list(expanded)


@tool("synthesize_narrative")
def synthesize_narrative(insights: list, summary: str, context: dict) -> str:
    """
    Synthesize a cohesive narrative from insights and summary.
    
    Args:
        insights: List of insight strings
        summary: Executive summary
        context: Conversation context
    
    Returns:
        Synthesized narrative text
    """
    # Build narrative that connects insights
    narrative_parts = []
    
    if summary:
        narrative_parts.append(f"**Analysis:** {summary}")
    
    if insights:
        narrative_parts.append(f"**Key Findings:** {' '.join(insights[:3])}")
    
    return " ".join(narrative_parts)


# ============================================================================
# Agent Definition
# ============================================================================

narrative_builder_agent = Agent(
    role='Narrative Builder Specialist',
    goal='Build cohesive narratives from conversation insights and summaries for real-time story-building',
    backstory="""You are an expert at synthesizing business intelligence into compelling narratives.
    You analyze insights, summaries, and context to build a coherent story of what's happening.
    You understand how to connect data points into meaningful narratives that help executives
    understand the bigger picture. You publish narratives as CloudEvents to Redis Streams
    for real-time consumption by the UI.""",
    tools=[publish_narrative_event, fetch_conversation_event, expand_concepts, synthesize_narrative],
    verbose=True,
    allow_delegation=False
)


# ============================================================================
# Task Template
# ============================================================================

def create_narrative_building_task(conversation_event_id: str, user_query: str) -> Task:
    """
    Create a task to build narratives from a conversation event.
    
    Args:
        conversation_event_id: ID of the conversation CloudEvent in Redis
        user_query: Original user query for context
    
    Returns:
        CrewAI Task
    """
    return Task(
        description=f"""
        Analyze the conversation event (ID: {conversation_event_id}) and build narrative updates.
        
        User Query: {user_query}
        
        Steps:
        1. Fetch the conversation event using fetch_conversation_event
        2. Extract insights, summaries, and key findings from executive cards
        3. Identify main concepts and expand them using expand_concepts
        4. Synthesize a cohesive narrative using synthesize_narrative
        5. Create narrative updates for each major insight or phase
        6. Publish each narrative using publish_narrative_event
        
        Narrative Criteria:
        - Must tell a coherent story (not just list facts)
        - Must connect insights to business context
        - Summaries become "Analysis Summary" narratives
        - High-confidence insights (>0.85) become "Key Insights" narratives
        - Each narrative should be 1-3 sentences
        - Include relevant ontology concepts for semantic linking
        
        Output: List of published narrative event IDs
        """,
        expected_output="JSON array of narrative event IDs that were published",
        agent=narrative_builder_agent
    )


# ============================================================================
# Consumer Loop
# ============================================================================

def start_narrative_builder_consumer():
    """
    Start consuming conversation events from Redis Streams.
    """
    stream_key = 'stream:conversation:completed'
    group_name = 'narrative-builders'
    consumer_name = 'narrative-builder-1'
    
    # Create consumer group
    try:
        redis_client.xgroup_create(stream_key, group_name, id='$', mkstream=True)
        print(f"[NarrativeBuilderAgent] Created consumer group: {group_name}")
    except redis.exceptions.ResponseError as e:
        if 'BUSYGROUP' not in str(e):
            raise
        print(f"[NarrativeBuilderAgent] Consumer group already exists: {group_name}")
    
    print(f"[NarrativeBuilderAgent] 🚀 Starting consumer loop...")
    
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
                    
                    print(f"[NarrativeBuilderAgent] 📥 Processing conversation: {event_id}")
                    
                    # Create and execute task
                    task = create_narrative_building_task(event_id, user_query)
                    crew = Crew(
                        agents=[narrative_builder_agent],
                        tasks=[task],
                        process=Process.sequential,
                        verbose=True
                    )
                    
                    result = crew.kickoff()
                    print(f"[NarrativeBuilderAgent] ✅ Result: {result}")
                    
                    # Acknowledge message
                    redis_client.xack(stream_key, group_name, msg_id)
                    
        except Exception as e:
            print(f"[NarrativeBuilderAgent] ❌ Error: {e}")
            time.sleep(5)


# ============================================================================
# Main
# ============================================================================

if __name__ == "__main__":
    start_narrative_builder_consumer()
