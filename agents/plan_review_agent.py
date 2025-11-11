"""
Plan Review Agent
Queries strategic plan RAG and interprets based on input query.
Follows: Redis Streams + CloudEvents + CrewAI + Ontology pattern
"""

import redis
import json
import uuid
import time
import os
import requests
from datetime import datetime
from typing import Dict, Any, Optional
from crewai import Agent, Task, Crew
from crewai.tools import tool
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_community.vectorstores import Redis as RedisVectorStore
from langchain.text_splitter import RecursiveCharacterTextSplitter

# Redis connection
redis_client = redis.Redis(host='localhost', port=6379, decode_responses=True)

# RedisJSON fallback helpers (for Redis without JSON module)
def redis_set_json(key: str, value: dict):
    """Set JSON value in Redis, with fallback if RedisJSON not available"""
    try:
        redis_client.json().set(key, "$", value)
    except redis.ResponseError as e:
        if "unknown command" in str(e).lower() or "json.set" in str(e).lower():
            # Fallback to regular SET with JSON string
            redis_client.set(key, json.dumps(value))
        else:
            raise

def redis_get_json(key: str) -> Optional[dict]:
    """Get JSON value from Redis, with fallback if RedisJSON not available"""
    try:
        return redis_client.json().get(key)
    except redis.ResponseError as e:
        if "unknown command" in str(e).lower() or "json.get" in str(e).lower():
            # Fallback to regular GET with JSON parse
            value = redis_client.get(key)
            return json.loads(value) if value else None
        else:
            raise

# Heartbeat functionality
def send_heartbeat(agent_id: str):
    """Send heartbeat to Node.js backend"""
    try:
        api_url = os.getenv('API_URL', 'http://localhost:3001')
        requests.post(
            f"{api_url}/api/managers/{agent_id}/heartbeat",
            timeout=2
        )
    except Exception:
        pass  # Silently fail - heartbeat is not critical

# Heartbeat tracking
last_heartbeat = 0
heartbeat_interval = 30  # Send heartbeat every 30 seconds

# Ontology service (from your existing implementation)
class OntologyService:
    """Simplified ontology service for concept resolution"""
    
    @staticmethod
    def resolve_concept(term: str) -> str:
        """Resolve business term to canonical URI"""
        concept_map = {
            'revenue': 'https://schema.org/revenue',
            'sales': 'https://schema.org/salesRevenue',
            'q4': 'https://vocab.acme.com/fiscal/Q4',
            'quarter': 'https://vocab.acme.com/fiscal/Quarter',
            'target': 'https://vocab.acme.com/planning/Target',
            'plan': 'https://vocab.acme.com/planning/StrategicPlan'
        }
        return concept_map.get(term.lower(), f'https://vocab.acme.com/{term}')
    
    @staticmethod
    def expand_concepts(concept_uri: str) -> list:
        """Expand concept to include related terms via SKOS"""
        expansions = {
            'https://schema.org/revenue': [
                'https://schema.org/totalRevenue',
                'https://vocab.acme.com/financial/GrossRevenue',
                'https://vocab.acme.com/financial/NetRevenue'
            ],
            'https://vocab.acme.com/fiscal/Q4': [
                'https://vocab.acme.com/fiscal/FourthQuarter',
                'https://vocab.acme.com/fiscal/October',
                'https://vocab.acme.com/fiscal/November',
                'https://vocab.acme.com/fiscal/December'
            ]
        }
        return expansions.get(concept_uri, [concept_uri])

ontology = OntologyService()

# LangChain Tools
@tool("query_strategic_plan")
def query_strategic_plan(query: str) -> str:
    """Query the strategic plan RAG system with semantic search."""
    try:
        print(f"[PlanReviewAgent] Querying strategic plan: {query}")
        
        # Resolve ontology concepts in query
        concepts = []
        for term in query.lower().split():
            if term in ['revenue', 'sales', 'q4', 'quarter', 'target', 'plan']:
                concept_uri = ontology.resolve_concept(term)
                concepts.append(concept_uri)
        
        print(f"[PlanReviewAgent] Resolved concepts: {concepts}")
        
        # Simulated RAG retrieval (replace with actual vector store)
        # In production: use RedisVectorStore with embeddings
        strategic_plan_data = {
            "q4_revenue_target": "$45M",
            "q4_growth_target": "18%",
            "q4_initiatives": [
                "Launch holiday marketing campaign",
                "Expand product line by 20 SKUs",
                "Open 3 new retail locations"
            ],
            "q4_budget": "$12M marketing, $8M operations",
            "q4_kpis": {
                "customer_acquisition": 50000,
                "retention_rate": "92%",
                "average_order_value": "$180"
            }
        }
        
        # Format response based on query
        if 'revenue' in query.lower() or 'sales' in query.lower():
            if 'q4' in query.lower() or 'fourth' in query.lower():
                return f"Q4 Revenue Target: {strategic_plan_data['q4_revenue_target']} with {strategic_plan_data['q4_growth_target']} growth"
            
        # Default: return full context
        return json.dumps(strategic_plan_data, indent=2)
        
    except Exception as e:
        print(f"[PlanReviewAgent] Error querying plan: {e}")
        return f"Error querying strategic plan: {str(e)}"

@tool("validate_plan_alignment")
def validate_plan_alignment(proposed_action: str, plan_context: str) -> str:
    """Validate if a proposed action aligns with strategic plan."""
    try:
        # Simple keyword matching (can be enhanced with embeddings)
        plan_lower = plan_context.lower()
        action_lower = proposed_action.lower()
        
        alignment_score = 0
        reasons = []
        
        if any(kw in action_lower for kw in ['marketing', 'campaign', 'customer']):
            if 'marketing' in plan_lower or 'customer' in plan_lower:
                alignment_score += 30
                reasons.append("Aligns with customer acquisition strategy")
        
        if any(kw in action_lower for kw in ['product', 'sku', 'inventory']):
            if 'product' in plan_lower or 'sku' in plan_lower:
                alignment_score += 30
                reasons.append("Aligns with product expansion initiative")
        
        if any(kw in action_lower for kw in ['revenue', 'sales', 'growth']):
            alignment_score += 40
            reasons.append("Directly supports revenue targets")
        
        result = {
            "alignment_score": alignment_score,
            "is_aligned": alignment_score >= 50,
            "reasons": reasons
        }
        
        return json.dumps(result, indent=2)
        
    except Exception as e:
        return f"Error validating alignment: {str(e)}"

# CrewAI Agent Definition
plan_review_agent = Agent(
    role="Strategic Plan Analyst",
    goal="Query and interpret the strategic plan to answer business questions and validate action alignment",
    backstory="""You are an expert strategic planning analyst with deep knowledge of 
    business strategy, financial planning, and organizational alignment. You have access 
    to the company's strategic plan RAG system and can retrieve precise information about 
    targets, initiatives, budgets, and KPIs. You understand ontology concepts like 
    fiscal quarters, revenue types, and planning hierarchies.""",
    tools=[query_strategic_plan, validate_plan_alignment],
    allow_delegation=False,
    verbose=True
)

# CloudEvents Builder
def build_cloudevent(event_type: str, source: str, subject: str, data: Dict[str, Any]) -> Dict[str, Any]:
    """Build CloudEvents 1.0 compliant event"""
    event_id = str(uuid.uuid4())
    return {
        "specversion": "1.0",
        "id": event_id,
        "source": source,
        "type": event_type,
        "subject": subject,
        "time": datetime.utcnow().isoformat() + "Z",
        "datacontenttype": "application/json",
        "dataschema": "https://schemas.acme.com/agents/plan-review-response/1-0-0.json",
        "data": {
            "@context": {
                "@vocab": "https://vocab.acme.com/",
                "revenue": "https://schema.org/revenue",
                "plan": "https://vocab.acme.com/planning/StrategicPlan"
            },
            **data
        }
    }

# Event Bus Publisher
def publish_to_event_bus(event: Dict[str, Any], stream_key: str = "stream:agents:plan-review:responses:v1"):
    """Publish CloudEvent to Redis Stream"""
    try:
        # Store full event in RedisJSON
        redis_set_json(f"event:{event['id']}", event)
        
        # Add pointer to stream
        redis_client.xadd(stream_key, {
            "event_id": event["id"],
            "type": event["type"],
            "subject": event["subject"],
            "dataschema": event["dataschema"]
        })
        
        print(f"[PlanReviewAgent] Published event {event['id']} to {stream_key}")
        return True
    except Exception as e:
        print(f"[PlanReviewAgent] Error publishing event: {e}")
        return False

# Main Agent Execution Loop
def run_plan_review_agent():
    """
    Consume events from Redis Stream, process with CrewAI agent, publish results
    """
    input_stream = "stream:agents:plan-review:requests:v1"
    output_stream = "stream:agents:plan-review:responses:v1"
    consumer_group = "plan-review-agents"
    consumer_name = f"plan-review-{uuid.uuid4().hex[:8]}"
    
    print(f"[PlanReviewAgent] Starting consumer: {consumer_name}")
    
    # Create consumer group (ignore if exists)
    try:
        redis_client.xgroup_create(input_stream, consumer_group, id="$", mkstream=True)
        print(f"[PlanReviewAgent] Created consumer group: {consumer_group}")
    except redis.ResponseError as e:
        if "BUSYGROUP" not in str(e):
            raise
        print(f"[PlanReviewAgent] Consumer group already exists")
    
    # Main processing loop
    while True:
        try:
            # Send heartbeat periodically
            global last_heartbeat
            if time.time() - last_heartbeat > heartbeat_interval:
                send_heartbeat("plan-review-agent")
                last_heartbeat = time.time()
            
            # Read from stream (blocking)
            messages = redis_client.xreadgroup(
                consumer_group,
                consumer_name,
                {input_stream: ">"},
                count=1,
                block=5000
            )
            
            if not messages:
                continue
            
            for stream, entries in messages:
                for message_id, fields in entries:
                    print(f"[PlanReviewAgent] Processing message: {message_id}")
                    
                    # Fetch full event from RedisJSON
                    event_id = fields.get("event_id")
                    if not event_id:
                        print(f"[PlanReviewAgent] No event_id in message")
                        redis_client.xack(input_stream, consumer_group, message_id)
                        continue
                    
                    source_event = redis_get_json(f"event:{event_id}")
                    if not source_event:
                        print(f"[PlanReviewAgent] Event {event_id} not found in RedisJSON")
                        redis_client.xack(input_stream, consumer_group, message_id)
                        continue
                    
                    # Extract query from event data
                    query = source_event.get("data", {}).get("query", "")
                    context = source_event.get("data", {}).get("context", {})
                    
                    print(f"[PlanReviewAgent] Query: {query}")
                    
                    # Create CrewAI task
                    task = Task(
                        description=f"""Analyze this strategic plan query: "{query}"
                        
                        Context: {json.dumps(context, indent=2)}
                        
                        Steps:
                        1. Query the strategic plan RAG system
                        2. Extract relevant targets, initiatives, and KPIs
                        3. If a proposed action is mentioned, validate alignment
                        4. Provide clear, actionable insights
                        
                        Return a JSON response with:
                        - answer: Direct answer to the query
                        - plan_context: Relevant plan excerpts
                        - alignment: If action validation was requested
                        - recommendations: Strategic recommendations
                        """,
                        expected_output="JSON response with answer, context, and recommendations",
                        agent=plan_review_agent
                    )
                    
                    # Execute agent
                    crew = Crew(
                        agents=[plan_review_agent],
                        tasks=[task],
                        verbose=True
                    )
                    
                    result = crew.kickoff()
                    
                    # Build response CloudEvent
                    response_event = build_cloudevent(
                        event_type="com.acme.agents.plan-review.completed",
                        source="urn:agent:plan-review",
                        subject=source_event.get("subject", "strategic-plan"),
                        data={
                            "query": query,
                            "result": str(result),
                            "correlation_id": event_id,
                            "ontology_concepts": [
                                ontology.resolve_concept(term)
                                for term in query.lower().split()
                                if term in ['revenue', 'sales', 'q4', 'quarter', 'target', 'plan']
                            ]
                        }
                    )
                    
                    # Publish response
                    publish_to_event_bus(response_event, output_stream)
                    
                    # ACK message
                    redis_client.xack(input_stream, consumer_group, message_id)
                    print(f"[PlanReviewAgent] Completed message: {message_id}")
                    
        except Exception as e:
            print(f"[PlanReviewAgent] Error in main loop: {e}")
            time.sleep(5)

# Agent Registration
AGENT_REGISTRY_ENTRY = {
    "id": "plan-review-agent",
    "name": "Strategic Plan Review Agent",
    "type": "analysis",
    "capabilities": ["strategic_planning", "rag_query", "plan_interpretation", "alignment_validation"],
    "input_stream": "stream:agents:plan-review:requests:v1",
    "output_stream": "stream:agents:plan-review:responses:v1",
    "input_schema": "https://schemas.acme.com/agents/plan-review-request/1-0-0.json",
    "output_schema": "https://schemas.acme.com/agents/plan-review-response/1-0-0.json",
    "ontology_concepts": [
        "https://vocab.acme.com/planning/StrategicPlan",
        "https://schema.org/revenue",
        "https://vocab.acme.com/fiscal/Quarter"
    ],
    "tools": ["query_strategic_plan", "validate_plan_alignment"],
    "status": "active"
}

if __name__ == "__main__":
    # Register agent
    redis_set_json(
        f"agent:registry:{AGENT_REGISTRY_ENTRY['id']}", 
        AGENT_REGISTRY_ENTRY
    )
    print(f"[PlanReviewAgent] Registered in agent registry")
    
    # Start processing
    run_plan_review_agent()
