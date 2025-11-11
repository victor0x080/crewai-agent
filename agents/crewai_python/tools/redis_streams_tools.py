"""
Redis Streams Tools for CrewAI Agents
Provides CloudEvents-compliant pub/sub via Redis Streams
Following pattern from @agent.md and @crewai-agent-design-pattern.md
"""

import json
import uuid
import time
from typing import Any, Dict, Optional, List
from crewai.tools import tool
import redis
from redis.commands.json.path import Path


class RedisStreamsClient:
    """Singleton Redis client for all agents"""
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance.redis = redis.Redis.from_url("redis://localhost:6379", decode_responses=False)
        return cls._instance
    
    def get_client(self):
        return self.redis


def build_cloudevent(event_type: str, source: str, data: dict, subject: str = None, dataschema: str = None) -> dict:
    """Build CloudEvents 1.0 envelope"""
    return {
        "specversion": "1.0",
        "id": str(uuid.uuid4()),
        "type": event_type,
        "source": source,
        "subject": subject or "",
        "time": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "dataschema": dataschema or "https://schemas.mesh/EventPayload.json",
        "data": data
    }


def publish_cloudevent_raw(stream_key: str, event_type: str, source: str, data: dict, subject: str = None, dataschema: str = None) -> str:
    """
    Publish a CloudEvent to Redis Streams.
    Stores full event in RedisJSON (or regular Redis if RedisJSON not available) and pointer in stream.
    
    Args:
        stream_key: Redis stream key (e.g., 'stream:mco:event:observation')
        event_type: CloudEvents type (e.g., 'mco.event.observation')
        source: Event source URN (e.g., 'urn:acme:agent:sda')
        data: Event payload data
        subject: Optional subject (entity ID)
        dataschema: Optional schema URI
    
    Returns:
        Event ID that was published
    """
    r = RedisStreamsClient().get_client()
    
    # Build CloudEvent
    event = build_cloudevent(event_type, source, data, subject, dataschema)
    event_id = event["id"]
    
    # Store full event (try RedisJSON first, fallback to regular SET)
    try:
        r.json().set(f"event:{event_id}", Path.root_path(), event)
    except redis.exceptions.ResponseError:
        # Fallback to regular SET if RedisJSON not available
        import json
        r.set(f"event:{event_id}", json.dumps(event))
    
    # Add pointer to stream
    r.xadd(stream_key, {
        "event_id": event_id,
        "type": event_type,
        "subject": subject or "",
        "dataschema": dataschema or ""
    })
    
    return event_id


@tool("publish_cloudevent")
def publish_cloudevent(stream_key: str, event_type: str, source: str, data: dict, subject: str = None, dataschema: str = None) -> str:
    """
    Tool wrapper around publish_cloudevent_raw for CrewAI.
    """
    event_id = publish_cloudevent_raw(stream_key, event_type, source, data, subject, dataschema)
    return f"Published event {event_id} to {stream_key}"


@tool("fetch_cloudevent")
def fetch_cloudevent(event_id: str) -> dict:
    """
    Fetch a CloudEvent from Redis by ID (RedisJSON or regular storage).
    
    Args:
        event_id: The CloudEvent ID
    
    Returns:
        CloudEvent dictionary
    """
    r = RedisStreamsClient().get_client()
    
    # Try RedisJSON first, fallback to regular GET
    try:
        event = r.json().get(f"event:{event_id}")
    except redis.exceptions.ResponseError:
        # Fallback to regular GET if RedisJSON not available
        import json
        event_json = r.get(f"event:{event_id}")
        if not event_json:
            raise ValueError(f"Event {event_id} not found")
        event = json.loads(event_json.decode() if isinstance(event_json, bytes) else event_json)
    
    return event


@tool("fetch_schema")
def fetch_schema(schema_uri: str) -> dict:
    """
    Fetch JSON Schema from Redis schema registry.
    
    Args:
        schema_uri: Schema URI (e.g., 'https://schemas.mesh/EventPayload.json')
    
    Returns:
        JSON Schema dictionary
    """
    r = RedisStreamsClient().get_client()
    import base64
    
    # Encode URI for Redis key
    key = f"schema:uri:{base64.urlsafe_b64encode(schema_uri.encode()).decode()}"
    schema = r.json().get(key)
    
    if not schema:
        # Fallback: return minimal schema
        return {"type": "object", "properties": {}}
    
    return schema


@tool("validate_against_schema")
def validate_against_schema(data: dict, schema_uri: str) -> str:
    """
    Validate data against a JSON Schema from registry.
    
    Args:
        data: Data to validate
        schema_uri: Schema URI
    
    Returns:
        Validation result message
    """
    try:
        from jsonschema import validate, Draft202012Validator
        schema = fetch_schema(schema_uri)
        Draft202012Validator(schema).validate(data)
        return f"✓ Data valid against {schema_uri}"
    except Exception as e:
        return f"✗ Validation failed: {str(e)}"


@tool("redis_ack")
def redis_ack(stream_key: str, consumer_group: str, message_id: str) -> str:
    """
    Acknowledge a message in a Redis Stream consumer group.
    Required for completing the event processing lifecycle.
    
    Args:
        stream_key: Redis stream key (e.g., 'stream:route.decisions')
        consumer_group: Consumer group name (e.g., 'google-ads-agent')
        message_id: Message ID to acknowledge (e.g., '1698321456789-0')
    
    Returns:
        Success message
    
    Example:
        redis_ack('stream:route.decisions', 'google-ads-agent', '1698321456789-0')
        → "✓ Acknowledged message 1698321456789-0"
    """
    r = RedisStreamsClient().get_client()
    
    try:
        # XACK returns number of messages acknowledged (should be 1)
        count = r.xack(stream_key, consumer_group, message_id)
        if count > 0:
            return f"✓ Acknowledged message {message_id}"
        else:
            return f"⚠ Message {message_id} was already acknowledged or not found"
    except Exception as e:
        return f"✗ Failed to acknowledge {message_id}: {str(e)}"


# Consumer group utilities (not tools, used by agent runners)

def consume_stream(stream_key: str, consumer_group: str, consumer_name: str, count: int = 10, block: int = 1000) -> List[Dict]:
    """
    Consume messages from Redis Stream using consumer group.
    Returns list of (message_id, event_dict) tuples.
    Handles both CloudEvents format (with event_id) and legacy raw format.
    """
    r = RedisStreamsClient().get_client()
    
    # Ensure consumer group exists
    try:
        r.xgroup_create(stream_key, consumer_group, id='$', mkstream=True)
    except redis.exceptions.ResponseError as e:
        if "BUSYGROUP" not in str(e):
            raise
    
    # Read from stream
    messages = r.xreadgroup(consumer_group, consumer_name, {stream_key: '>'}, count=count, block=block)
    
    results = []
    for stream, entries in messages or []:
        for msg_id, fields in entries:
            # Decode fields
            decoded = {k.decode(): v.decode() for k, v in fields.items()}
            event_id = decoded.get('event_id')
            
            event = None
            
            if event_id:
                # New CloudEvents format: Fetch full event from Redis
                try:
                    # Try RedisJSON first (if available)
                    event = r.json().get(f"event:{event_id}")
                except redis.exceptions.ResponseError:
                    # Fallback to regular GET if RedisJSON not available
                    try:
                        import json
                        event_json = r.get(f"event:{event_id}")
                        if event_json:
                            event = json.loads(event_json.decode() if isinstance(event_json, bytes) else event_json)
                    except Exception:
                        pass
            else:
                # Legacy format: Construct CloudEvent from raw fields
                import json
                try:
                    # Parse inputs if it's a JSON string
                    inputs = decoded.get('inputs', '{}')
                    if isinstance(inputs, str):
                        try:
                            inputs = json.loads(inputs)
                        except:
                            inputs = {}
                    
                    # Build CloudEvent structure from raw fields
                    event = {
                        "specversion": "1.0",
                        "id": decoded.get('task_id', str(uuid.uuid4())),
                        "type": "crewai.task.request",
                        "source": decoded.get('requester', 'nodejs-backend'),
                        "subject": decoded.get('agent_id', ''),
                        "time": decoded.get('timestamp', ''),
                        "dataschema": "https://schemas.mesh/TaskRequest.json",
                        "data": {
                            "task_id": decoded.get('task_id', ''),
                            "agent_id": decoded.get('agent_id', ''),
                            "task_type": decoded.get('task_type', 'generic'),
                            "task_description": decoded.get('task_description', ''),
                            "inputs": inputs,
                            "priority": decoded.get('priority', 'medium'),
                            "timestamp": decoded.get('timestamp', ''),
                            "requester": decoded.get('requester', 'nodejs-backend')
                        }
                    }
                except Exception as e:
                    # Skip malformed messages
                    continue
            
            if event:
                results.append({'message_id': msg_id.decode(), 'event': event})
    
    return results


def ack_message(stream_key: str, consumer_group: str, message_id: str):
    """Acknowledge a message"""
    r = RedisStreamsClient().get_client()
    r.xack(stream_key, consumer_group, message_id)


def nack_to_dlq(stream_key: str, consumer_group: str, message_id: str, event_id: str, reason: str):
    """Send message to DLQ and ack original"""
    r = RedisStreamsClient().get_client()
    r.xadd('stream:dlq', {
        'event_id': event_id,
        'source_stream': stream_key,
        'reason': reason,
        'timestamp': time.time()
    })
    r.xack(stream_key, consumer_group, message_id)
