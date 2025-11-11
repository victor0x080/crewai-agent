"""
Plan Monitor Consumer
=====================
Redis Streams consumer that runs plan monitoring agents on business events.

Listens to:
- stream:business:events (all business events)
- mesh:events (enterprise event mesh)

Routes events to appropriate monitoring agents based on event type and domain.
"""

import os
import json
import time
from typing import Dict, Any, List
import redis
from crewai import Task, Crew, Process
from plan_monitoring_agents import (
    strategic_plan_tracker_agent,
    playbook_adherence_agent,
    plan_event_correlation_agent,
    AGENTS_METADATA
)

# Configuration
REDIS_HOST = os.getenv('REDIS_HOST', 'localhost')
REDIS_PORT = int(os.getenv('REDIS_PORT', '6379'))
CONSUMER_GROUP = 'plan-monitors'
CONSUMER_NAME = f'monitor-{os.getpid()}'

redis_client = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)

# Stream subscriptions
STREAMS = {
    'stream:business:events': '>',
    'mesh:events': '>'
}


def create_consumer_groups():
    """Create consumer groups for all streams."""
    for stream in STREAMS.keys():
        try:
            redis_client.xgroup_create(stream, CONSUMER_GROUP, id='$', mkstream=True)
            print(f"✅ Created consumer group '{CONSUMER_GROUP}' for stream '{stream}'")
        except redis.exceptions.ResponseError as e:
            if 'BUSYGROUP' in str(e):
                print(f"ℹ️  Consumer group '{CONSUMER_GROUP}' already exists for '{stream}'")
            else:
                print(f"⚠️  Error creating consumer group: {e}")


def fetch_event_data(event_id: str) -> Dict[str, Any]:
    """Fetch full CloudEvent from RedisJSON."""
    try:
        event_data = redis_client.json().get(f"event:{event_id}")
        if event_data:
            return event_data
        return {}
    except Exception as e:
        print(f"⚠️  Error fetching event {event_id}: {e}")
        return {}


def route_to_agent(event: Dict[str, Any]) -> str:
    """
    Determine which agent should handle this event.
    
    Returns: agent_id
    """
    event_type = event.get('type', '')
    data = event.get('data', {})
    
    # Variance/metrics events → Strategic Plan Tracker
    if 'variance' in event_type.lower() or 'metric' in event_type.lower():
        return 'strategic-plan-tracker'
    
    # Policy/compliance events → Playbook Adherence Monitor
    if 'policy' in event_type.lower() or 'compliance' in event_type.lower():
        return 'playbook-adherence-monitor'
    
    # Generic business events → Correlation Analyst (checks both)
    if 'business' in event_type.lower() or data.get('importance') in ['high', 'critical']:
        return 'plan-event-correlation-analyst'
    
    # Default: Correlation Analyst handles all
    return 'plan-event-correlation-analyst'


def execute_monitoring_task(agent_id: str, event: Dict[str, Any]):
    """Execute monitoring task with appropriate agent."""
    
    # Find agent metadata
    agent_meta = next((m for m in AGENTS_METADATA if m['agent_id'] == agent_id), None)
    if not agent_meta:
        print(f"⚠️  Unknown agent: {agent_id}")
        return
    
    agent = agent_meta['agent_instance']
    event_type = event.get('type', '')
    event_data = event.get('data', {})
    
    # Create task based on agent type
    if agent_id == 'strategic-plan-tracker':
        task_description = f"""
Analyze this business event and check if it affects strategic plan objectives:

Event Type: {event_type}
Event Data: {json.dumps(event_data, indent=2)}

Steps:
1. Use search_strategic_plans() to find relevant strategic objectives
2. Use check_plan_variance() to calculate variances if metrics are provided
3. If variance exceeds thresholds, publish a CloudEvent alert via publish_cloudevent()

Report:
- Which plan objectives are affected
- Current vs target metrics
- Variance status (on-plan, warning, critical)
- Recommended actions
"""
    
    elif agent_id == 'playbook-adherence-monitor':
        task_description = f"""
Verify that this event adheres to operational playbooks:

Event Type: {event_type}
Event Data: {json.dumps(event_data, indent=2)}

Steps:
1. Use search_playbooks() to find relevant playbooks for this event
2. Use match_business_events() to get recent related events
3. Use check_playbook_adherence() to verify compliance
4. If violations detected, publish a CloudEvent alert via publish_cloudevent()

Report:
- Which playbooks are relevant
- Whether actions adhere to playbook specifications
- Any policy violations detected
- Recommended remediation
"""
    
    else:  # plan-event-correlation-analyst
        task_description = f"""
Correlate this event with strategic plans and determine if playbooks should be triggered:

Event Type: {event_type}
Event Data: {json.dumps(event_data, indent=2)}

Steps:
1. Use search_strategic_plans() to find affected objectives
2. Use search_playbooks() to find relevant response playbooks
3. Use match_business_events() to find correlated recent events
4. Determine if playbook should be triggered based on event severity and plan impact
5. If playbook triggering is needed, publish CloudEvent alerts via publish_cloudevent()

Report:
- Plan objectives impacted
- Relevant playbooks
- Correlation strength
- Triggering recommendation (yes/no)
- Confidence level
"""
    
    # Create and execute task
    task = Task(
        description=task_description,
        expected_output="Detailed monitoring report with recommendations",
        agent=agent
    )
    
    crew = Crew(
        agents=[agent],
        tasks=[task],
        process=Process.sequential,
        verbose=True
    )
    
    try:
        print(f"\n{'='*80}")
        print(f"▶️  Executing {agent_meta['name']}")
        print(f"{'='*80}\n")
        
        result = crew.kickoff()
        
        print(f"\n{'='*80}")
        print(f"✅ {agent_meta['name']} completed")
        print(f"{'='*80}\n")
        print(f"Result:\n{result}\n")
        
        return result
    
    except Exception as e:
        print(f"❌ Error executing {agent_meta['name']}: {e}")
        return None


def process_message(stream: str, message_id: str, fields: Dict[str, str]):
    """Process a single message from a stream."""
    try:
        event_id = fields.get('event_id')
        if not event_id:
            print(f"⚠️  No event_id in message {message_id}")
            redis_client.xack(stream, CONSUMER_GROUP, message_id)
            return
        
        # Fetch full event
        event = fetch_event_data(event_id)
        if not event:
            print(f"⚠️  Could not fetch event {event_id}")
            redis_client.xack(stream, CONSUMER_GROUP, message_id)
            return
        
        print(f"\n📨 Received event: {event.get('type')} (ID: {event_id[:8]}...)")
        
        # Route to appropriate agent
        agent_id = route_to_agent(event)
        print(f"🎯 Routing to: {agent_id}")
        
        # Execute monitoring task
        result = execute_monitoring_task(agent_id, event)
        
        # Acknowledge message
        redis_client.xack(stream, CONSUMER_GROUP, message_id)
        print(f"✅ Acknowledged message {message_id[:8]}...")
        
    except Exception as e:
        print(f"❌ Error processing message {message_id}: {e}")
        # Still acknowledge to prevent reprocessing
        redis_client.xack(stream, CONSUMER_GROUP, message_id)


def main():
    """Main consumer loop."""
    print("\n" + "="*80)
    print("PLAN MONITOR CONSUMER")
    print("="*80)
    print(f"Consumer Group: {CONSUMER_GROUP}")
    print(f"Consumer Name: {CONSUMER_NAME}")
    print(f"Streams: {list(STREAMS.keys())}")
    print("="*80 + "\n")
    
    # Create consumer groups
    create_consumer_groups()
    
    print("\n🔄 Starting consumer loop...\n")
    
    while True:
        try:
            # Read from all streams
            messages = redis_client.xreadgroup(
                CONSUMER_GROUP,
                CONSUMER_NAME,
                STREAMS,
                count=1,
                block=5000  # 5 second timeout
            )
            
            if not messages:
                continue
            
            # Process each message
            for stream, message_list in messages:
                for message_id, fields in message_list:
                    process_message(stream, message_id, fields)
        
        except KeyboardInterrupt:
            print("\n\n👋 Shutting down consumer...")
            break
        
        except Exception as e:
            print(f"❌ Consumer error: {e}")
            time.sleep(5)


if __name__ == "__main__":
    main()
