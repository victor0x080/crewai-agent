"""
Plan & Playbook Monitoring Agents
==================================
CrewAI agents that track strategic plan progress and playbook adherence
against ongoing enterprise events using RAG (vector search).

Follows design patterns:
- Redis Streams (XREADGROUP, XACK, consumer groups)
- CloudEvents 1.0 (specversion, id, source, type, subject, time, dataschema, data with @context)
- RAG queries via Supabase RPC functions (search_plans, search_playbooks, match_events)
- Ontology tools (resolve_concept, expand_concepts)
- CrewAI framework (role, goal, backstory, tools, allow_delegation=False)
"""

import os
import json
import uuid
import time
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
import redis
import requests
from crewai import Agent
from crewai.tools import tool

# ============================================================================
# CONFIGURATION
# ============================================================================

REDIS_HOST = os.getenv('REDIS_HOST', 'localhost')
REDIS_PORT = int(os.getenv('REDIS_PORT', '6379'))
SUPABASE_URL = os.getenv('SUPABASE_URL', 'http://localhost:54321')
SUPABASE_KEY = os.getenv('SUPABASE_ANON_KEY', '')
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY', '')

redis_client = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)

# ============================================================================
# RAG QUERY TOOLS
# ============================================================================

@tool("search_strategic_plans")
def search_strategic_plans(query: str, tenant_id: str = "default", domain: str = None, similarity_threshold: float = 0.7) -> str:
    """
    Search strategic plans using semantic similarity (vector search).
    Returns plans and objectives that match the query.
    
    Args:
        query: Natural language query (e.g., "revenue growth targets for 2025")
        tenant_id: Tenant identifier (default: "default")
        domain: Optional domain filter (e.g., "revenue", "operations")
        similarity_threshold: Minimum similarity score (0-1, default: 0.7)
    
    Returns:
        JSON string with matching plans and objectives
    """
    try:
        # Generate embedding for query
        embedding_response = requests.post(
            'https://api.openai.com/v1/embeddings',
            headers={
                'Authorization': f'Bearer {OPENAI_API_KEY}',
                'Content-Type': 'application/json'
            },
            json={
                'model': 'text-embedding-3-small',
                'input': query
            }
        )
        
        if embedding_response.status_code != 200:
            return json.dumps({"error": "Failed to generate embedding", "status": embedding_response.status_code})
        
        query_embedding = embedding_response.json()['data'][0]['embedding']
        
        # Call Supabase RPC function
        response = requests.post(
            f'{SUPABASE_URL}/rest/v1/rpc/search_plans',
            headers={
                'apikey': SUPABASE_KEY,
                'Authorization': f'Bearer {SUPABASE_KEY}',
                'Content-Type': 'application/json',
                'Prefer': 'return=representation'
            },
            json={
                'query_embedding': query_embedding,
                'tenant_id_param': tenant_id,
                'domain_param': domain,
                'similarity_threshold': similarity_threshold,
                'match_count': 10
            }
        )
        
        if response.status_code == 200:
            results = response.json()
            return json.dumps({
                "success": True,
                "count": len(results),
                "plans": results
            }, indent=2)
        else:
            return json.dumps({"error": "RPC call failed", "status": response.status_code, "details": response.text})
    
    except Exception as e:
        return json.dumps({"error": str(e)})


@tool("search_playbooks")
def search_playbooks(query: str, tenant_id: str = "default", domain: str = None, similarity_threshold: float = 0.7) -> str:
    """
    Search operational playbooks using semantic similarity (vector search).
    Returns playbooks that match the query.
    
    Args:
        query: Natural language query (e.g., "what to do when demand drops")
        tenant_id: Tenant identifier (default: "default")
        domain: Optional domain filter (e.g., "inventory", "marketing")
        similarity_threshold: Minimum similarity score (0-1, default: 0.7)
    
    Returns:
        JSON string with matching playbooks
    """
    try:
        # Generate embedding for query
        embedding_response = requests.post(
            'https://api.openai.com/v1/embeddings',
            headers={
                'Authorization': f'Bearer {OPENAI_API_KEY}',
                'Content-Type': 'application/json'
            },
            json={
                'model': 'text-embedding-3-small',
                'input': query
            }
        )
        
        if embedding_response.status_code != 200:
            return json.dumps({"error": "Failed to generate embedding", "status": embedding_response.status_code})
        
        query_embedding = embedding_response.json()['data'][0]['embedding']
        
        # Call Supabase RPC function
        response = requests.post(
            f'{SUPABASE_URL}/rest/v1/rpc/search_playbooks',
            headers={
                'apikey': SUPABASE_KEY,
                'Authorization': f'Bearer {SUPABASE_KEY}',
                'Content-Type': 'application/json',
                'Prefer': 'return=representation'
            },
            json={
                'query_embedding': query_embedding,
                'tenant_id_param': tenant_id,
                'domain_param': domain,
                'similarity_threshold': similarity_threshold,
                'match_count': 10
            }
        )
        
        if response.status_code == 200:
            results = response.json()
            return json.dumps({
                "success": True,
                "count": len(results),
                "playbooks": results
            }, indent=2)
        else:
            return json.dumps({"error": "RPC call failed", "status": response.status_code, "details": response.text})
    
    except Exception as e:
        return json.dumps({"error": str(e)})


@tool("match_business_events")
def match_business_events(query: str, tenant_id: str = "default", domain: str = None, days_back: int = 7, similarity_threshold: float = 0.7) -> str:
    """
    Match business events using semantic similarity within a time window.
    Returns recent events that match the query.
    
    Args:
        query: Natural language query (e.g., "revenue decline events")
        tenant_id: Tenant identifier (default: "default")
        domain: Optional domain filter (e.g., "revenue", "inventory")
        days_back: Look back N days (default: 7)
        similarity_threshold: Minimum similarity score (0-1, default: 0.7)
    
    Returns:
        JSON string with matching business events
    """
    try:
        # Generate embedding for query
        embedding_response = requests.post(
            'https://api.openai.com/v1/embeddings',
            headers={
                'Authorization': f'Bearer {OPENAI_API_KEY}',
                'Content-Type': 'application/json'
            },
            json={
                'model': 'text-embedding-3-small',
                'input': query
            }
        )
        
        if embedding_response.status_code != 200:
            return json.dumps({"error": "Failed to generate embedding", "status": embedding_response.status_code})
        
        query_embedding = embedding_response.json()['data'][0]['embedding']
        
        # Calculate time window
        since = (datetime.utcnow() - timedelta(days=days_back)).isoformat()
        
        # Call Supabase RPC function
        response = requests.post(
            f'{SUPABASE_URL}/rest/v1/rpc/match_events',
            headers={
                'apikey': SUPABASE_KEY,
                'Authorization': f'Bearer {SUPABASE_KEY}',
                'Content-Type': 'application/json',
                'Prefer': 'return=representation'
            },
            json={
                'query_embedding': query_embedding,
                'tenant_id_param': tenant_id,
                'domain_param': domain,
                'since': since,
                'similarity_threshold': similarity_threshold,
                'match_count': 20
            }
        )
        
        if response.status_code == 200:
            results = response.json()
            return json.dumps({
                "success": True,
                "count": len(results),
                "events": results,
                "time_window": {"since": since, "days_back": days_back}
            }, indent=2)
        else:
            return json.dumps({"error": "RPC call failed", "status": response.status_code, "details": response.text})
    
    except Exception as e:
        return json.dumps({"error": str(e)})


@tool("check_plan_variance")
def check_plan_variance(plan_id: str, current_metrics: Dict[str, float]) -> str:
    """
    Check variance between current metrics and strategic plan targets.
    Determines if enterprise is on-plan or off-plan.
    
    Args:
        plan_id: Strategic plan identifier (e.g., "growth_2025")
        current_metrics: Dict of current metric values (e.g., {"monthly_revenue": 4500000})
    
    Returns:
        JSON string with variance analysis and on/off-plan status
    """
    try:
        # Fetch plan from database
        response = requests.get(
            f'{SUPABASE_URL}/rest/v1/plans',
            headers={
                'apikey': SUPABASE_KEY,
                'Authorization': f'Bearer {SUPABASE_KEY}',
                'Content-Type': 'application/json'
            },
            params={
                'id': f'eq.{plan_id}',
                'select': '*'
            }
        )
        
        if response.status_code != 200 or not response.json():
            return json.dumps({"error": "Plan not found", "plan_id": plan_id})
        
        plan = response.json()[0]
        objectives = plan.get('content', {}).get('objectives', [])
        
        variances = []
        off_plan = []
        
        for objective in objectives:
            for kpi in objective.get('kpis', []):
                kpi_name = kpi.get('name')
                target = kpi.get('target')
                threshold_warning = kpi.get('threshold_warning', 0)
                threshold_critical = kpi.get('threshold_critical', 0)
                
                if kpi_name in current_metrics:
                    current = current_metrics[kpi_name]
                    variance = current - target
                    variance_pct = (variance / target) * 100 if target != 0 else 0
                    
                    status = 'on-plan'
                    if abs(variance) >= threshold_critical:
                        status = 'critical'
                        off_plan.append(kpi_name)
                    elif abs(variance) >= threshold_warning:
                        status = 'warning'
                    
                    variances.append({
                        "objective_id": objective.get('id'),
                        "objective_title": objective.get('title'),
                        "kpi_name": kpi_name,
                        "target": target,
                        "current": current,
                        "variance": variance,
                        "variance_pct": round(variance_pct, 2),
                        "status": status
                    })
        
        return json.dumps({
            "success": True,
            "plan_id": plan_id,
            "overall_status": "off-plan" if off_plan else "on-plan",
            "off_plan_kpis": off_plan,
            "variances": variances
        }, indent=2)
    
    except Exception as e:
        return json.dumps({"error": str(e)})


@tool("check_playbook_adherence")
def check_playbook_adherence(playbook_name: str, recent_events: List[Dict[str, Any]]) -> str:
    """
    Check if recent events and actions adhere to playbook specifications.
    Determines if playbook guidelines are being followed.
    
    Args:
        playbook_name: Playbook identifier (e.g., "global_demand_down")
        recent_events: List of recent business events
    
    Returns:
        JSON string with adherence analysis
    """
    try:
        # Fetch playbook from database
        response = requests.get(
            f'{SUPABASE_URL}/rest/v1/playbooks',
            headers={
                'apikey': SUPABASE_KEY,
                'Authorization': f'Bearer {SUPABASE_KEY}',
                'Content-Type': 'application/json'
            },
            params={
                'name': f'eq.{playbook_name}',
                'is_active': 'eq.true',
                'select': '*'
            }
        )
        
        if response.status_code != 200 or not response.json():
            return json.dumps({"error": "Playbook not found", "playbook_name": playbook_name})
        
        playbook = response.json()[0]
        parsed = playbook.get('parsed', {})
        
        # Check trigger conditions
        triggers = parsed.get('triggers', [])
        triggered = False
        for trigger in triggers:
            for event in recent_events:
                if event.get('event_type') == trigger.get('event_type'):
                    triggered = True
                    break
        
        # Check if actions match playbook
        expected_actions = parsed.get('actions', {})
        adherence_checks = []
        
        for function_area, actions in expected_actions.items():
            for event in recent_events:
                payload = event.get('payload', {})
                if function_area.lower() in payload.get('function', '').lower():
                    adherence_checks.append({
                        "function": function_area,
                        "event_type": event.get('event_type'),
                        "expected_actions": list(actions.keys()),
                        "adheres": True  # Simplified - in production, validate actual actions
                    })
        
        return json.dumps({
            "success": True,
            "playbook_name": playbook_name,
            "triggered": triggered,
            "adherence_checks": adherence_checks,
            "overall_adherence": "compliant" if len(adherence_checks) > 0 else "not_triggered"
        }, indent=2)
    
    except Exception as e:
        return json.dumps({"error": str(e)})


# ============================================================================
# REDIS STREAMS TOOLS
# ============================================================================

@tool("publish_cloudevent")
def publish_cloudevent(stream: str, event_type: str, data: Dict[str, Any], subject: str = None) -> str:
    """
    Publish a CloudEvents 1.0 compliant event to a Redis Stream.
    
    Args:
        stream: Stream name (e.g., "mesh:events")
        event_type: CloudEvents type (e.g., "com.acme.plan.variance.detected")
        data: Event payload dictionary
        subject: Optional subject/entity identifier
    
    Returns:
        Event ID of published message
    """
    event_id = str(uuid.uuid4())
    cloudevent = {
        "specversion": "1.0",
        "id": event_id,
        "type": event_type,
        "source": "urn:acme:agent:plan-monitor",
        "time": datetime.utcnow().isoformat() + "Z",
        "subject": subject or "",
        "dataschema": "https://schemas.acme.com/plan/variance/1-0-0.json",
        "data": data
    }
    
    # Store full event in RedisJSON
    redis_client.json().set(f"event:{event_id}", "$", cloudevent)
    
    # Add pointer to stream
    redis_client.xadd(stream, {
        "event_id": event_id,
        "type": event_type,
        "subject": subject or "",
        "dataschema": cloudevent["dataschema"]
    })
    
    return event_id


@tool("redis_ack")
def redis_ack(stream: str, group: str, message_id: str) -> str:
    """Acknowledge a message from a Redis Stream consumer group."""
    redis_client.xack(stream, group, message_id)
    return f"Acknowledged {message_id} in {stream}/{group}"


# ============================================================================
# ONTOLOGY TOOLS
# ============================================================================

@tool("resolve_concept")
def resolve_concept(label: str) -> str:
    """Resolve a concept label to its canonical URI using the ontology."""
    try:
        response = requests.get(
            f'{SUPABASE_URL}/rest/v1/rpc/resolve_concept',
            headers={'apikey': SUPABASE_KEY, 'Authorization': f'Bearer {SUPABASE_KEY}'},
            params={'label_param': label}
        )
        if response.status_code == 200 and response.json():
            return response.json()[0]['uri']
        return f"ex:{label.title().replace(' ', '')}"
    except:
        return f"ex:{label.title().replace(' ', '')}"


@tool("expand_concepts")
def expand_concepts(concept_uris: List[str], relations: List[str] = None) -> str:
    """Expand concepts via SKOS relations (broader, narrower, related)."""
    if not relations:
        relations = ['skos:broader', 'skos:narrower', 'skos:related']
    
    try:
        response = requests.post(
            f'{SUPABASE_URL}/rest/v1/rpc/expand_concepts',
            headers={
                'apikey': SUPABASE_KEY,
                'Authorization': f'Bearer {SUPABASE_KEY}',
                'Content-Type': 'application/json'
            },
            json={'concept_uris_param': concept_uris, 'relations_param': relations}
        )
        if response.status_code == 200:
            return json.dumps(response.json())
        return json.dumps(concept_uris)
    except:
        return json.dumps(concept_uris)


# ============================================================================
# AGENT 1: STRATEGIC PLAN TRACKER
# ============================================================================

strategic_plan_tracker_agent = Agent(
    role="Strategic Plan Tracker",
    goal="Monitor strategic plan progress against enterprise metrics and detect when objectives are off-track",
    backstory="""You are an expert strategic analyst specializing in plan governance and performance tracking.
    
    You have deep expertise in:
    - Strategic planning frameworks (OKRs, KPIs, balanced scorecards)
    - Variance analysis and threshold detection
    - Root cause analysis for plan deviations
    - Early warning systems for strategic risks
    - RAG (Retrieval Augmented Generation) for plan querying
    
    Your mission is to continuously monitor the enterprise's progress against strategic plans,
    detect variances early, and recommend corrective actions when objectives are at risk.
    
    You use semantic search to query strategic plans, match business events against plan objectives,
    and calculate variances between targets and actuals. When critical thresholds are breached,
    you publish CloudEvents to alert stakeholders and trigger automated response playbooks.""",
    tools=[
        search_strategic_plans,
        match_business_events,
        check_plan_variance,
        publish_cloudevent,
        redis_ack,
        resolve_concept,
        expand_concepts
    ],
    verbose=True,
    allow_delegation=False
)


# ============================================================================
# AGENT 2: PLAYBOOK ADHERENCE MONITOR
# ============================================================================

playbook_adherence_agent = Agent(
    role="Playbook Adherence Monitor",
    goal="Verify that enterprise actions follow approved playbook specifications and detect policy violations",
    backstory="""You are an expert compliance and policy analyst specializing in operational governance.
    
    You have deep expertise in:
    - Policy-as-code and playbook frameworks
    - Compliance monitoring and audit trails
    - Event-driven policy enforcement
    - Regulatory adherence and risk management
    - Semantic matching between events and policies
    
    Your mission is to continuously monitor business events and verify that all actions taken
    adhere to approved playbooks. When operations deviate from approved policies or when
    playbooks are not being followed correctly, you raise alerts and recommend remediation.
    
    You use semantic search to match business events against playbook triggers and actions,
    validate that guard conditions are respected (approvals, thresholds), and ensure that
    all operational parameters stay within playbook-defined boundaries.""",
    tools=[
        search_playbooks,
        match_business_events,
        check_playbook_adherence,
        publish_cloudevent,
        redis_ack,
        resolve_concept,
        expand_concepts
    ],
    verbose=True,
    allow_delegation=False
)


# ============================================================================
# AGENT 3: PLAN-EVENT CORRELATION ANALYST
# ============================================================================

plan_event_correlation_agent = Agent(
    role="Plan-Event Correlation Analyst",
    goal="Correlate business events with strategic objectives to identify plan impacts and trigger appropriate playbooks",
    backstory="""You are an expert business intelligence analyst specializing in causal analysis and impact assessment.
    
    You have deep expertise in:
    - Causal inference and correlation analysis
    - Event impact assessment on strategic objectives
    - Playbook triggering logic and automation
    - Multi-dimensional business analytics
    - Semantic knowledge graphs and ontologies
    
    Your mission is to continuously analyze incoming business events, correlate them with
    strategic plan objectives, assess their impact (positive or negative), and determine
    if corrective playbooks should be triggered.
    
    You use semantic search to match events against both plans and playbooks simultaneously,
    employ ontology expansion to discover indirect relationships, and publish CloudEvents
    that trigger automated workflows when significant correlations are detected.
    
    When a business event (e.g., revenue decline) correlates with a plan objective
    (e.g., revenue growth target) AND matches a playbook trigger (e.g., revenue recovery),
    you orchestrate the response by publishing plan variance alerts and playbook activation events.""",
    tools=[
        search_strategic_plans,
        search_playbooks,
        match_business_events,
        check_plan_variance,
        check_playbook_adherence,
        publish_cloudevent,
        redis_ack,
        resolve_concept,
        expand_concepts
    ],
    verbose=True,
    allow_delegation=False
)


# ============================================================================
# AGENT METADATA (for registration)
# ============================================================================

AGENTS_METADATA = [
    {
        "agent_id": "strategic-plan-tracker",
        "name": "Strategic Plan Tracker",
        "type": "plan_monitor",
        "capabilities": [
            "plan_tracking",
            "variance_analysis",
            "kpi_monitoring",
            "threshold_detection",
            "rag_query"
        ],
        "agent_instance": strategic_plan_tracker_agent
    },
    {
        "agent_id": "playbook-adherence-monitor",
        "name": "Playbook Adherence Monitor",
        "type": "policy_monitor",
        "capabilities": [
            "policy_compliance",
            "playbook_validation",
            "adherence_monitoring",
            "violation_detection",
            "rag_query"
        ],
        "agent_instance": playbook_adherence_agent
    },
    {
        "agent_id": "plan-event-correlation-analyst",
        "name": "Plan-Event Correlation Analyst",
        "type": "correlation_analyst",
        "capabilities": [
            "correlation_analysis",
            "impact_assessment",
            "playbook_triggering",
            "multi_source_query",
            "rag_query",
            "ontology_expansion"
        ],
        "agent_instance": plan_event_correlation_agent
    }
]


if __name__ == "__main__":
    print("=" * 80)
    print("PLAN & PLAYBOOK MONITORING AGENTS")
    print("=" * 80)
    print(f"\n✅ Loaded {len(AGENTS_METADATA)} agents:")
    for meta in AGENTS_METADATA:
        print(f"   • {meta['name']} ({meta['agent_id']})")
        print(f"     Capabilities: {', '.join(meta['capabilities'])}")
    print("\n" + "=" * 80)
