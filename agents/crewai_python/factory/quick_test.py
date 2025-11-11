#!/usr/bin/env python3
"""
Quick test script for dynamic agent configuration
Tests the factory without requiring full infrastructure
"""
import sys
import os
sys.path.append(os.path.dirname(__file__))

import json
import asyncio
from datetime import datetime


def test_tool_registry():
    """Test 1: Tool Registry"""
    print("\n" + "="*80)
    print("TEST 1: TOOL REGISTRY")
    print("="*80)
    
    try:
        from tool_registry import get_tool_registry
        
        registry = get_tool_registry()
        
        # Test capability vocabulary
        capabilities = registry.get_capability_vocabulary()
        print(f"\n✅ Loaded {len(capabilities)} capabilities")
        print(f"   Sample: {capabilities[:5]}")
        
        # Test tool vocabulary
        tools = registry.get_tool_vocabulary()
        print(f"\n✅ Loaded {len(tools)} tools")
        print(f"   Sample: {tools[:5]}")
        
        # Test tool selection
        test_caps = ['forecasting', 'optimization']
        selected_tools = registry.get_tools_for_capabilities(test_caps)
        print(f"\n✅ Selected {len(selected_tools)} tools for {test_caps}")
        tool_names = [t.__name__ if hasattr(t, '__name__') else (t.name if hasattr(t, 'name') else str(t)) for t in selected_tools]
        print(f"   Tools: {tool_names}")
        
        # Test validation
        validation = registry.validate_capabilities(['forecasting', 'invalid_cap', 'optimization'])
        print(f"\n✅ Validation test:")
        print(f"   Valid: {validation['valid']}")
        print(f"   Invalid: {validation['invalid']}")
        
        print("\n✅ TEST 1 PASSED")
        return True
        
    except Exception as e:
        print(f"\n❌ TEST 1 FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_agent_spec_generation():
    """Test 2: Agent Specification Generation (Mock)"""
    print("\n" + "="*80)
    print("TEST 2: AGENT SPECIFICATION GENERATION (MOCK)")
    print("="*80)
    
    try:
        from agent_factory import AgentSpec
        
        # Create a mock agent spec
        spec = AgentSpec(
            role="Demand Forecast Analyst",
            goal="Identify root causes of 15% demand drop for SKU WH-PRO-2024 and recommend 3 corrective actions within 24 hours",
            backstory="Expert demand forecaster with deep expertise in time series analysis, causal inference, and marketing attribution.",
            capabilities=['forecasting', 'causal_analysis', 'anomaly_detection'],
            required_tools=['fetch_demand_forecast_signal', 'run_simulation_scenario'],
            data_sources=['demand_forecast', 'pricing'],
            output_format="CloudEvent with root cause analysis and ranked recommendations",
            allow_delegation=False,
            model="gpt-4o-mini",
            temperature=0.7,
            metadata={
                'trigger_type': 'demand.forecast.updated',
                'trigger_severity': 'high',
                'generated_at': datetime.utcnow().isoformat()
            }
        )
        
        print(f"\n✅ Created AgentSpec:")
        print(f"   Role: {spec.role}")
        print(f"   Goal: {spec.goal[:80]}...")
        print(f"   Capabilities: {spec.capabilities}")
        print(f"   Tools: {spec.required_tools}")
        print(f"   Data Sources: {spec.data_sources}")
        
        print("\n✅ TEST 2 PASSED")
        return True
        
    except Exception as e:
        print(f"\n❌ TEST 2 FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_tool_selection():
    """Test 3: Tool Selection from Spec"""
    print("\n" + "="*80)
    print("TEST 3: TOOL SELECTION FROM SPEC")
    print("="*80)
    
    try:
        from agent_factory import AgentSpec, CrewAIAgentFactory
        from tool_registry import get_tool_registry
        
        # Create mock spec
        spec = AgentSpec(
            role="Test Agent",
            goal="Test goal",
            backstory="Test backstory",
            capabilities=['forecasting', 'inventory'],
            required_tools=['fetch_demand_forecast_signal'],
            data_sources=['demand_forecast', 'inventory'],
            output_format="Test output",
            allow_delegation=False,
            model="gpt-4o-mini",
            temperature=0.7,
            metadata={}
        )
        
        # Create factory (without LLM client to avoid API calls)
        factory = CrewAIAgentFactory(
            llm_client=False,
            tool_registry=get_tool_registry(),
            supabase_client=None
        )
        
        # Test tool selection
        tools = factory._select_tools(spec)
        
        print(f"\n✅ Selected {len(tools)} tools:")
        for tool in tools:
            tool_name = tool.__name__ if hasattr(tool, '__name__') else (tool.name if hasattr(tool, 'name') else str(tool))
            print(f"   - {tool_name}")
        
        # Verify expected tools are present
        tool_names = [t.__name__ if hasattr(t, '__name__') else (t.name if hasattr(t, 'name') else str(t)) for t in tools]
        assert 'fetch_demand_forecast_signal' in tool_names, "Should include demand forecast tool"
        assert 'fetch_inventory_position' in tool_names, "Should include inventory tool"
        
        print("\n✅ TEST 3 PASSED")
        return True
        
    except Exception as e:
        print(f"\n❌ TEST 3 FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_ontology_profile_creation():
    """Test 4: Ontology Profile Creation"""
    print("\n" + "="*80)
    print("TEST 4: ONTOLOGY PROFILE CREATION")
    print("="*80)
    
    try:
        from agent_factory import AgentSpec, CrewAIAgentFactory
        
        # Create mock spec
        spec = AgentSpec(
            role="Test Agent",
            goal="Test goal",
            backstory="Test backstory",
            capabilities=['forecasting', 'optimization', 'compliance'],
            required_tools=[],
            data_sources=[],
            output_format="Test output",
            allow_delegation=False,
            model="gpt-4o-mini",
            temperature=0.7,
            metadata={}
        )
        
        factory = CrewAIAgentFactory(
            llm_client=False,
            tool_registry=None,
            supabase_client=None
        )
        
        # Create ontology profile
        profile = factory._create_ontology_profile(spec)
        
        print(f"\n✅ Created Ontology Profile:")
        print(f"   Concepts: {profile['interests_concepts_must']}")
        print(f"   Entities: {profile.get('interests_entities', {})}")
        print(f"   Tools: {profile['tools']}")
        
        # Verify concepts are mapped
        assert len(profile['interests_concepts_must']) > 0, "Should have mapped concepts"
        assert 'kg.resolve' in profile['tools'], "Should include kg.resolve tool"
        
        print("\n✅ TEST 4 PASSED")
        return True
        
    except Exception as e:
        print(f"\n❌ TEST 4 FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_cache_key_generation():
    """Test 5: Cache Key Generation"""
    print("\n" + "="*80)
    print("TEST 5: CACHE KEY GENERATION")
    print("="*80)
    
    try:
        from agent_factory import CrewAIAgentFactory
        
        factory = CrewAIAgentFactory(
            llm_client=False,
            tool_registry=None,
            supabase_client=None
        )
        
        # Test with similar triggers
        trigger1 = {
            'type': 'demand.forecast.updated',
            'severity': 'high',
            'data': {'sku': 'SKU-001'}
        }
        
        trigger2 = {
            'type': 'demand.forecast.updated',
            'severity': 'high',
            'data': {'sku': 'SKU-002'}  # Different SKU
        }
        
        trigger3 = {
            'type': 'inventory.stockout.risk',
            'severity': 'critical',
            'data': {'sku': 'SKU-001'}
        }
        
        context = {'business_unit': 'Test'}
        
        key1 = factory._generate_cache_key(trigger1, context)
        key2 = factory._generate_cache_key(trigger2, context)
        key3 = factory._generate_cache_key(trigger3, context)
        
        print(f"\n✅ Generated cache keys:")
        print(f"   Trigger 1: {key1}")
        print(f"   Trigger 2: {key2}")
        print(f"   Trigger 3: {key3}")
        
        # Similar triggers should have same key
        assert key1 == key2, "Similar triggers should generate same cache key"
        assert key1 != key3, "Different trigger types should generate different keys"
        
        print("\n✅ TEST 5 PASSED")
        return True
        
    except Exception as e:
        print(f"\n❌ TEST 5 FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_prompt_building():
    """Test 6: Prompt Building"""
    print("\n" + "="*80)
    print("TEST 6: PROMPT BUILDING")
    print("="*80)
    
    try:
        from agent_factory import CrewAIAgentFactory
        from tool_registry import get_tool_registry
        
        factory = CrewAIAgentFactory(
            llm_client=False,
            tool_registry=get_tool_registry(),
            supabase_client=None
        )
        
        trigger_event = {
            'type': 'demand.forecast.updated',
            'severity': 'high',
            'data': {
                'sku': 'WH-PRO-2024',
                'demand_change': -0.15
            }
        }
        
        context = {
            'business_unit': 'Electronics',
            'current_quarter': 'Q4'
        }
        
        available_datasets = ['demand_forecast', 'inventory']
        
        # Build prompt
        prompt = factory._build_agent_generation_prompt(
            trigger_event,
            context,
            available_datasets
        )
        
        print(f"\n✅ Generated prompt ({len(prompt)} chars)")
        print(f"\n   Preview (first 500 chars):")
        print(f"   {prompt[:500]}...")
        
        # Verify prompt contains key elements
        assert 'TRIGGER EVENT' in prompt, "Should include trigger event section"
        assert 'BUSINESS CONTEXT' in prompt, "Should include business context"
        assert 'CAPABILITIES VOCABULARY' in prompt, "Should include capabilities"
        assert 'TOOL VOCABULARY' in prompt, "Should include tools"
        assert 'demand.forecast.updated' in prompt, "Should include trigger type"
        
        print("\n✅ TEST 6 PASSED")
        return True
        
    except Exception as e:
        print(f"\n❌ TEST 6 FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_bridge_script():
    """Test 7: Bridge Script Execution"""
    print("\n" + "="*80)
    print("TEST 7: BRIDGE SCRIPT (DRY RUN)")
    print("="*80)
    
    try:
        import tempfile
        import subprocess
        
        # Create temp files
        trigger_data = {
            'id': 'test-001',
            'type': 'demand.forecast.updated',
            'severity': 'high',
            'data': {'sku': 'TEST-SKU', 'demand_change': -0.15}
        }
        
        context_data = {
            'business_unit': 'Test',
            'available_datasets': ['demand_forecast']
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as tf:
            json.dump(trigger_data, tf)
            trigger_file = tf.name
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as cf:
            json.dump(context_data, cf)
            context_file = cf.name
        
        print(f"\n✅ Created temp files:")
        print(f"   Trigger: {trigger_file}")
        print(f"   Context: {context_file}")
        
        # Check if bridge script exists
        bridge_script = os.path.join(os.path.dirname(__file__), 'generate_agent.py')
        
        if os.path.exists(bridge_script):
            print(f"\n✅ Bridge script found: {bridge_script}")
            print(f"   Executable: {os.access(bridge_script, os.X_OK)}")
        else:
            print(f"\n⚠️  Bridge script not found at: {bridge_script}")
        
        # Cleanup
        os.unlink(trigger_file)
        os.unlink(context_file)
        
        print("\n✅ TEST 7 PASSED (DRY RUN)")
        return True
        
    except Exception as e:
        print(f"\n❌ TEST 7 FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """Run all tests."""
    print("\n" + "="*80)
    print("DYNAMIC AGENT CONFIGURATION TEST SUITE")
    print("="*80)
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    results = []
    
    # Run tests
    tests = [
        ("Tool Registry", test_tool_registry),
        ("Agent Spec Generation", test_agent_spec_generation),
        ("Tool Selection", test_tool_selection),
        ("Ontology Profile Creation", test_ontology_profile_creation),
        ("Cache Key Generation", test_cache_key_generation),
        ("Prompt Building", test_prompt_building),
        ("Bridge Script", test_bridge_script),
    ]
    
    for test_name, test_func in tests:
        try:
            if asyncio.iscoroutinefunction(test_func):
                result = await test_func()
            else:
                result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"\n❌ {test_name} crashed: {e}")
            results.append((test_name, False))
    
    # Print summary
    print("\n" + "="*80)
    print("TEST SUMMARY")
    print("="*80)
    
    passed = sum(1 for _, result in results if result)
    failed = sum(1 for _, result in results if not result)
    
    print(f"\nTotal Tests: {len(results)}")
    print(f"Passed: {passed}")
    print(f"Failed: {failed}")
    
    print("\nDetailed Results:")
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"  {status} - {test_name}")
    
    print("\n" + "="*80)
    
    if failed == 0:
        print("🎉 ALL TESTS PASSED!")
        print("\nNext Steps:")
        print("  1. Set OPENAI_API_KEY to test full agent generation")
        print("  2. Run: python test_factory.py (requires API key)")
        print("  3. Integrate with ProactiveAgentSpawner")
    else:
        print(f"⚠️  {failed} TEST(S) FAILED")
        print("\nPlease fix failing tests before proceeding.")
    
    print("="*80 + "\n")
    
    return failed == 0


if __name__ == '__main__':
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
