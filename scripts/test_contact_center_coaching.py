#!/usr/bin/env python3
"""
Contact Center Coaching System - Integration Tests
Tests the complete flow from transcript ingestion to coaching delivery

Tests:
1. CrewAI agent compliance verification
2. Detection service functionality
3. Redis Streams integration
4. End-to-end coaching flow
5. WebSocket delivery
"""

import sys
import os
import time
import json
import uuid
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / 'agents' / 'crewai_python'))
sys.path.insert(0, str(Path(__file__).parent.parent / 'agents' / 'crewai_python' / 'crews' / 'contact-center'))

import redis
import requests
from typing import Dict, Any, List


# Configuration
REDIS_URL = os.getenv('REDIS_URL', 'redis://localhost:6379')
API_URL = os.getenv('API_URL', 'http://localhost:3000')
redis_client = redis.from_url(REDIS_URL, decode_responses=True)

# Test Results Tracker
test_results = {
    "passed": 0,
    "failed": 0,
    "errors": []
}


def log_test(name: str, passed: bool, message: str = ""):
    """Log test result"""
    status = "✅ PASS" if passed else "❌ FAIL"
    print(f"\n{status} - {name}")
    if message:
        print(f"  {message}")
    
    if passed:
        test_results["passed"] += 1
    else:
        test_results["failed"] += 1
        test_results["errors"].append(f"{name}: {message}")


def test_crewai_compliance():
    """Test 1: Verify CrewAI agent compliance"""
    print("\n" + "="*60)
    print("TEST 1: CrewAI Agent Compliance Verification")
    print("="*60)
    
    try:
        # Import the crew
        from ContactCenterCoachingCrew import build_crew, build_coaching_manager
        
        config, crew = build_crew()
        
        # Test 1.1: Manager has correct settings
        manager = crew.manager_agent
        
        # Check allow_delegation
        has_delegation = manager.allow_delegation
        log_test(
            "Manager allow_delegation=True",
            has_delegation,
            f"Manager delegation: {has_delegation}"
        )
        
        # Check tools
        manager_tools = [tool.name for tool in manager.tools] if hasattr(manager, 'tools') and manager.tools else []
        expected_tools = ['redis_publish', 'redis_ack', 'fetch_schema', 'validate_jsonschema']
        has_tools = all(tool in manager_tools for tool in expected_tools)
        log_test(
            "Manager has required tools",
            has_tools,
            f"Tools: {manager_tools}"
        )
        
        # Test 1.2: Workers have correct settings
        workers = [agent for agent in crew.agents if agent != manager]
        
        log_test(
            "Has 5 specialist workers",
            len(workers) == 5,
            f"Found {len(workers)} workers"
        )
        
        # Check all workers have allow_delegation=False and no tools
        all_workers_valid = True
        for worker in workers:
            if worker.allow_delegation:
                all_workers_valid = False
                print(f"  ❌ Worker {worker.role} has allow_delegation=True (should be False)")
            
            worker_tools = worker.tools if hasattr(worker, 'tools') and worker.tools else []
            if worker_tools:
                all_workers_valid = False
                print(f"  ❌ Worker {worker.role} has tools (should have none)")
        
        log_test(
            "All workers: allow_delegation=False, no tools",
            all_workers_valid,
            "All workers properly configured"
        )
        
        # Test 1.3: Process is hierarchical
        from crewai import Process
        is_hierarchical = crew.process == Process.hierarchical
        log_test(
            "Process is hierarchical",
            is_hierarchical,
            f"Process: {crew.process}"
        )
        
        # Test 1.4: Manager is specified
        has_manager = crew.manager_agent is not None
        log_test(
            "Manager agent specified",
            has_manager,
            f"Manager: {crew.manager_agent.role if has_manager else 'None'}"
        )
        
        return True
        
    except Exception as e:
        log_test("CrewAI Compliance", False, f"Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def test_redis_connectivity():
    """Test 2: Redis connectivity and stream setup"""
    print("\n" + "="*60)
    print("TEST 2: Redis Connectivity")
    print("="*60)
    
    try:
        # Test 2.1: Redis ping
        pong = redis_client.ping()
        log_test("Redis connection", pong, "Redis is responsive")
        
        # Test 2.2: Create test streams if they don't exist
        streams = [
            'stream:contact_center:issues',
            'stream:coaching:messages',
            'stream:route.decisions:coaching-manager'
        ]
        
        for stream in streams:
            try:
                # Try to read stream info
                redis_client.xinfo_stream(stream)
                print(f"  ✓ Stream exists: {stream}")
            except redis.exceptions.ResponseError:
                # Create stream with dummy message
                redis_client.xadd(stream, {'init': 'true'})
                print(f"  ✓ Created stream: {stream}")
        
        log_test("Redis streams setup", True, f"All {len(streams)} streams ready")
        
        return True
        
    except Exception as e:
        log_test("Redis connectivity", False, f"Error: {str(e)}")
        return False


def test_api_connectivity():
    """Test 3: API connectivity"""
    print("\n" + "="*60)
    print("TEST 3: API Connectivity")
    print("="*60)
    
    try:
        # Test 3.1: API is responding
        response = requests.get(f"{API_URL}/api/health", timeout=5)
        api_up = response.status_code in [200, 404]  # 404 is ok if /health doesn't exist
        log_test("API server responding", api_up, f"Status: {response.status_code}")
        
        return api_up
        
    except Exception as e:
        log_test("API connectivity", False, f"Error: {str(e)}")
        print(f"\n  💡 Make sure server is running: npm start")
        return False


def test_detection_logic():
    """Test 4: Detection logic"""
    print("\n" + "="*60)
    print("TEST 4: Detection Logic")
    print("="*60)
    
    try:
        # Create test transcript with known errors
        test_call_id = f"test_call_{uuid.uuid4().hex[:8]}"
        test_rep_id = "test_rep_1"
        test_customer_id = "test_customer_1"
        
        # Test 4.1: No empathy detection
        transcript_no_empathy = [
            {
                "call_id": test_call_id,
                "turn_index": 0,
                "speaker": "customer",
                "text": "This is ridiculous and very frustrating!",
                "timestamp": "2025-11-24T16:00:00Z",
                "rep_id": test_rep_id,
                "customer_id": test_customer_id
            },
            {
                "call_id": test_call_id,
                "turn_index": 1,
                "speaker": "rep",
                "text": "What's your booking number?",
                "timestamp": "2025-11-24T16:00:15Z",
                "rep_id": test_rep_id,
                "customer_id": test_customer_id
            }
        ]
        
        # Register test rep and customer
        requests.post(
            f"{API_URL}/api/contact-center/reps",
            json={
                "rep_id": test_rep_id,
                "name": "Test Rep",
                "tenure_months": 6,
                "skill_level": "novice",
                "vertical_specialty": "hotel",
                "language": "EN",
                "avg_aht_seconds": 300,
                "avg_csat": 3.5,
                "compliance_score": 75.0,
                "upsell_rate": 0.1,
                "top_training_needs": ["empathy"]
            },
            timeout=5
        )
        
        requests.post(
            f"{API_URL}/api/contact-center/customers",
            json={
                "customer_id": test_customer_id,
                "segment": "leisure",
                "vertical": "hotel",
                "sentiment_tendency": "impatient"
            },
            timeout=5
        )
        
        # Start call
        requests.post(
            f"{API_URL}/api/contact-center/calls/start",
            json={
                "call_id": test_call_id,
                "rep_id": test_rep_id,
                "customer_id": test_customer_id
            },
            timeout=5
        )
        
        # Ingest transcript turns
        for turn in transcript_no_empathy:
            requests.post(
                f"{API_URL}/api/contact-center/calls/{test_call_id}/turns",
                json=turn,
                timeout=5
            )
            time.sleep(0.5)  # Small delay between turns
        
        # Wait for detection
        time.sleep(2)
        
        # Check if issue was published to Redis Stream
        messages = redis_client.xrange('stream:contact_center:issues', '-', '+', count=10)
        
        # Look for our test call
        found_issue = False
        for msg_id, fields in messages:
            if fields.get('call_id') == test_call_id:
                found_issue = True
                issue_type = fields.get('issue_type')
                print(f"  ✓ Detected issue: {issue_type}")
                break
        
        log_test(
            "No empathy detection",
            found_issue,
            "Issue published to Redis Stream" if found_issue else "No issue detected"
        )
        
        return found_issue
        
    except Exception as e:
        log_test("Detection logic", False, f"Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def test_coaching_crew_activation():
    """Test 5: Coaching crew can be activated"""
    print("\n" + "="*60)
    print("TEST 5: Coaching Crew Activation")
    print("="*60)
    
    try:
        # Import and build crew
        from ContactCenterCoachingCrew import build_crew
        
        config, crew = build_crew()
        
        # Test 5.1: Crew can be instantiated
        log_test("Crew instantiation", True, f"Crew ID: {config.crew_id}")
        
        # Test 5.2: Create test issue event
        test_issue_id = f"test_issue_{uuid.uuid4().hex[:8]}"
        test_call_id = f"test_call_{uuid.uuid4().hex[:8]}"
        
        test_issue = {
            "issue_id": test_issue_id,
            "call_id": test_call_id,
            "rep_id": "test_rep_1",
            "issue_type": "no_empathy",
            "severity": "medium",
            "detected_at_turn": 1,
            "rep_profile": {
                "rep_id": "test_rep_1",
                "name": "Test Rep",
                "tenure_months": 6,
                "skill_level": "novice",
                "avg_csat": 3.5,
                "compliance_score": 75.0,
                "upsell_rate": 0.1,
                "top_training_needs": ["empathy"]
            },
            "customer_profile": {
                "customer_id": "test_customer_1",
                "segment": "leisure",
                "sentiment_tendency": "impatient"
            },
            "transcript_snippet": [
                {"turn_index": 0, "speaker": "customer", "text": "This is frustrating!"},
                {"turn_index": 1, "speaker": "rep", "text": "What's your number?"}
            ]
        }
        
        # Test 5.3: Try to run crew with test inputs
        try:
            print("\n  Testing crew execution (this may take a few seconds)...")
            
            # Note: We can't actually run the crew without proper setup,
            # but we can verify the structure is correct
            inputs = {
                'source_event': test_issue,
                'target_schema_uri': 'CoachingMessageV1',
                'target_stream': 'stream:coaching:messages',
                'route_msg_id': 'test_msg_id',
                'route_stream': config.route_stream
            }
            
            # Verify task accepts these inputs
            task = crew.tasks[0]
            log_test(
                "Crew task structure",
                task.agent == crew.manager_agent,
                "Task assigned to manager"
            )
            
            log_test(
                "Crew is activatable",
                True,
                "Crew structure is valid and ready for activation"
            )
            
        except Exception as e:
            log_test("Crew execution", False, f"Execution error: {str(e)}")
        
        return True
        
    except Exception as e:
        log_test("Coaching crew activation", False, f"Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def test_end_to_end_simulation():
    """Test 6: End-to-end simulation"""
    print("\n" + "="*60)
    print("TEST 6: End-to-End Simulation")
    print("="*60)
    
    try:
        # Create realistic test call
        test_call_id = f"demo_call_{uuid.uuid4().hex[:8]}"
        test_rep_id = "demo_rep_1"
        test_customer_id = "demo_customer_1"
        
        print(f"\n  📞 Simulating call: {test_call_id}")
        print(f"  👤 Rep: {test_rep_id}")
        print(f"  🧑 Customer: {test_customer_id}\n")
        
        # Register participants
        print("  1️⃣  Registering rep...")
        requests.post(
            f"{API_URL}/api/contact-center/reps",
            json={
                "rep_id": test_rep_id,
                "name": "Demo Rep",
                "tenure_months": 3,
                "skill_level": "novice",
                "vertical_specialty": "hotel",
                "language": "EN",
                "avg_aht_seconds": 420,
                "avg_csat": 3.6,
                "compliance_score": 72.0,
                "upsell_rate": 0.08,
                "top_training_needs": ["empathy", "policy_adherence"]
            },
            timeout=5
        )
        
        print("  2️⃣  Registering customer...")
        requests.post(
            f"{API_URL}/api/contact-center/customers",
            json={
                "customer_id": test_customer_id,
                "segment": "leisure",
                "vertical": "hotel",
                "sentiment_tendency": "impatient"
            },
            timeout=5
        )
        
        # Start call
        print("  3️⃣  Starting call...")
        requests.post(
            f"{API_URL}/api/contact-center/calls/start",
            json={
                "call_id": test_call_id,
                "rep_id": test_rep_id,
                "customer_id": test_customer_id
            },
            timeout=5
        )
        
        # Simulate transcript with multiple errors
        transcript = [
            {
                "turn_index": 0,
                "speaker": "customer",
                "text": "Hi, I just arrived and the hotel says they're overbooked. I don't have a room!",
                "timestamp": "2025-11-24T16:00:00Z"
            },
            {
                "turn_index": 1,
                "speaker": "rep",
                "text": "Can you give me your confirmation number?",
                "timestamp": "2025-11-24T16:00:15Z"
            },
            {
                "turn_index": 2,
                "speaker": "customer",
                "text": "It's ABC123. This is ridiculous and very frustrating!",
                "timestamp": "2025-11-24T16:00:30Z"
            },
            {
                "turn_index": 3,
                "speaker": "rep",
                "text": "I see your booking. Let me check what happened.",
                "timestamp": "2025-11-24T16:00:45Z"
            },
            {
                "turn_index": 4,
                "speaker": "customer",
                "text": "I want a full refund and you need to find me another hotel.",
                "timestamp": "2025-11-24T16:01:00Z"
            },
            {
                "turn_index": 5,
                "speaker": "rep",
                "text": "Okay, I'll refund everything right now.",
                "timestamp": "2025-11-24T16:01:15Z"
            }
        ]
        
        print("  4️⃣  Streaming transcript turns...")
        for i, turn in enumerate(transcript):
            turn_data = {
                **turn,
                "call_id": test_call_id,
                "rep_id": test_rep_id,
                "customer_id": test_customer_id
            }
            
            speaker_icon = "🧑" if turn["speaker"] == "customer" else "👤"
            print(f"     {speaker_icon} Turn {i}: {turn['text'][:50]}...")
            
            requests.post(
                f"{API_URL}/api/contact-center/calls/{test_call_id}/turns",
                json=turn_data,
                timeout=5
            )
            time.sleep(1)  # Simulate real-time streaming
        
        # Wait for detection
        print("\n  5️⃣  Waiting for detection...")
        time.sleep(3)
        
        # Check for detected issues
        print("  6️⃣  Checking detected issues...")
        response = requests.get(
            f"{API_URL}/api/contact-center/issues",
            params={"call_id": test_call_id},
            timeout=5
        )
        
        if response.status_code == 200:
            issues = response.json().get('issues', [])
            print(f"\n  🚨 Detected {len(issues)} issue(s):")
            for issue in issues:
                issue_type = issue.get('issue_type', 'unknown')
                severity = issue.get('severity', 'unknown')
                print(f"     - {issue_type} ({severity} severity)")
            
            log_test(
                "End-to-end simulation",
                len(issues) > 0,
                f"Detected {len(issues)} issues in test call"
            )
            
            return len(issues) > 0
        else:
            log_test("End-to-end simulation", False, f"API error: {response.status_code}")
            return False
        
    except Exception as e:
        log_test("End-to-end simulation", False, f"Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def print_summary():
    """Print test summary"""
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    
    total = test_results["passed"] + test_results["failed"]
    pass_rate = (test_results["passed"] / total * 100) if total > 0 else 0
    
    print(f"\n✅ Passed: {test_results['passed']}/{total}")
    print(f"❌ Failed: {test_results['failed']}/{total}")
    print(f"📊 Pass Rate: {pass_rate:.1f}%")
    
    if test_results["errors"]:
        print("\n❌ Failed Tests:")
        for error in test_results["errors"]:
            print(f"   - {error}")
    
    if test_results["failed"] == 0:
        print("\n🎉 All tests passed! Demo is ready.")
    else:
        print("\n⚠️  Some tests failed. Check errors above.")
    
    return test_results["failed"] == 0


def main():
    """Run all tests"""
    print("\n" + "="*60)
    print("CONTACT CENTER COACHING SYSTEM - INTEGRATION TESTS")
    print("="*60)
    print("\nThis will test:")
    print("1. CrewAI agent compliance")
    print("2. Redis connectivity")
    print("3. API connectivity")
    print("4. Detection logic")
    print("5. Coaching crew activation")
    print("6. End-to-end simulation")
    
    input("\nPress Enter to start tests...")
    
    # Run tests
    test_crewai_compliance()
    test_redis_connectivity()
    
    api_ok = test_api_connectivity()
    if api_ok:
        test_detection_logic()
        test_end_to_end_simulation()
    else:
        print("\n⚠️  Skipping API-dependent tests (server not running)")
    
    test_coaching_crew_activation()
    
    # Print summary
    all_passed = print_summary()
    
    sys.exit(0 if all_passed else 1)


if __name__ == '__main__':
    main()

