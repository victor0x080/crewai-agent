"""
Tool Registry - Maps capabilities to CrewAI tools
Provides centralized tool selection for auto-generated agents
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from typing import List, Dict, Any, Set
from crewai.tools import tool

# Import all available tools
from tools.redis_streams_tools import (
    publish_cloudevent, 
    fetch_cloudevent, 
    fetch_schema
)
from tools.schema_validation_tools import (
    validate_against_schema,
    publish_platform_action
)
from tools.simulation_tools import (
    fetch_demand_forecast_signal,
    fetch_inventory_position,
    fetch_pricing_promo_data,
    fetch_campaign_performance,
    run_simulation_scenario,
    compute_stockout_risk
)
from tools.algorithm_comparison_tool import (
    compare_algorithm_results,
    synthesize_multi_algorithm_insights
)


class ToolRegistry:
    """
    Central registry for mapping agent capabilities to tool functions.
    Enables dynamic tool selection for auto-generated agents.
    """
    
    def __init__(self):
        self._capability_tool_map = self._build_capability_map()
        self._tool_catalog = self._build_tool_catalog()
    
    def get_tools_for_capabilities(self, capabilities: List[str]) -> List[Any]:
        """
        Get list of tool functions for given capabilities.
        
        Args:
            capabilities: List of capability strings (e.g., ['forecasting', 'optimization'])
        
        Returns:
            List of tool functions (deduplicated)
        """
        tools = []
        seen = set()
        
        # Add base tools (always included)
        for tool in [publish_cloudevent, fetch_schema]:
            tool_id = id(tool)
            if tool_id not in seen:
                tools.append(tool)
                seen.add(tool_id)
        
        # Add capability-specific tools
        for capability in capabilities:
            capability_lower = capability.lower()
            if capability_lower in self._capability_tool_map:
                for tool in self._capability_tool_map[capability_lower]:
                    tool_id = id(tool)
                    if tool_id not in seen:
                        tools.append(tool)
                        seen.add(tool_id)
        
        return tools
    
    def get_tools_for_data_sources(self, data_sources: List[str]) -> List[Any]:
        """
        Get tools needed to access specific data sources.
        
        Args:
            data_sources: List of data source names (e.g., ['demand_forecast', 'inventory'])
        
        Returns:
            List of tool functions
        """
        tools = []
        seen = set()
        
        data_source_map = {
            'demand_forecast': [fetch_demand_forecast_signal],
            'inventory': [fetch_inventory_position, compute_stockout_risk],
            'pricing': [fetch_pricing_promo_data],
            'campaign': [fetch_campaign_performance],
            'simulation': [run_simulation_scenario],
        }
        
        for source in data_sources:
            source_lower = source.lower()
            if source_lower in data_source_map:
                for tool in data_source_map[source_lower]:
                    tool_id = id(tool)
                    if tool_id not in seen:
                        tools.append(tool)
                        seen.add(tool_id)
        
        return tools
    
    def get_tool_by_name(self, tool_name: str) -> Any:
        """Get a specific tool by name."""
        return self._tool_catalog.get(tool_name)
    
    def get_all_tools(self) -> Dict[str, Any]:
        """Get all available tools."""
        return self._tool_catalog.copy()
    
    def get_tool_names_for_capabilities(self, capabilities: List[str]) -> List[str]:
        """Get tool names (strings) instead of functions."""
        tools = self.get_tools_for_capabilities(capabilities)
        return [tool.__name__ if hasattr(tool, '__name__') else str(tool) for tool in tools]
    
    def _build_capability_map(self) -> Dict[str, List[Any]]:
        """
        Build mapping from capabilities to tool functions.
        This is the core intelligence of the registry.
        """
        return {
            # Data & Analytics Capabilities
            'semantic_data': [
                fetch_demand_forecast_signal,
                fetch_inventory_position,
                fetch_pricing_promo_data,
                fetch_campaign_performance
            ],
            'forecasting': [
                fetch_demand_forecast_signal,
                run_simulation_scenario
            ],
            'causal_analysis': [
                fetch_demand_forecast_signal,
                fetch_campaign_performance,
                run_simulation_scenario
            ],
            'scenario_simulation': [
                run_simulation_scenario,
                fetch_demand_forecast_signal,
                fetch_inventory_position
            ],
            'inventory': [
                fetch_inventory_position,
                compute_stockout_risk,
                fetch_demand_forecast_signal
            ],
            'risk': [
                compute_stockout_risk,
                fetch_inventory_position,
                run_simulation_scenario
            ],
            
            # Optimization Capabilities
            'optimization': [
                publish_platform_action,
                validate_against_schema,
                run_simulation_scenario
            ],
            'budget_optimization': [
                publish_platform_action,
                validate_against_schema,
                fetch_campaign_performance
            ],
            'bid_optimization': [
                publish_platform_action,
                validate_against_schema,
                fetch_pricing_promo_data
            ],
            'portfolio_optimization': [
                publish_platform_action,
                validate_against_schema,
                fetch_campaign_performance
            ],
            
            # Detection & Monitoring
            'anomaly_detection': [
                fetch_demand_forecast_signal,
                fetch_inventory_position,
                fetch_pricing_promo_data,
                fetch_campaign_performance
            ],
            'opportunity_scanning': [
                fetch_demand_forecast_signal,
                fetch_campaign_performance,
                run_simulation_scenario
            ],
            'change_detection': [
                fetch_demand_forecast_signal,
                fetch_campaign_performance
            ],
            
            # Integration & Routing
            'routing': [
                publish_cloudevent,
                fetch_cloudevent,
                fetch_schema
            ],
            'translation': [
                publish_cloudevent,
                fetch_cloudevent,
                fetch_schema,
                validate_against_schema
            ],
            'validation': [
                validate_against_schema,
                fetch_schema
            ],
            'compliance': [
                validate_against_schema,
                fetch_schema
            ],
            
            # Platform Integration
            'platform_integration': [
                publish_platform_action,
                validate_against_schema
            ],
            'creative': [
                publish_platform_action,
                validate_against_schema
            ],
            
            # RMN-Specific Capabilities
            'retail_media': [
                publish_platform_action,
                fetch_campaign_performance,
                validate_against_schema
            ],
            'closed_loop_attribution': [
                fetch_campaign_performance,
                fetch_demand_forecast_signal
            ],
            'incrementality': [
                run_simulation_scenario,
                fetch_campaign_performance
            ],
            
            # Campaign & Marketing
            'campaign': [
                fetch_campaign_performance,
                publish_platform_action,
                validate_against_schema,
                compare_algorithm_results,
                synthesize_multi_algorithm_insights
            ],
            'attribution': [
                fetch_campaign_performance,
                fetch_demand_forecast_signal,
                compare_algorithm_results
            ],
            'elasticity': [
                fetch_pricing_promo_data,
                fetch_demand_forecast_signal,
                run_simulation_scenario
            ],
            
            # Mapping & Gap Detection
            'mapping': [
                fetch_schema,
                validate_against_schema,
                publish_cloudevent
            ],
            'gap_detection': [
                fetch_schema,
                validate_against_schema
            ],
        }
    
    def _build_tool_catalog(self) -> Dict[str, Any]:
        """Build catalog of all available tools by name."""
        return {
            # Redis Streams Tools
            'publish_cloudevent': publish_cloudevent,
            'fetch_cloudevent': fetch_cloudevent,
            'fetch_schema': fetch_schema,
            
            # Validation Tools
            'validate_against_schema': validate_against_schema,
            'publish_platform_action': publish_platform_action,
            
            # Simulation Tools
            'fetch_demand_forecast_signal': fetch_demand_forecast_signal,
            'fetch_inventory_position': fetch_inventory_position,
            'fetch_pricing_promo_data': fetch_pricing_promo_data,
            'fetch_campaign_performance': fetch_campaign_performance,
            'run_simulation_scenario': run_simulation_scenario,
            'compute_stockout_risk': compute_stockout_risk,
            
            # Algorithm Comparison Tools
            'compare_algorithm_results': compare_algorithm_results,
            'synthesize_multi_algorithm_insights': synthesize_multi_algorithm_insights,
        }
    
    def get_capability_vocabulary(self) -> List[str]:
        """Get list of all supported capabilities."""
        return sorted(list(self._capability_tool_map.keys()))
    
    def get_tool_vocabulary(self) -> List[str]:
        """Get list of all available tool names."""
        return sorted(list(self._tool_catalog.keys()))
    
    def validate_capabilities(self, capabilities: List[str]) -> Dict[str, Any]:
        """
        Validate that capabilities are recognized.
        
        Returns:
            Dict with 'valid', 'invalid', and 'suggestions' keys
        """
        valid = []
        invalid = []
        suggestions = {}
        
        for cap in capabilities:
            cap_lower = cap.lower()
            if cap_lower in self._capability_tool_map:
                valid.append(cap)
            else:
                invalid.append(cap)
                # Find similar capabilities (simple string matching)
                similar = [
                    known_cap for known_cap in self._capability_tool_map.keys()
                    if cap_lower in known_cap or known_cap in cap_lower
                ]
                if similar:
                    suggestions[cap] = similar
        
        return {
            'valid': valid,
            'invalid': invalid,
            'suggestions': suggestions
        }


# Singleton instance
_registry_instance = None

def get_tool_registry() -> ToolRegistry:
    """Get singleton instance of ToolRegistry."""
    global _registry_instance
    if _registry_instance is None:
        _registry_instance = ToolRegistry()
    return _registry_instance


# Convenience functions
def get_tools_for_capabilities(capabilities: List[str]) -> List[Any]:
    """Convenience function to get tools for capabilities."""
    return get_tool_registry().get_tools_for_capabilities(capabilities)


def get_tools_for_data_sources(data_sources: List[str]) -> List[Any]:
    """Convenience function to get tools for data sources."""
    return get_tool_registry().get_tools_for_data_sources(data_sources)


if __name__ == '__main__':
    # Test the registry
    registry = get_tool_registry()
    
    print("=" * 80)
    print("TOOL REGISTRY TEST")
    print("=" * 80)
    
    print(f"\nSupported Capabilities ({len(registry.get_capability_vocabulary())}):")
    for cap in registry.get_capability_vocabulary():
        print(f"  - {cap}")
    
    print(f"\nAvailable Tools ({len(registry.get_tool_vocabulary())}):")
    for tool in registry.get_tool_vocabulary():
        print(f"  - {tool}")
    
    print("\nTest: Get tools for ['forecasting', 'optimization']")
    tools = registry.get_tools_for_capabilities(['forecasting', 'optimization'])
    print(f"  Found {len(tools)} tools:")
    for tool in tools:
        print(f"    - {tool.__name__}")
    
    print("\nTest: Validate capabilities")
    result = registry.validate_capabilities(['forecasting', 'invalid_cap', 'optimization'])
    print(f"  Valid: {result['valid']}")
    print(f"  Invalid: {result['invalid']}")
    print(f"  Suggestions: {result['suggestions']}")
    
    print("\n" + "=" * 80)
