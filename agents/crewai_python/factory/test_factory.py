"""
Test suite for CrewAI Agent Factory
Validates agent generation, tool selection, and ontology profile creation
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

import asyncio
import json
from typing import Dict, Any

from agent_factory import get_agent_factory, CrewAIAgentFactory
from tool_registry import get_tool_registry


class TestAgentFactory:
    """Test cases for agent factory."""
    
    def __init__(self):
        self.factory = get_agent_factory()
        self.registry = get_tool_registry()
        self.test_results = []
    
    async def run_all_tests(self):
        """Run all test cases."""
        print("=" * 80)
        print("CREWAI AGENT FACTORY TEST SUITE")
        print("=" * 80)
        
        tests = [
            self.test_demand_forecast_trigger,
            self.test_inventory_stockout_trigger,
            self.test_campaign_performance_trigger,
            self.test_pricing_optimization_trigger,
            self.test_tool_registry_validation,
            self.test_agent_caching,
            self.test_telemetry_tracking,
        ]
        
        for test in tests:
            try:
                await test()
                self.test_results.append({'test': test.__name__, 'status': 'PASS'})
            except Exception as e:
                self.test_results.append({
                    'test': test.__name__, 
                    'status': 'FAIL', 
                    'error': str(e)
                })
                print(f"❌ {test.__name__} FAILED: {e}")
        
        self.print_summary()
    
    async def test_demand_forecast_trigger(self):
        """Test agent generation for demand forecast trigger."""
        print("\n" + "=" * 80)
        print("TEST 1: Demand Forecast Trigger")
        print("=" * 80)
        
        trigger_event = {
            'id': 'test-trigger-001',
            'type': 'demand.forecast.updated',
            'severity': 'high',
            'data': {
                'sku': 'WH-PRO-2024',
                'demand_change': -0.15,
                'confidence': 0.85,
                'current_inventory': 15000,
                'forecast_units': 12750
            }
        }
        
        context = {
            'business_unit': 'Electronics',
            'current_quarter': 'Q4',
            'budget_remaining': 250000,
            'constraints': ['maintain_service_level_95', 'max_markdown_20_percent']
        }
        
        available_datasets = [
            'demand_forecast',
            'inventory',
            'pricing',
            'campaign_performance'
        ]
        
        print("\nGenerating agent...")
        agent = await self.factory.generate_agent_from_trigger(
            trigger_event,
            context,
            available_datasets,
            use_cache=False  # Force generation for test
        )
        
        # Validate agent
        assert agent.role, "Agent must have a role"
        assert agent.goal, "Agent must have a goal"
        assert agent.backstory, "Agent must have a backstory"
        assert len(agent.tools) > 0, "Agent must have tools"
        
        print(f"\n✅ Agent Generated Successfully:")
        print(f"  Role: {agent.role}")
        print(f"  Goal: {agent.goal[:100]}...")
        print(f"  Backstory: {agent.backstory[:100]}...")
        print(f"  Tools ({len(agent.tools)}): {[t.__name__ for t in agent.tools]}")
        
        # Validate tools include demand forecast tools
        tool_names = [t.__name__ for t in agent.tools]
        assert 'fetch_demand_forecast_signal' in tool_names, "Should include demand forecast tool"
        
        print("\n✅ TEST 1 PASSED")
    
    async def test_inventory_stockout_trigger(self):
        """Test agent generation for inventory stockout trigger."""
        print("\n" + "=" * 80)
        print("TEST 2: Inventory Stockout Trigger")
        print("=" * 80)
        
        trigger_event = {
            'id': 'test-trigger-002',
            'type': 'inventory.stockout.risk',
            'severity': 'critical',
            'data': {
                'sku': 'SW-FIT-2024',
                'stockout_risk': 0.90,
                'days_until_stockout': 3,
                'on_hand': 150,
                'in_transit': 0,
                'daily_demand': 50
            }
        }
        
        context = {
            'business_unit': 'Electronics',
            'supplier_lead_time_days': 14,
            'service_level_target': 0.95
        }
        
        available_datasets = ['inventory', 'demand_forecast']
        
        print("\nGenerating agent...")
        agent = await self.factory.generate_agent_from_trigger(
            trigger_event,
            context,
            available_datasets,
            use_cache=False
        )
        
        print(f"\n✅ Agent Generated Successfully:")
        print(f"  Role: {agent.role}")
        print(f"  Goal: {agent.goal[:100]}...")
        print(f"  Tools ({len(agent.tools)}): {[t.__name__ for t in agent.tools]}")
        
        # Validate tools include inventory tools
        tool_names = [t.__name__ for t in agent.tools]
        assert 'fetch_inventory_position' in tool_names or 'compute_stockout_risk' in tool_names, \
            "Should include inventory tools"
        
        print("\n✅ TEST 2 PASSED")
    
    async def test_campaign_performance_trigger(self):
        """Test agent generation for campaign performance trigger."""
        print("\n" + "=" * 80)
        print("TEST 3: Campaign Performance Trigger")
        print("=" * 80)
        
        trigger_event = {
            'id': 'test-trigger-003',
            'type': 'campaign.performance.alert',
            'severity': 'high',
            'data': {
                'campaign_id': 'CAMP-2024-Q4',
                'roas': 1.2,
                'target_roas': 3.0,
                'spend': 45000,
                'budget': 50000,
                'days_remaining': 7
            }
        }
        
        context = {
            'business_unit': 'Marketing',
            'available_channels': ['amazon', 'walmart', 'target', 'instacart'],
            'total_budget': 200000
        }
        
        available_datasets = ['campaign_performance', 'pricing', 'demand_forecast']
        
        print("\nGenerating agent...")
        agent = await self.factory.generate_agent_from_trigger(
            trigger_event,
            context,
            available_datasets,
            use_cache=False
        )
        
        print(f"\n✅ Agent Generated Successfully:")
        print(f"  Role: {agent.role}")
        print(f"  Goal: {agent.goal[:100]}...")
        print(f"  Tools ({len(agent.tools)}): {[t.__name__ for t in agent.tools]}")
        
        # Validate tools include campaign tools
        tool_names = [t.__name__ for t in agent.tools]
        assert 'fetch_campaign_performance' in tool_names, "Should include campaign performance tool"
        
        print("\n✅ TEST 3 PASSED")
    
    async def test_pricing_optimization_trigger(self):
        """Test agent generation for pricing optimization trigger."""
        print("\n" + "=" * 80)
        print("TEST 4: Pricing Optimization Trigger")
        print("=" * 80)
        
        trigger_event = {
            'id': 'test-trigger-004',
            'type': 'pricing.elasticity.detected',
            'severity': 'medium',
            'data': {
                'sku': 'WH-PRO-2024',
                'current_price': 99.99,
                'elasticity': -1.8,
                'competitor_price': 89.99,
                'margin': 0.35
            }
        }
        
        context = {
            'business_unit': 'Electronics',
            'pricing_strategy': 'competitive',
            'min_margin': 0.25
        }
        
        available_datasets = ['pricing', 'demand_forecast', 'campaign_performance']
        
        print("\nGenerating agent...")
        agent = await self.factory.generate_agent_from_trigger(
            trigger_event,
            context,
            available_datasets,
            use_cache=False
        )
        
        print(f"\n✅ Agent Generated Successfully:")
        print(f"  Role: {agent.role}")
        print(f"  Goal: {agent.goal[:100]}...")
        print(f"  Tools ({len(agent.tools)}): {[t.__name__ for t in agent.tools]}")
        
        # Validate tools include pricing tools
        tool_names = [t.__name__ for t in agent.tools]
        assert 'fetch_pricing_promo_data' in tool_names or 'run_simulation_scenario' in tool_names, \
            "Should include pricing/simulation tools"
        
        print("\n✅ TEST 4 PASSED")
    
    async def test_tool_registry_validation(self):
        """Test tool registry validation."""
        print("\n" + "=" * 80)
        print("TEST 5: Tool Registry Validation")
        print("=" * 80)
        
        # Test valid capabilities
        capabilities = ['forecasting', 'optimization', 'inventory']
        tools = self.registry.get_tools_for_capabilities(capabilities)
        
        print(f"\nCapabilities: {capabilities}")
        print(f"Tools found: {len(tools)}")
        print(f"Tool names: {[t.__name__ for t in tools]}")
        
        assert len(tools) > 0, "Should find tools for valid capabilities"
        
        # Test validation
        result = self.registry.validate_capabilities([
            'forecasting',
            'invalid_capability',
            'optimization'
        ])
        
        print(f"\nValidation result:")
        print(f"  Valid: {result['valid']}")
        print(f"  Invalid: {result['invalid']}")
        print(f"  Suggestions: {result['suggestions']}")
        
        assert len(result['valid']) == 2, "Should validate 2 capabilities"
        assert len(result['invalid']) == 1, "Should detect 1 invalid capability"
        
        print("\n✅ TEST 5 PASSED")
    
    async def test_agent_caching(self):
        """Test agent caching functionality."""
        print("\n" + "=" * 80)
        print("TEST 6: Agent Caching")
        print("=" * 80)
        
        trigger_event = {
            'id': 'test-trigger-cache-001',
            'type': 'demand.forecast.updated',
            'severity': 'high',
            'data': {'sku': 'TEST-SKU', 'demand_change': -0.10}
        }
        
        context = {'business_unit': 'Test'}
        available_datasets = ['demand_forecast']
        
        # Clear cache first
        self.factory.clear_cache()
        
        # First generation (should not hit cache)
        print("\nFirst generation (no cache)...")
        agent1 = await self.factory.generate_agent_from_trigger(
            trigger_event, context, available_datasets, use_cache=True
        )
        
        telemetry1 = self.factory.get_telemetry()
        print(f"  Cache hits: {telemetry1['cache_hits']}")
        print(f"  Total generations: {telemetry1['total_generations']}")
        
        # Second generation (should hit cache)
        print("\nSecond generation (should hit cache)...")
        agent2 = await self.factory.generate_agent_from_trigger(
            trigger_event, context, available_datasets, use_cache=True
        )
        
        telemetry2 = self.factory.get_telemetry()
        print(f"  Cache hits: {telemetry2['cache_hits']}")
        print(f"  Total generations: {telemetry2['total_generations']}")
        
        assert telemetry2['cache_hits'] > telemetry1['cache_hits'], "Should hit cache on second call"
        assert agent1.role == agent2.role, "Cached agent should be identical"
        
        print("\n✅ TEST 6 PASSED")
    
    async def test_telemetry_tracking(self):
        """Test telemetry tracking."""
        print("\n" + "=" * 80)
        print("TEST 7: Telemetry Tracking")
        print("=" * 80)
        
        telemetry = self.factory.get_telemetry()
        
        print(f"\nTelemetry:")
        print(f"  Total generations: {telemetry['total_generations']}")
        print(f"  Cache hits: {telemetry['cache_hits']}")
        print(f"  Cache hit rate: {telemetry['cache_hit_rate']:.2%}")
        print(f"  Avg generation time: {telemetry['avg_generation_time_seconds']:.2f}s")
        print(f"  Cached agents: {telemetry['cached_agents']}")
        
        assert telemetry['total_generations'] > 0, "Should have generated agents"
        assert 'cache_hit_rate' in telemetry, "Should track cache hit rate"
        assert 'avg_generation_time_seconds' in telemetry, "Should track generation time"
        
        print("\n✅ TEST 7 PASSED")
    
    def print_summary(self):
        """Print test summary."""
        print("\n" + "=" * 80)
        print("TEST SUMMARY")
        print("=" * 80)
        
        passed = sum(1 for r in self.test_results if r['status'] == 'PASS')
        failed = sum(1 for r in self.test_results if r['status'] == 'FAIL')
        
        print(f"\nTotal Tests: {len(self.test_results)}")
        print(f"Passed: {passed}")
        print(f"Failed: {failed}")
        
        if failed > 0:
            print("\nFailed Tests:")
            for result in self.test_results:
                if result['status'] == 'FAIL':
                    print(f"  ❌ {result['test']}: {result.get('error', 'Unknown error')}")
        
        print("\nDetailed Results:")
        for result in self.test_results:
            status_icon = "✅" if result['status'] == 'PASS' else "❌"
            print(f"  {status_icon} {result['test']}: {result['status']}")
        
        print("\n" + "=" * 80)
        
        if failed == 0:
            print("🎉 ALL TESTS PASSED!")
        else:
            print(f"⚠️  {failed} TEST(S) FAILED")
        
        print("=" * 80)


async def main():
    """Run test suite."""
    test_suite = TestAgentFactory()
    await test_suite.run_all_tests()


if __name__ == '__main__':
    asyncio.run(main())
