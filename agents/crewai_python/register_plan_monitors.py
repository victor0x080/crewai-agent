"""
Register Plan Monitoring Agents
================================
Registers plan monitoring agents with the agent registry system.
"""

import os
import requests
import json
from plan_monitoring_agents import AGENTS_METADATA

SUPABASE_URL = os.getenv('SUPABASE_URL', 'http://localhost:54321')
SUPABASE_KEY = os.getenv('SUPABASE_SERVICE_ROLE_KEY', os.getenv('SUPABASE_ANON_KEY', ''))


def register_agent(agent_meta):
    """Register a single agent with the registry."""
    print(f"\n📝 Registering agent: {agent_meta['name']}")
    
    # Prepare agent record
    agent_record = {
        "agent_id": agent_meta['agent_id'],
        "name": agent_meta['name'],
        "type": agent_meta['type'],
        "capabilities": agent_meta['capabilities'],
        "status": "active",
        "language": "python",
        "framework": "crewai",
        "version": "1.0.0",
        "metadata": {
            "role": agent_meta['agent_instance'].role,
            "goal": agent_meta['agent_instance'].goal,
            "tools": [tool.name for tool in agent_meta['agent_instance'].tools],
            "streams": ["stream:business:events", "mesh:events"]
        }
    }
    
    # Upsert to database
    try:
        response = requests.post(
            f'{SUPABASE_URL}/rest/v1/python_agents',
            headers={
                'apikey': SUPABASE_KEY,
                'Authorization': f'Bearer {SUPABASE_KEY}',
                'Content-Type': 'application/json',
                'Prefer': 'resolution=merge-duplicates'
            },
            json=agent_record
        )
        
        if response.status_code in [200, 201]:
            print(f"   ✅ Registered successfully")
            print(f"   Capabilities: {', '.join(agent_meta['capabilities'])}")
            return True
        else:
            print(f"   ❌ Registration failed: {response.status_code}")
            print(f"   {response.text}")
            return False
    
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return False


def create_ontology_profiles():
    """Create ontology profiles for plan monitoring agents."""
    print("\n🔗 Creating ontology profiles...")
    
    profiles = [
        {
            "agent_id": "strategic-plan-tracker",
            "interests_concepts_must": [
                "ex:StrategicPlan",
                "ex:StrategicObjective",
                "ex:KPI",
                "ex:Variance"
            ],
            "interests_concepts_any": [
                "ex:Revenue",
                "ex:Growth",
                "ex:Target",
                "ex:Metric"
            ],
            "tools_needed": [
                "kg.search_plans",
                "kg.check_variance",
                "kg.resolve",
                "kg.expand"
            ]
        },
        {
            "agent_id": "playbook-adherence-monitor",
            "interests_concepts_must": [
                "ex:Playbook",
                "ex:Policy",
                "ex:Compliance"
            ],
            "interests_concepts_any": [
                "ex:Violation",
                "ex:Approval",
                "ex:Guard",
                "ex:Action"
            ],
            "tools_needed": [
                "kg.search_playbooks",
                "kg.check_adherence",
                "kg.resolve",
                "kg.expand"
            ]
        },
        {
            "agent_id": "plan-event-correlation-analyst",
            "interests_concepts_must": [
                "ex:Correlation",
                "ex:Impact"
            ],
            "interests_concepts_any": [
                "ex:StrategicPlan",
                "ex:Playbook",
                "ex:BusinessEvent",
                "ex:Trigger"
            ],
            "tools_needed": [
                "kg.search_plans",
                "kg.search_playbooks",
                "kg.match_events",
                "kg.resolve",
                "kg.expand"
            ]
        }
    ]
    
    for profile in profiles:
        try:
            response = requests.post(
                f'{SUPABASE_URL}/rest/v1/agent_ontology_profiles',
                headers={
                    'apikey': SUPABASE_KEY,
                    'Authorization': f'Bearer {SUPABASE_KEY}',
                    'Content-Type': 'application/json',
                    'Prefer': 'resolution=merge-duplicates'
                },
                json=profile
            )
            
            if response.status_code in [200, 201]:
                print(f"   ✅ Profile created: {profile['agent_id']}")
            else:
                print(f"   ⚠️  Profile creation failed: {response.status_code}")
        
        except Exception as e:
            print(f"   ⚠️  Error creating profile: {e}")


def main():
    """Main registration function."""
    print("=" * 80)
    print("PLAN MONITOR AGENT REGISTRATION")
    print("=" * 80)
    
    success_count = 0
    
    for agent_meta in AGENTS_METADATA:
        if register_agent(agent_meta):
            success_count += 1
    
    print("\n" + "=" * 80)
    print(f"✅ Registered {success_count}/{len(AGENTS_METADATA)} agents")
    print("=" * 80)
    
    # Create ontology profiles
    create_ontology_profiles()
    
    print("\n✅ Registration complete!\n")


if __name__ == "__main__":
    main()
