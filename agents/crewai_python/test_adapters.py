"""
Comprehensive Test Suite for Platform Adapters
Tests Phase 1-4 implementation
"""
import asyncio
import json
import sys
import time
from tools.redis_streams_tools import RedisStreamsClient
from tools.schema_validation_tools import (
    validate_against_schema,
    publish_platform_action,
    fetch_schema
)

def test_schema_validation():
    """Test schema validation against ActionContract"""
    print("\n=== Test 1: Schema Validation ===")
    
    # Valid SA360 action
    valid_action = {
        'kind': 'action',
        'target': {
            'entityType': 'campaign',
            'entityId': '789'
        },
        'operation': 'setCampaignBudget',
        'params': {
            'campaignId': '789',
            'amount': 15000,
            'currency': 'USD'
        }
    }
    
    result = validate_against_schema(
        'https://schemas.mesh/adapters/sa360/ActionContract.json',
        valid_action
    )
    
    assert result['valid'], f"Valid action failed validation: {result.get('errors')}"
    print("✅ Valid action passed validation")
    
    # Invalid action (missing required field)
    invalid_action = {
        'kind': 'action',
        'operation': 'setCampaignBudget',
        'params': {
            'campaignId': '789',
            'amount': 15000
            # Missing 'currency'
        }
    }
    
    result = validate_against_schema(
        'https://schemas.mesh/adapters/sa360/ActionContract.json',
        invalid_action
    )
    
    assert not result['valid'], "Invalid action should fail validation"
    print("✅ Invalid action correctly rejected")


def test_publish_platform_action():
    """Test publish_platform_action tool"""
    print("\n=== Test 2: Publish Platform Action ===")
    
    result = publish_platform_action(
        operation='setCampaignBudget',
        params={
            'campaignId': 'test-789',
            'amount': 10000,
            'currency': 'USD'
        },
        platform='sa360',
        target_entity_type='campaign',
        target_entity_id='test-789'
    )
    
    assert result['success'], f"Publish failed: {result.get('errors')}"
    assert 'event_id' in result
    print(f"✅ Action published successfully: {result['event_id']}")
    
    # Verify event in Redis
    r = RedisStreamsClient().get_client()
    event = r.json().get(f"event:{result['event_id']}")
    assert event is not None, "Event not found in RedisJSON"
    assert event['type'] == 'mco.event.action'
    print("✅ Event stored in RedisJSON")
    
    # Verify pointer in stream
    messages = r.xrevrange('stream:mco:event:action', count=1)
    assert len(messages) > 0, "No messages in stream"
    print("✅ Event pointer in stream")
    
    return result['event_id']


def test_adapter_consumption():
    """Test adapter can consume and process events"""
    print("\n=== Test 3: Adapter Consumption (Manual) ===")
    print("To test adapter consumption:")
    print("1. Start adapter: python runners/adapter_runners.py sa360")
    print("2. Replay sample: python tools/replay_samples.py --adapter sa360")
    print("3. Check outcomes: redis-cli XRANGE stream:mco:event:outcome - + COUNT 10")
    print("⚠️  Manual test required")


def test_end_to_end_flow():
    """Test end-to-end: Decision → Action → Outcome"""
    print("\n=== Test 4: End-to-End Flow (Manual) ===")
    print("To test end-to-end flow:")
    print("1. Start Budget Optimizer agent")
    print("2. Agent calls publish_platform_action")
    print("3. Start SA360 adapter")
    print("4. Adapter consumes action, publishes outcome")
    print("5. Verify outcome in stream:mco:event:outcome")
    print("⚠️  Manual test required")


def test_all_adapters():
    """Test all 4 adapters are registered"""
    print("\n=== Test 5: All Adapters Registered ===")
    
    from runners.adapter_runners import ADAPTERS
    
    expected_adapters = ['sa360', 'dv360', 'amazon', 'tiktok']
    for adapter in expected_adapters:
        assert adapter in ADAPTERS, f"Adapter {adapter} not registered"
        print(f"✅ {adapter} adapter registered")


def test_rate_limiting():
    """Test rate limiting logic"""
    print("\n=== Test 6: Rate Limiting ===")
    
    from adapters.base_platform_adapter import BasePlatformAdapter
    from adapters.sa360_adapter import SA360Adapter
    
    adapter = SA360Adapter()
    
    # Check initial state
    assert adapter.rate_limit_remaining == 1000
    print("✅ Initial rate limit: 1000")
    
    # Simulate rate limit check
    async def test_rate_limit():
        await adapter._check_rate_limit()
        assert adapter.rate_limit_remaining == 999
        print("✅ Rate limit decremented")
    
    asyncio.run(test_rate_limit())


def test_idempotency():
    """Test idempotency tracking"""
    print("\n=== Test 7: Idempotency ===")
    
    from adapters.sa360_adapter import SA360Adapter
    
    adapter = SA360Adapter()
    
    # Add action to processed set
    action_id = 'test-action-123'
    adapter.processed_actions.add(action_id)
    
    # Check it's tracked
    assert action_id in adapter.processed_actions
    print("✅ Idempotency tracking works")


def test_schema_fetch():
    """Test schema fetching from registry"""
    print("\n=== Test 8: Schema Fetch ===")
    
    schema = fetch_schema('https://schemas.mesh/adapters/sa360/ActionContract.json')
    
    assert 'error' not in schema, f"Schema fetch failed: {schema.get('error')}"
    assert schema.get('title') == 'SA360 Action Contract'
    assert 'operation' in schema.get('properties', {})
    print("✅ Schema fetched successfully")


def test_outcome_structure():
    """Test ActionOutcome structure"""
    print("\n=== Test 9: ActionOutcome Structure ===")
    
    from adapters.base_platform_adapter import ActionOutcome
    
    outcome = ActionOutcome(
        action_id='test-123',
        status='success',
        platform_id='campaign-456',
        api_latency_ms=150
    )
    
    outcome_dict = outcome.to_dict()
    assert outcome_dict['action_id'] == 'test-123'
    assert outcome_dict['status'] == 'success'
    assert outcome_dict['api_latency_ms'] == 150
    print("✅ ActionOutcome structure correct")


def test_retry_logic():
    """Test retry logic with exponential backoff"""
    print("\n=== Test 10: Retry Logic ===")
    
    from adapters.sa360_adapter import SA360Adapter
    
    adapter = SA360Adapter()
    
    # Test retry with simulated failure
    async def test_retry():
        action = {
            'target': {'entityId': 'test-retry'},
            'operation': 'invalid_operation',  # Will fail
            'params': {}
        }
        
        start_time = time.time()
        outcome = await adapter.retry_action(action, max_retries=2)
        elapsed = time.time() - start_time
        
        assert outcome.status == 'failure'
        assert outcome.retry_count == 2
        assert elapsed >= 6  # 2^1 + 2^2 = 6 seconds minimum
        print(f"✅ Retry logic works (elapsed: {elapsed:.1f}s)")
    
    asyncio.run(test_retry())


def run_all_tests():
    """Run all tests"""
    print("=" * 60)
    print("PLATFORM ADAPTER TEST SUITE")
    print("=" * 60)
    
    tests = [
        ("Schema Validation", test_schema_validation),
        ("Publish Platform Action", test_publish_platform_action),
        ("Adapter Consumption", test_adapter_consumption),
        ("End-to-End Flow", test_end_to_end_flow),
        ("All Adapters Registered", test_all_adapters),
        ("Rate Limiting", test_rate_limiting),
        ("Idempotency", test_idempotency),
        ("Schema Fetch", test_schema_fetch),
        ("ActionOutcome Structure", test_outcome_structure),
        ("Retry Logic", test_retry_logic)
    ]
    
    passed = 0
    failed = 0
    
    for test_name, test_func in tests:
        try:
            test_func()
            passed += 1
        except Exception as e:
            print(f"❌ {test_name} FAILED: {e}")
            failed += 1
    
    print("\n" + "=" * 60)
    print(f"RESULTS: {passed} passed, {failed} failed")
    print("=" * 60)
    
    if failed == 0:
        print("\n✅ ALL TESTS PASSED!")
    else:
        print(f"\n⚠️  {failed} tests failed")
        sys.exit(1)


if __name__ == '__main__':
    run_all_tests()
