"""
Register All Generic CrewAI Agents
Registers the 4 generic pattern agents in Redis registry
"""

import redis
import json
from plan_review_agent import AGENT_REGISTRY_ENTRY as PLAN_REVIEW
from data_query_agent import AGENT_REGISTRY_ENTRY as DATA_QUERY
from stream_capture_agent import AGENT_REGISTRY_ENTRY as STREAM_CAPTURE
from system_call_zapier_agent import AGENT_REGISTRY_ENTRY as SYSTEM_CALL

# Redis connection
redis_client = redis.Redis(host='localhost', port=6379, decode_responses=True)

# All generic agents
GENERIC_AGENTS = {
    "plan-review-agent": PLAN_REVIEW,
    "data-query-agent": DATA_QUERY,
    "stream-capture-agent": STREAM_CAPTURE,
    "system-call-zapier-agent": SYSTEM_CALL
}

def register_all_agents():
    """Register all generic agents in Redis"""
    print("=" * 80)
    print("REGISTERING GENERIC CREWAI AGENTS")
    print("=" * 80)
    
    registered_count = 0
    
    for agent_id, agent_config in GENERIC_AGENTS.items():
        try:
            # Store in agent registry
            redis_client.json().set(
                f"agent:registry:{agent_id}",
                "$",
                agent_config
            )
            
            print(f"\n✅ Registered: {agent_config['name']}")
            print(f"   ID: {agent_id}")
            print(f"   Type: {agent_config['type']}")
            print(f"   Capabilities: {', '.join(agent_config['capabilities'])}")
            print(f"   Input Stream: {agent_config['input_stream']}")
            print(f"   Output Stream: {agent_config['output_stream']}")
            
            registered_count += 1
            
        except Exception as e:
            print(f"\n❌ Error registering {agent_id}: {e}")
    
    print("\n" + "=" * 80)
    print(f"REGISTRATION COMPLETE: {registered_count}/{len(GENERIC_AGENTS)} agents")
    print("=" * 80)
    
    return registered_count

def create_stream_groups():
    """Create consumer groups for all agent streams"""
    print("\n" + "=" * 80)
    print("CREATING CONSUMER GROUPS")
    print("=" * 80)
    
    streams = [
        "stream:agents:plan-review:requests:v1",
        "stream:agents:plan-review:responses:v1",
        "stream:agents:data-query:requests:v1",
        "stream:agents:data-query:responses:v1",
        "stream:agents:stream-capture:requests:v1",
        "stream:alerts:v1",
        "stream:agents:system-call:requests:v1",
        "stream:agents:system-call:responses:v1",
        "stream:inventory:stock-updates:v1",
        "stream:pricing:price-updated:v1"
    ]
    
    groups_created = 0
    
    for stream in streams:
        try:
            redis_client.xgroup_create(stream, "default", id="$", mkstream=True)
            print(f"✅ Created group 'default' for {stream}")
            groups_created += 1
        except redis.ResponseError as e:
            if "BUSYGROUP" in str(e):
                print(f"⚠️  Group already exists for {stream}")
            else:
                print(f"❌ Error creating group for {stream}: {e}")
    
    print(f"\n{groups_created} new consumer groups created")
    print("=" * 80)

def list_registered_agents():
    """List all registered agents"""
    print("\n" + "=" * 80)
    print("REGISTERED AGENTS")
    print("=" * 80)
    
    # Get all agent keys
    agent_keys = redis_client.keys("agent:registry:*")
    
    print(f"\nFound {len(agent_keys)} registered agents:\n")
    
    for key in sorted(agent_keys):
        try:
            agent = redis_client.json().get(key)
            if agent:
                print(f"📋 {agent['name']}")
                print(f"   ID: {agent['id']}")
                print(f"   Type: {agent['type']}")
                print(f"   Status: {agent.get('status', 'unknown')}")
                print(f"   Capabilities: {len(agent.get('capabilities', []))}")
                print()
        except Exception as e:
            print(f"❌ Error reading {key}: {e}")
    
    print("=" * 80)

def verify_redis_connection():
    """Verify Redis connection"""
    try:
        redis_client.ping()
        print("✅ Redis connection successful")
        return True
    except Exception as e:
        print(f"❌ Redis connection failed: {e}")
        print("   Make sure Redis is running: redis-server")
        return False

if __name__ == "__main__":
    print("\n🚀 Generic CrewAI Agent Registration\n")
    
    # Verify Redis connection
    if not verify_redis_connection():
        exit(1)
    
    # Register agents
    count = register_all_agents()
    
    # Create stream groups
    create_stream_groups()
    
    # List all registered agents
    list_registered_agents()
    
    print("\n✅ All agents registered and ready!")
    print("\nTo start agents:")
    print("  python plan_review_agent.py")
    print("  python data_query_agent.py")
    print("  python stream_capture_agent.py")
    print("  python system_call_zapier_agent.py")
    print()
