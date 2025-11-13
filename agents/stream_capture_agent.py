"""
Stream Capture Agent
Monitors event streams and posts events when specific conditions are met.
Follows: Redis Streams + CloudEvents + CrewAI + Ontology pattern
"""

import redis
import json
import uuid
import re
import os
import requests
from datetime import datetime
from typing import Dict, Any, List, Callable, Optional
from crewai import Agent, Task, Crew
from crewai.tools import tool
import time

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

def redis_get_json(key: str):
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

# Ontology service
class OntologyService:
    """Ontology concept resolution for event matching"""
    
    @staticmethod
    def resolve_concept(term: str) -> str:
        """Resolve event term to canonical URI"""
        concept_map = {
            'price': 'https://schema.org/price',
            'inventory': 'https://vocab.acme.com/inventory/StockLevel',
            'order': 'https://schema.org/Order',
            'customer': 'https://schema.org/Customer',
            'threshold': 'https://vocab.acme.com/monitoring/Threshold',
            'alert': 'https://vocab.acme.com/monitoring/Alert'
        }
        return concept_map.get(term.lower(), f'https://vocab.acme.com/{term}')
    
    @staticmethod
    def expand_concepts(concept_uri: str) -> List[str]:
        """Expand concept to related terms via SKOS"""
        expansions = {
            'https://schema.org/price': [
                'https://vocab.acme.com/pricing/ListPrice',
                'https://vocab.acme.com/pricing/SalePrice',
                'https://vocab.acme.com/pricing/MarkdownPrice'
            ],
            'https://vocab.acme.com/inventory/StockLevel': [
                'https://vocab.acme.com/inventory/Available',
                'https://vocab.acme.com/inventory/Reserved',
                'https://vocab.acme.com/inventory/OnOrder'
            ]
        }
        return expansions.get(concept_uri, [concept_uri])

ontology = OntologyService()

# Event Pattern Matcher
class EventPatternMatcher:
    """Matches events against configured patterns"""
    
    def __init__(self):
        self.patterns = {}
    
    def add_pattern(self, pattern_id: str, pattern: Dict[str, Any]):
        """Add a pattern to monitor"""
        self.patterns[pattern_id] = pattern
        print(f"[StreamCaptureAgent] Added pattern: {pattern_id}")
    
    def match(self, event: Dict[str, Any]) -> List[str]:
        """Check if event matches any patterns"""
        matches = []
        
        for pattern_id, pattern in self.patterns.items():
            if self._matches_pattern(event, pattern):
                matches.append(pattern_id)
        
        return matches
    
    def _matches_pattern(self, event: Dict[str, Any], pattern: Dict[str, Any]) -> bool:
        """Check if event matches a specific pattern"""
        # Match event type
        if 'event_type' in pattern:
            if event.get('type') != pattern['event_type']:
                return False
        
        # Match subject pattern (regex)
        if 'subject_pattern' in pattern:
            subject = event.get('subject', '')
            if not re.match(pattern['subject_pattern'], subject):
                return False
        
        # Match data conditions
        if 'conditions' in pattern:
            data = event.get('data', {})
            for condition in pattern['conditions']:
                field = condition.get('field')
                operator = condition.get('operator')
                value = condition.get('value')
                
                if field not in data:
                    return False
                
                actual_value = data[field]
                
                if operator == 'eq' and actual_value != value:
                    return False
                elif operator == 'gt' and not (actual_value > value):
                    return False
                elif operator == 'lt' and not (actual_value < value):
                    return False
                elif operator == 'gte' and not (actual_value >= value):
                    return False
                elif operator == 'lte' and not (actual_value <= value):
                    return False
                elif operator == 'contains' and value not in str(actual_value):
                    return False
        
        return True

# Global pattern matcher
pattern_matcher = EventPatternMatcher()

# LangChain Tools
@tool("register_pattern")
def register_pattern(pattern_id: str, pattern_config: str) -> str:
    """
    Register a new event pattern to monitor.
    
    Args:
        pattern_id: Unique identifier for the pattern
        pattern_config: JSON string with pattern configuration
        
    Example:
    {
        "event_type": "com.acme.inventory.stock.updated",
        "subject_pattern": "SKU-.*",
        "conditions": [
            {"field": "stock_level", "operator": "lt", "value": 10}
        ],
        "alert_type": "low_stock"
    }
    
    Returns:
        Status message
    """
    try:
        pattern = json.loads(pattern_config) if isinstance(pattern_config, str) else pattern_config
        pattern_matcher.add_pattern(pattern_id, pattern)
        
        return json.dumps({
            "status": "registered",
            "pattern_id": pattern_id,
            "pattern": pattern
        })
    except Exception as e:
        return json.dumps({"error": str(e)})

@tool("check_event_match")
def check_event_match(event_json: str) -> str:
    """
    Check if an event matches any registered patterns.
    
    Args:
        event_json: JSON string of the event to check
    
    Returns:
        JSON with matching pattern IDs
    """
    try:
        event = json.loads(event_json) if isinstance(event_json, str) else event_json
        matches = pattern_matcher.match(event)
        
        return json.dumps({
            "matches": matches,
            "match_count": len(matches),
            "event_id": event.get('id', 'unknown')
        })
    except Exception as e:
        return json.dumps({"error": str(e)})

@tool("analyze_event_stream")
def analyze_event_stream(stream_name: str, pattern_ids: str) -> str:
    """
    Analyze recent events in a stream for pattern matches.
    
    Args:
        stream_name: Redis stream key to analyze
        pattern_ids: Comma-separated list of pattern IDs to check
    
    Returns:
        JSON with match statistics
    """
    try:
        # Read recent events from stream
        entries = redis_client.xrevrange(stream_name, count=100)
        
        pattern_id_list = [p.strip() for p in pattern_ids.split(',')]
        stats = {pid: {"matches": 0, "events": []} for pid in pattern_id_list}
        
        for entry_id, fields in entries:
            event_id = fields.get('event_id')
            if event_id:
                event = redis_client.json().get(f"event:{event_id}")
                if event:
                    matches = pattern_matcher.match(event)
                    for match in matches:
                        if match in stats:
                            stats[match]["matches"] += 1
                            stats[match]["events"].append({
                                "event_id": event_id,
                                "type": event.get('type'),
                                "time": event.get('time')
                            })
        
        return json.dumps(stats, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)})

# CrewAI Agent Definition
stream_capture_agent = Agent(
    role="Event Stream Monitor",
    goal="Monitor event streams for specific patterns and trigger alerts when conditions are met",
    backstory="""You are an expert event monitoring specialist with deep knowledge of 
    event-driven architectures, pattern matching, and real-time alerting. You understand 
    CloudEvents, Redis Streams, and ontology-based event classification. You can define 
    complex patterns, monitor multiple streams simultaneously, and trigger appropriate 
    actions when patterns are detected. You ensure no critical events are missed.""",
    tools=[register_pattern, check_event_match, analyze_event_stream],
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
        "dataschema": "https://schemas.acme.com/agents/stream-capture-alert/1-0-0.json",
        "data": {
            "@context": {
                "@vocab": "https://vocab.acme.com/",
                "alert": "https://vocab.acme.com/monitoring/Alert",
                "threshold": "https://vocab.acme.com/monitoring/Threshold"
            },
            **data
        }
    }

# Event Bus Publisher
def publish_to_event_bus(event: Dict[str, Any], stream_key: str = "stream:alerts:v1"):
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
        
        print(f"[StreamCaptureAgent] Published alert {event['id']} to {stream_key}")
        return True
    except Exception as e:
        print(f"[StreamCaptureAgent] Error publishing alert: {e}")
        return False

# Stream Monitor
def monitor_stream(stream_name: str, monitored_patterns: Dict[str, Dict]):
    """
    Monitor a stream for pattern matches
    
    Args:
        stream_name: Redis stream to monitor
        monitored_patterns: Dict of pattern_id -> pattern_config
    """
    consumer_group = "stream-capture-monitors"
    consumer_name = f"monitor-{uuid.uuid4().hex[:8]}"
    
    print(f"[StreamCaptureAgent] Monitoring stream: {stream_name}")
    
    # Register patterns
    for pattern_id, pattern in monitored_patterns.items():
        pattern_matcher.add_pattern(pattern_id, pattern)
    
    # Create consumer group
    try:
        redis_client.xgroup_create(stream_name, consumer_group, id="$", mkstream=True)
    except redis.ResponseError as e:
        if "BUSYGROUP" not in str(e):
            raise
    
    # Monitor loop
    while True:
        try:
            # Send heartbeat periodically
            global last_heartbeat
            if time.time() - last_heartbeat > heartbeat_interval:
                send_heartbeat("stream-capture-agent")
                last_heartbeat = time.time()
            
            messages = redis_client.xreadgroup(
                consumer_group,
                consumer_name,
                {stream_name: ">"},
                count=10,
                block=1000
            )
            
            if not messages:
                continue
            
            for stream, entries in messages:
                for message_id, fields in entries:
                    event_id = fields.get("event_id")
                    if not event_id:
                        redis_client.xack(stream_name, consumer_group, message_id)
                        continue
                    
                    # Fetch full event
                    event = redis_get_json(f"event:{event_id}")
                    if not event:
                        redis_client.xack(stream_name, consumer_group, message_id)
                        continue
                    
                    # Check for matches
                    matches = pattern_matcher.match(event)
                    
                    if matches:
                        print(f"[StreamCaptureAgent] Pattern matches: {matches}")
                        
                        # Create alert event
                        for pattern_id in matches:
                            pattern = monitored_patterns.get(pattern_id, {})
                            
                            alert_event = build_cloudevent(
                                event_type="com.acme.monitoring.pattern.matched",
                                source="urn:agent:stream-capture",
                                subject=event.get('subject', 'unknown'),
                                data={
                                    "pattern_id": pattern_id,
                                    "pattern_type": pattern.get('alert_type', 'generic'),
                                    "matched_event_id": event_id,
                                    "matched_event_type": event.get('type'),
                                    "matched_event_data": event.get('data', {}),
                                    "timestamp": datetime.utcnow().isoformat() + "Z",
                                    "severity": pattern.get('severity', 'medium'),
                                    "ontology_concepts": [
                                        ontology.resolve_concept(term)
                                        for term in pattern_id.split('_')
                                    ]
                                }
                            )
                            
                            # Publish alert
                            publish_to_event_bus(alert_event, "stream:alerts:v1")
                    
                    # ACK message
                    redis_client.xack(stream_name, consumer_group, message_id)
                    
        except Exception as e:
            print(f"[StreamCaptureAgent] Monitor error: {e}")
            time.sleep(5)

# Main Agent Execution
def run_stream_capture_agent():
    """
    Consume monitoring requests and spawn stream monitors
    """
    input_stream = "stream:agents:stream-capture:requests:v1"
    consumer_group = "stream-capture-agents"
    consumer_name = f"stream-capture-{uuid.uuid4().hex[:8]}"
    
    print(f"[StreamCaptureAgent] Starting consumer: {consumer_name}")
    
    # Create consumer group
    try:
        redis_client.xgroup_create(input_stream, consumer_group, id="$", mkstream=True)
    except redis.ResponseError as e:
        if "BUSYGROUP" not in str(e):
            raise
    
    # Example: Start monitoring inventory stream with low stock pattern
    LOW_STOCK_PATTERN = {
        "event_type": "com.acme.inventory.stock.updated",
        "conditions": [
            {"field": "stock_level", "operator": "lt", "value": 10}
        ],
        "alert_type": "low_stock",
        "severity": "high"
    }
    
    PRICE_CHANGE_PATTERN = {
        "event_type": "com.acme.pricing.price.updated",
        "conditions": [
            {"field": "price_change_percent", "operator": "gt", "value": 20}
        ],
        "alert_type": "large_price_change",
        "severity": "medium"
    }
    
    # Start monitoring (in production, these would come from requests)
    import threading
    
    inventory_thread = threading.Thread(
        target=monitor_stream,
        args=("stream:inventory:stock-updates:v1", {"low_stock": LOW_STOCK_PATTERN})
    )
    inventory_thread.daemon = True
    inventory_thread.start()
    
    pricing_thread = threading.Thread(
        target=monitor_stream,
        args=("stream:pricing:price-updated:v1", {"large_price_change": PRICE_CHANGE_PATTERN})
    )
    pricing_thread.daemon = True
    pricing_thread.start()
    
    print(f"[StreamCaptureAgent] Monitoring threads started")
    
    # Keep main thread alive
    while True:
        # Send heartbeat periodically
        global last_heartbeat
        if time.time() - last_heartbeat > heartbeat_interval:
            send_heartbeat("stream-capture")
            last_heartbeat = time.time()
        time.sleep(60)
        print(f"[StreamCaptureAgent] Active monitors: inventory, pricing")

# Agent Registration
AGENT_REGISTRY_ENTRY = {
    "id": "stream-capture-agent",
    "name": "Stream Capture Agent",
    "type": "monitoring",
    "capabilities": ["event_monitoring", "pattern_matching", "alert_generation", "stream_analysis"],
    "input_stream": "stream:agents:stream-capture:requests:v1",
    "output_stream": "stream:alerts:v1",
    "input_schema": "https://schemas.acme.com/agents/stream-capture-request/1-0-0.json",
    "output_schema": "https://schemas.acme.com/agents/stream-capture-alert/1-0-0.json",
    "monitored_streams": [
        "stream:inventory:stock-updates:v1",
        "stream:pricing:price-updated:v1"
    ],
    "ontology_concepts": [
        "https://vocab.acme.com/monitoring/Alert",
        "https://vocab.acme.com/monitoring/Threshold",
        "https://vocab.acme.com/inventory/StockLevel"
    ],
    "tools": ["register_pattern", "check_event_match", "analyze_event_stream"],
    "status": "active"
}

if __name__ == "__main__":
    # Register agent
    redis_set_json(
        f"agent:registry:{AGENT_REGISTRY_ENTRY['id']}", 
        AGENT_REGISTRY_ENTRY
    )
    print(f"[StreamCaptureAgent] Registered in agent registry")
    
    # Start monitoring
    run_stream_capture_agent()
