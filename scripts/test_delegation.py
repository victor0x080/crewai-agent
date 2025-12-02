#!/usr/bin/env python3
"""
Test script to verify delegation is working in ContactCenterCoachingCrew
"""

import sys
import json
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from ContactCenterCoachingCrew import build_crew


def test_delegation():
    """Test that delegation works correctly"""
    print("="*80)
    print("Testing ContactCenterCoachingCrew Delegation")
    print("="*80)
    
    # Build the crew
    config, crew = build_crew()
    
    # Verify crew setup
    print("\n[1] Crew Configuration:")
    print(f"   - Process: {crew.process}")
    print(f"   - Manager: {crew.manager_agent.role}")
    print(f"   - Manager can delegate: {crew.manager_agent.allow_delegation}")
    print(f"   - Total agents: {len(crew.agents)}")
    print(f"   - Total tasks: {len(crew.tasks)}")
    
    # Verify manager is in agents list
    print("\n[2] Agent List Check:")
    manager_in_list = crew.manager_agent in crew.agents
    print(f"   - Manager in agents list: {manager_in_list} {'✅' if manager_in_list else '❌ FAIL'}")
    
    if not manager_in_list:
        print("   ⚠️  WARNING: Manager not in agents list - delegation will likely fail!")
        return False
    
    # List all agents
    print("\n[3] All Agents:")
    for i, agent in enumerate(crew.agents, 1):
        is_manager = agent == crew.manager_agent
        print(f"   {i}. {agent.role} {'(MANAGER)' if is_manager else '(worker)'}")
        print(f"      - Can delegate: {agent.allow_delegation}")
    
    # Create a test event
    print("\n[4] Creating Test Event:")
    test_event = {
        'specversion': '1.0',
        'id': 'test_issue_001',
        'source': 'test-monitor',
        'type': 'contact_center.issue.detected',
        'subject': 'rep_test',
        'dataschema': 'ContactCenterIssueV1',
        'data': {
            'call_id': 'test_call_001',
            'rep_id': 'rep_test_001',
            'issue_type': 'no_empathy',
            'severity': 'medium',
            'detected_at_turn': 3,
            'rep_profile': {
                'name': 'Test Rep',
                'tenure_months': 3,
                'skill_level': 'novice',
                'vertical_specialty': 'hotel',
                'avg_csat': 3.8,
                'compliance_score': 82.0,
                'upsell_rate': 0.12,
                'top_training_needs': ['empathy', 'product_knowledge']
            },
            'customer_profile': {
                'segment': 'leisure',
                'sentiment_tendency': 'frustrated'
            },
            'transcript_snippet': [
                {
                    'turn_index': 2,
                    'speaker': 'customer',
                    'text': 'This is absolutely ridiculous! I have been waiting for 2 hours!',
                    'timestamp': '2025-12-01T09:00:00.000Z',
                    'call_id': 'test_call_001'
                },
                {
                    'turn_index': 3,
                    'speaker': 'rep',
                    'text': 'Can you provide your reservation number?',
                    'timestamp': '2025-12-01T09:00:05.000Z',
                    'call_id': 'test_call_001'
                }
            ]
        }
    }
    
    print(f"   - Issue Type: {test_event['data']['issue_type']}")
    print(f"   - Expected Coach: Empathy & Emotional Intelligence Coach")
    print(f"   - Rep Tenure: {test_event['data']['rep_profile']['tenure_months']} months")
    print(f"   - Customer Sentiment: {test_event['data']['customer_profile']['sentiment_tendency']}")
    
    # Run the crew
    print("\n[5] Running Crew (this may take a moment...):")
    print("   - Watching for delegation messages in verbose output...\n")
    
    try:
        result = crew.kickoff(inputs={
            'source_event': test_event,
            'target_schema_uri': 'CoachingMessageV1',
            'target_stream': 'stream:coaching:messages',
            'route_msg_id': 'test_msg_001',
            'route_stream': 'stream:test:route',
            'actual_issue_type': test_event['data']['issue_type']
        })
        
        print("\n[6] Result:")
        print(f"   - Type: {type(result)}")
        print(f"   - Content:\n{result}")
        
        # Check verbose output for delegation
        print("\n[7] Delegation Status:")
        print("   - Check the verbose output above for 'Delegating' or 'Delegate work to coworker' messages")
        print("   - If you see delegation messages, delegation is working ✅")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Error running crew: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == '__main__':
    print("\n" + "="*80)
    print("DELEGATION TEST FOR CONTACT CENTER COACHING CREW")
    print("="*80 + "\n")
    
    success = test_delegation()
    
    print("\n" + "="*80)
    if success:
        print("✅ TEST COMPLETED - Check verbose output for delegation messages")
        print("="*80)
        sys.exit(0)
    else:
        print("❌ TEST FAILED")
        print("="*80)
        sys.exit(1)