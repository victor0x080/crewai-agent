"""
System Call (Zapier) Agent
Calls external system APIs via Zapier integration and posts results to event bus.
Follows: Redis Streams + CloudEvents + CrewAI + Ontology pattern
"""

import redis
import json
import uuid
import requests
import os
from datetime import datetime
from typing import Dict, Any, Optional
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

# Zapier webhook URL (set via environment variable)
ZAPIER_WEBHOOK_BASE = os.getenv('ZAPIER_WEBHOOK_URL', 'https://hooks.zapier.com/hooks/catch/')

# Ontology service
class OntologyService:
    """Ontology concept resolution for system integrations"""
    
    @staticmethod
    def resolve_concept(term: str) -> str:
        """Resolve system term to canonical URI"""
        concept_map = {
            'crm': 'https://vocab.acme.com/systems/CRM',
            'email': 'https://schema.org/EmailMessage',
            'slack': 'https://vocab.acme.com/systems/Slack',
            'salesforce': 'https://vocab.acme.com/systems/Salesforce',
            'hubspot': 'https://vocab.acme.com/systems/HubSpot',
            'webhook': 'https://vocab.acme.com/integration/Webhook',
            'api_call': 'https://vocab.acme.com/integration/APICall'
        }
        return concept_map.get(term.lower(), f'https://vocab.acme.com/{term}')
    
    @staticmethod
    def map_system_field(system: str, field: str) -> str:
        """Map system-specific field to canonical field"""
        field_mappings = {
            'salesforce': {
                'account_id': 'https://vocab.acme.com/crm/AccountId',
                'opportunity_id': 'https://vocab.acme.com/crm/OpportunityId',
                'contact_email': 'https://schema.org/email'
            },
            'hubspot': {
                'contact_id': 'https://vocab.acme.com/crm/ContactId',
                'deal_id': 'https://vocab.acme.com/crm/DealId',
                'email': 'https://schema.org/email'
            }
        }
        return field_mappings.get(system.lower(), {}).get(field.lower(), f'https://vocab.acme.com/{field}')

ontology = OntologyService()

# Zapier Integration Manager
class ZapierIntegration:
    """Manages Zapier webhook calls"""
    
    def __init__(self):
        self.webhook_configs = {
            'salesforce': {
                'create_lead': f'{ZAPIER_WEBHOOK_BASE}/{{zap_id}}/salesforce-create-lead/',
                'update_opportunity': f'{ZAPIER_WEBHOOK_BASE}/{{zap_id}}/salesforce-update-opp/',
                'create_task': f'{ZAPIER_WEBHOOK_BASE}/{{zap_id}}/salesforce-create-task/'
            },
            'hubspot': {
                'create_contact': f'{ZAPIER_WEBHOOK_BASE}/{{zap_id}}/hubspot-create-contact/',
                'update_deal': f'{ZAPIER_WEBHOOK_BASE}/{{zap_id}}/hubspot-update-deal/'
            },
            'slack': {
                'post_message': f'{ZAPIER_WEBHOOK_BASE}/{{zap_id}}/slack-post-message/',
                'create_channel': f'{ZAPIER_WEBHOOK_BASE}/{{zap_id}}/slack-create-channel/'
            },
            'email': {
                'send_email': f'{ZAPIER_WEBHOOK_BASE}/{{zap_id}}/send-email/'
            }
        }
    
    def call_webhook(self, system: str, action: str, payload: Dict[str, Any], zap_id: str = None) -> Dict[str, Any]:
        """
        Call Zapier webhook for a system action
        
        Args:
            system: Target system (salesforce, hubspot, slack, email)
            action: Action to perform (create_lead, send_email, etc.)
            payload: Data to send to the system
            zap_id: Zapier zap ID (optional if using env vars)
        
        Returns:
            Response from Zapier
        """
        try:
            if system not in self.webhook_configs:
                return {"error": f"System '{system}' not configured"}
            
            if action not in self.webhook_configs[system]:
                return {"error": f"Action '{action}' not found for system '{system}'"}
            
            # Get webhook URL
            webhook_url = self.webhook_configs[system][action]
            
            # Use env var for zap_id if not provided
            if not zap_id:
                zap_id = os.getenv(f'ZAPIER_{system.upper()}_{action.upper()}_ID', 'demo_id')
            
            webhook_url = webhook_url.format(zap_id=zap_id)
            
            print(f"[ZapierIntegration] Calling {system}.{action}")
            print(f"[ZapierIntegration] Webhook URL: {webhook_url}")
            print(f"[ZapierIntegration] Payload: {json.dumps(payload, indent=2)}")
            
            # For demo purposes, simulate the call if using demo_id
            if 'demo_id' in webhook_url:
                return {
                    "status": "success",
                    "message": f"Demo mode: Would call {system}.{action}",
                    "webhook_url": webhook_url,
                    "payload": payload,
                    "simulated": True
                }
            
            # Make actual webhook call
            response = requests.post(
                webhook_url,
                json=payload,
                headers={'Content-Type': 'application/json'},
                timeout=30
            )
            
            response.raise_for_status()
            
            return {
                "status": "success",
                "status_code": response.status_code,
                "response": response.json() if response.content else {},
                "simulated": False
            }
            
        except requests.RequestException as e:
            print(f"[ZapierIntegration] Error calling webhook: {e}")
            return {
                "status": "error",
                "error": str(e),
                "system": system,
                "action": action
            }
        except Exception as e:
            print(f"[ZapierIntegration] Unexpected error: {e}")
            return {
                "status": "error",
                "error": str(e)
            }

zapier = ZapierIntegration()

# LangChain Tools
@tool("call_salesforce_api")
def call_salesforce_api(action: str, data: str) -> str:
    """
    Call Salesforce API via Zapier.
    
    Actions: create_lead, update_opportunity, create_task
    
    Example data for create_lead:
    {
        "first_name": "John",
        "last_name": "Doe",
        "email": "john.doe@example.com",
        "company": "Acme Corp",
        "phone": "+1-555-123-4567"
    }
    
    Returns:
        JSON response from Salesforce
    """
    try:
        payload = json.loads(data) if isinstance(data, str) else data
        
        # Add ontology context
        payload["@context"] = {
            "@vocab": "https://vocab.acme.com/",
            "crm": ontology.resolve_concept('salesforce')
        }
        
        result = zapier.call_webhook('salesforce', action, payload)
        return json.dumps(result, indent=2)
        
    except Exception as e:
        return json.dumps({"error": str(e)})

@tool("call_hubspot_api")
def call_hubspot_api(action: str, data: str) -> str:
    """
    Call HubSpot API via Zapier.
    
    Actions: create_contact, update_deal
    
    Example data for create_contact:
    {
        "email": "contact@example.com",
        "firstname": "Jane",
        "lastname": "Smith",
        "company": "Example Inc",
        "phone": "+1-555-987-6543"
    }
    
    Returns:
        JSON response from HubSpot
    """
    try:
        payload = json.loads(data) if isinstance(data, str) else data
        
        payload["@context"] = {
            "@vocab": "https://vocab.acme.com/",
            "crm": ontology.resolve_concept('hubspot')
        }
        
        result = zapier.call_webhook('hubspot', action, payload)
        return json.dumps(result, indent=2)
        
    except Exception as e:
        return json.dumps({"error": str(e)})

@tool("post_to_slack")
def post_to_slack(channel: str, message: str, attachments: str = "") -> str:
    """
    Post message to Slack via Zapier.
    
    Args:
        channel: Slack channel name (e.g., #alerts, #sales)
        message: Message text
        attachments: JSON string with message attachments (optional)
    
    Returns:
        JSON response from Slack
    """
    try:
        payload = {
            "channel": channel,
            "text": message,
            "@context": {
                "@vocab": "https://vocab.acme.com/",
                "slack": ontology.resolve_concept('slack')
            }
        }
        
        if attachments:
            payload["attachments"] = json.loads(attachments) if isinstance(attachments, str) else attachments
        
        result = zapier.call_webhook('slack', 'post_message', payload)
        return json.dumps(result, indent=2)
        
    except Exception as e:
        return json.dumps({"error": str(e)})

@tool("send_email")
def send_email(to: str, subject: str, body: str, cc: str = "") -> str:
    """
    Send email via Zapier.
    
    Args:
        to: Recipient email address
        subject: Email subject
        body: Email body (can include HTML)
        cc: CC recipients (comma-separated, optional)
    
    Returns:
        JSON response from email service
    """
    try:
        payload = {
            "to": to,
            "subject": subject,
            "body": body,
            "@context": {
                "@vocab": "https://vocab.acme.com/",
                "email": ontology.resolve_concept('email')
            }
        }
        
        if cc:
            payload["cc"] = cc
        
        result = zapier.call_webhook('email', 'send_email', payload)
        return json.dumps(result, indent=2)
        
    except Exception as e:
        return json.dumps({"error": str(e)})

@tool("validate_system_credentials")
def validate_system_credentials(system: str) -> str:
    """
    Validate that credentials are configured for a system.
    
    Args:
        system: System name (salesforce, hubspot, slack, email)
    
    Returns:
        JSON with validation status
    """
    try:
        zap_id_key = f'ZAPIER_{system.upper()}_ID'
        has_credentials = os.getenv(zap_id_key) is not None
        
        return json.dumps({
            "system": system,
            "configured": has_credentials,
            "env_var": zap_id_key,
            "demo_mode": not has_credentials
        })
        
    except Exception as e:
        return json.dumps({"error": str(e)})

# CrewAI Agent Definition
system_call_agent = Agent(
    role="System Integration Specialist",
    goal="Execute API calls to external systems via Zapier and return results",
    backstory="""You are an expert system integration engineer with deep knowledge of 
    CRM systems (Salesforce, HubSpot), communication platforms (Slack, Email), and API 
    integrations. You understand Zapier webhooks, data transformation, error handling, 
    and retry strategies. You ensure data is properly formatted, validated, and mapped 
    using ontology concepts before sending to external systems. You always verify 
    credentials and handle errors gracefully.""",
    tools=[
        call_salesforce_api,
        call_hubspot_api,
        post_to_slack,
        send_email,
        validate_system_credentials
    ],
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
        "dataschema": "https://schemas.acme.com/agents/system-call-response/1-0-0.json",
        "data": {
            "@context": {
                "@vocab": "https://vocab.acme.com/",
                "api_call": "https://vocab.acme.com/integration/APICall",
                "webhook": "https://vocab.acme.com/integration/Webhook"
            },
            **data
        }
    }

# Event Bus Publisher
def publish_to_event_bus(event: Dict[str, Any], stream_key: str = "stream:agents:system-call:responses:v1"):
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
        
        print(f"[SystemCallAgent] Published event {event['id']} to {stream_key}")
        return True
    except Exception as e:
        print(f"[SystemCallAgent] Error publishing event: {e}")
        return False

# Main Agent Execution Loop
def run_system_call_agent():
    """
    Consume system call requests from Redis Stream, execute via Zapier, publish results
    """
    input_stream = "stream:agents:system-call:requests:v1"
    output_stream = "stream:agents:system-call:responses:v1"
    consumer_group = "system-call-agents"
    consumer_name = f"system-call-{uuid.uuid4().hex[:8]}"
    
    print(f"[SystemCallAgent] Starting consumer: {consumer_name}")
    
    # Create consumer group
    try:
        redis_client.xgroup_create(input_stream, consumer_group, id="$", mkstream=True)
        print(f"[SystemCallAgent] Created consumer group: {consumer_group}")
    except redis.ResponseError as e:
        if "BUSYGROUP" not in str(e):
            raise
        print(f"[SystemCallAgent] Consumer group already exists")
    
    # Main processing loop
    while True:
        try:
            # Send heartbeat periodically
            global last_heartbeat
            if time.time() - last_heartbeat > heartbeat_interval:
                send_heartbeat("system-call-zapier-agent")
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
                    print(f"[SystemCallAgent] Processing message: {message_id}")
                    
                    # Fetch full event from RedisJSON
                    event_id = fields.get("event_id")
                    if not event_id:
                        redis_client.xack(input_stream, consumer_group, message_id)
                        continue
                    
                    source_event = redis_get_json(f"event:{event_id}")
                    if not source_event:
                        redis_client.xack(input_stream, consumer_group, message_id)
                        continue
                    
                    # Extract system call parameters
                    data = source_event.get("data", {})
                    target_system = data.get("system", "")
                    action = data.get("action", "")
                    payload = data.get("payload", {})
                    
                    print(f"[SystemCallAgent] System: {target_system}, Action: {action}")
                    
                    # Create CrewAI task
                    task = Task(
                        description=f"""Execute this system API call:
                        
                        System: {target_system}
                        Action: {action}
                        Payload: {json.dumps(payload, indent=2)}
                        
                        Steps:
                        1. Validate system credentials are configured
                        2. Map payload fields using ontology
                        3. Execute the API call via Zapier webhook
                        4. Handle any errors with retry logic if needed
                        5. Return the result with proper context
                        
                        Return JSON with:
                        - status: success/error
                        - result: API response
                        - system: Target system
                        - action: Action performed
                        - ontology_context: Mapped concepts
                        """,
                        expected_output="JSON response with API call result",
                        agent=system_call_agent
                    )
                    
                    # Execute agent
                    crew = Crew(
                        agents=[system_call_agent],
                        tasks=[task],
                        verbose=True
                    )
                    
                    result = crew.kickoff()
                    
                    # Build response CloudEvent
                    response_event = build_cloudevent(
                        event_type=f"com.acme.agents.system-call.{target_system}.completed",
                        source="urn:agent:system-call",
                        subject=f"{target_system}/{action}",
                        data={
                            "system": target_system,
                            "action": action,
                            "result": str(result),
                            "correlation_id": event_id,
                            "payload_sent": payload,
                            "ontology_concepts": [
                                ontology.resolve_concept(target_system),
                                ontology.resolve_concept('api_call')
                            ]
                        }
                    )
                    
                    # Publish response
                    publish_to_event_bus(response_event, output_stream)
                    
                    # ACK message
                    redis_client.xack(input_stream, consumer_group, message_id)
                    print(f"[SystemCallAgent] Completed message: {message_id}")
                    
        except Exception as e:
            print(f"[SystemCallAgent] Error in main loop: {e}")
            time.sleep(5)

# Agent Registration
AGENT_REGISTRY_ENTRY = {
    "id": "system-call-zapier-agent",
    "name": "System Call (Zapier) Agent",
    "type": "integration",
    "capabilities": ["system_integration", "api_calls", "zapier_webhooks", "crm_integration", "communication"],
    "input_stream": "stream:agents:system-call:requests:v1",
    "output_stream": "stream:agents:system-call:responses:v1",
    "input_schema": "https://schemas.acme.com/agents/system-call-request/1-0-0.json",
    "output_schema": "https://schemas.acme.com/agents/system-call-response/1-0-0.json",
    "supported_systems": ["salesforce", "hubspot", "slack", "email"],
    "ontology_concepts": [
        "https://vocab.acme.com/systems/CRM",
        "https://vocab.acme.com/integration/APICall",
        "https://vocab.acme.com/integration/Webhook"
    ],
    "tools": [
        "call_salesforce_api",
        "call_hubspot_api",
        "post_to_slack",
        "send_email",
        "validate_system_credentials"
    ],
    "status": "active"
}

if __name__ == "__main__":
    # Register agent
    redis_set_json(
        f"agent:registry:{AGENT_REGISTRY_ENTRY['id']}", 
        AGENT_REGISTRY_ENTRY
    )
    print(f"[SystemCallAgent] Registered in agent registry")
    
    # Start processing
    run_system_call_agent()
