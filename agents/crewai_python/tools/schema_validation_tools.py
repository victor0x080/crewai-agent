"""
Schema Validation Tools
Validates data against JSON Schema from registry
"""
import json
import requests
from typing import Dict, Any
from crewai.tools import tool
import jsonschema
from jsonschema import Draft202012Validator


# In-memory schema cache
_schema_cache: Dict[str, Dict] = {}


def fetch_schema_from_registry(schema_uri: str) -> Dict[str, Any]:
    """
    Fetch JSON Schema from registry
    
    Args:
        schema_uri: URI of the schema
        
    Returns:
        JSON Schema document
    """
    # Check cache first
    if schema_uri in _schema_cache:
        return _schema_cache[schema_uri]
    
    # For local file paths (development)
    if schema_uri.startswith('./') or schema_uri.startswith('../'):
        # Convert relative path to absolute
        import os
        base_path = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
        schema_path = os.path.join(base_path, '..', schema_uri.lstrip('./'))
        
        with open(schema_path, 'r') as f:
            schema = json.load(f)
            _schema_cache[schema_uri] = schema
            return schema
    
    # For HTTP(S) URIs
    if schema_uri.startswith('http://') or schema_uri.startswith('https://'):
        response = requests.get(schema_uri, timeout=5)
        response.raise_for_status()
        schema = response.json()
        _schema_cache[schema_uri] = schema
        return schema
    
    # For schemas.mesh URIs, try local Adapters folder
    if 'schemas.mesh/adapters' in schema_uri:
        # Extract adapter name and schema file
        # e.g., https://schemas.mesh/adapters/sa360/ActionContract.json
        parts = schema_uri.split('/')
        adapter_name = parts[-2]
        schema_file = parts[-1]
        
        import os
        base_path = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
        schema_path = os.path.join(base_path, '..', 'Adapters', f'adapter-{adapter_name}', 'schemas', schema_file)
        
        if os.path.exists(schema_path):
            with open(schema_path, 'r') as f:
                schema = json.load(f)
                _schema_cache[schema_uri] = schema
                return schema
    
    raise ValueError(f"Cannot fetch schema from URI: {schema_uri}")


@tool("validate_against_schema")
def validate_against_schema(schema_uri: str, data: dict) -> dict:
    """
    Validate data against JSON Schema from registry.
    
    Args:
        schema_uri: URI of the JSON Schema
        data: Data to validate
        
    Returns:
        dict with 'valid' (bool) and 'errors' (list) keys
    """
    try:
        schema = fetch_schema_from_registry(schema_uri)
        validator = Draft202012Validator(schema)
        
        # Validate
        errors = list(validator.iter_errors(data))
        
        if errors:
            error_messages = [
                f"{'.'.join(str(p) for p in e.path)}: {e.message}"
                for e in errors
            ]
            return {
                'valid': False,
                'errors': error_messages
            }
        
        return {'valid': True, 'errors': []}
        
    except Exception as e:
        return {
            'valid': False,
            'errors': [f"Validation error: {str(e)}"]
        }


@tool("fetch_schema")
def fetch_schema(schema_uri: str) -> dict:
    """
    Fetch JSON Schema by URI from the schema registry.
    
    Args:
        schema_uri: URI of the schema
        
    Returns:
        JSON Schema document
    """
    try:
        return fetch_schema_from_registry(schema_uri)
    except Exception as e:
        return {'error': str(e)}


@tool("publish_platform_action")
def publish_platform_action(
    operation: str,
    params: dict,
    platform: str,
    target_entity_type: str = 'campaign',
    target_entity_id: str = None
) -> dict:
    """
    Publish validated action to platform adapter.
    Validates against ActionContract before publishing.
    
    Args:
        operation: Operation name (e.g., 'setCampaignBudget')
        params: Operation parameters
        platform: Platform name (e.g., 'sa360', 'dv360')
        target_entity_type: Entity type (e.g., 'campaign', 'adGroup')
        target_entity_id: Entity ID
        
    Returns:
        dict with 'success' (bool) and 'event_id' or 'errors'
    """
    from tools.redis_streams_tools import RedisStreamsClient, build_cloudevent
    import uuid
    
    # Select correct ActionContract schema
    schema_uri = f"https://schemas.mesh/adapters/{platform}/ActionContract.json"
    
    # Build action payload
    action = {
        'kind': 'action',
        'target': {
            'entityType': target_entity_type,
            'entityId': target_entity_id or params.get('campaignId') or params.get('adGroupId') or 'unknown'
        },
        'operation': operation,
        'params': params
    }
    
    # Validate against ActionContract
    validation = validate_against_schema(schema_uri, action)
    if not validation['valid']:
        return {
            'success': False,
            'errors': validation['errors']
        }
    
    # Build CloudEvent
    event_id = str(uuid.uuid4())
    cloudevent = build_cloudevent(
        event_type='mco.event.action',
        source=f'urn:agent:decision',
        data=action,
        subject=action['target']['entityId'],
        dataschema=schema_uri
    )
    cloudevent['id'] = event_id
    
    # Publish to stream:mco:event:action
    r = RedisStreamsClient().get_client()
    
    # Store full event in Redis (try RedisJSON first, fallback to SET)
    try:
        r.json().set(f"event:{event_id}", '$', cloudevent)
    except Exception:
        r.set(f"event:{event_id}", json.dumps(cloudevent))
    
    # Add pointer to stream
    r.xadd('stream:mco:event:action', {
        'event_id': event_id,
        'type': 'mco.event.action',
        'subject': cloudevent['subject'],
        'dataschema': schema_uri
    })
    
    return {
        'success': True,
        'event_id': event_id,
        'platform': platform,
        'operation': operation
    }
