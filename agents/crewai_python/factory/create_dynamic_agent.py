#!/usr/bin/env python3
"""
Create Dynamic Agent from Spec
Called from Node.js UnifiedAgentDiscoveryService when no suitable agent found
"""

import sys
import os
import json
import asyncio
from pathlib import Path

# Redirect all non-JSON output to stderr so stdout only contains JSON
def log_info(msg):
    """Log to stderr (won't interfere with JSON output)"""
    print(msg, file=sys.stderr)

# Add parent directories to path
factory_dir = Path(__file__).parent
crewai_dir = factory_dir.parent
agents_dir = crewai_dir.parent
sys.path.insert(0, str(crewai_dir))
sys.path.insert(0, str(agents_dir))

from factory.agent_factory import get_agent_factory, AgentSpec
from factory.tool_registry import get_tool_registry
from factory.algorithm_tool_generator import get_algorithm_tool_generator

async def create_agent_from_spec(spec_json: str) -> dict:
    """
    Create a dynamic agent from a JSON specification.
    
    Args:
        spec_json: JSON string containing agent specification from Node.js
        
    Returns:
        Dict with agent info and status
    """
    try:
        spec = json.loads(spec_json)
        
        import time
        
        # Build trigger event from spec
        trigger_event = {
            'id': f"dynamic_{int(time.time())}",
            'type': 'agent.dynamic_creation_requested',
            'severity': 'medium',
            'data': {
                'query': spec.get('input', {}).get('query', ''),
                'intent': spec.get('input', {}).get('intent', {}),
                'entities': spec.get('input', {}).get('entities', {}),
                'agent_spec': spec
            }
        }
        
        # Build context from spec
        context = {
            'agent_name': spec.get('agentName'),
            'agent_type': spec.get('agentType'),
            'capabilities': spec.get('capabilities', []),
            'algorithms': spec.get('algorithms', []),
            'expected_insights': spec.get('expectedInsights', [])
        }
        
        # Available datasets (can be extended)
        available_datasets = spec.get('data_sources', [
            'demand_forecast',
            'inventory',
            'pricing',
            'campaign_performance'
        ])
        
        # Get factory and create agent
        factory = get_agent_factory()
        
        # Create agent spec from provided spec
        from datetime import datetime
        
        agent_spec = AgentSpec(
            role=spec.get('role', spec.get('agentName', 'Dynamic Specialist')),
            goal=spec.get('goal', 'Analyze and provide insights'),
            backstory=spec.get('backstory', 'Specialized agent created dynamically'),
            capabilities=spec.get('capabilities', []),
            required_tools=spec.get('required_tools', []),
            data_sources=available_datasets,
            output_format='CloudEvent with analysis results',
            allow_delegation=False,
            model='gpt-4o-mini',
            temperature=0.7,
            metadata={
                'trigger_type': trigger_event.get('type'),
                'generated_at': datetime.utcnow().isoformat(),
                'source': 'dynamic_creation',
                'algorithms': spec.get('algorithms', [])
            }
        )
        
        # Generate algorithm tools from spec
        algorithm_tool_generator = get_algorithm_tool_generator()
        algorithm_tools = []
        for algo_spec in spec.get('algorithms', []):
            try:
                algo_tool = algorithm_tool_generator.generate_tool_from_algorithm_spec(algo_spec)
                algorithm_tools.append(algo_tool)
                log_info(f"✅ Generated algorithm tool: {algo_spec.get('name', 'Unknown')}")
            except Exception as e:
                log_info(f"⚠️  Failed to generate algorithm tool {algo_spec.get('name', 'Unknown')}: {e}")
        
        # Select tools using tool registry (this is the key integration point)
        tool_registry = get_tool_registry()
        tools = factory._select_tools(agent_spec)
        
        # Add algorithm tools to the tool list
        tools.extend(algorithm_tools)
        
        # If multiple algorithms, add comparison tools
        if len(algorithm_tools) > 1:
            from tools.algorithm_comparison_tool import compare_algorithm_results, synthesize_multi_algorithm_insights
            if compare_algorithm_results not in tools:
                tools.append(compare_algorithm_results)
            if synthesize_multi_algorithm_insights not in tools:
                tools.append(synthesize_multi_algorithm_insights)
            log_info(f"✅ Added algorithm comparison tools (comparing {len(algorithm_tools)} algorithms)")
        
        # Create ontology profile
        ontology_profile = factory._create_ontology_profile(agent_spec)
        
        # Instantiate CrewAI agent
        from crewai import Agent
        agent = Agent(
            role=agent_spec.role,
            goal=agent_spec.goal,
            backstory=agent_spec.backstory,
            tools=tools,
            verbose=True,
            allow_delegation=agent_spec.allow_delegation,
            llm_config={
                'provider': 'openai',
                'model': agent_spec.model,
                'temperature': agent_spec.temperature
            }
        )
        
        # Generate agent ID
        agent_id = f"dynamic_{spec.get('agentType', 'agent').lower().replace(' ', '_')}_{int(time.time())}"
        
        # Register agent if Supabase available
        if factory.supabase:
            await factory._register_agent(agent, agent_spec, ontology_profile, trigger_event)
        
        # Save agent configuration to storage (Redis + file system) so runner can load it
        agent_config = {
            'agent_id': agent_id,
            'role': agent_spec.role,
            'goal': agent_spec.goal,
            'backstory': agent_spec.backstory,
            'capabilities': agent_spec.capabilities,
            'required_tools': agent_spec.required_tools,
            'data_sources': agent_spec.data_sources,
            'output_format': agent_spec.output_format,
            'allow_delegation': agent_spec.allow_delegation,
            'model': agent_spec.model,
            'temperature': agent_spec.temperature,
            'metadata': agent_spec.metadata,
            'tools': [t.__name__ if hasattr(t, '__name__') else str(t) for t in tools]
        }
        
        # Save to Redis
        try:
            import redis
            redis_client = redis.Redis(
                host=os.getenv('REDIS_HOST', 'localhost'),
                port=int(os.getenv('REDIS_PORT', 6379)),
                password=os.getenv('REDIS_PASSWORD'),
                decode_responses=True
            )
            config_key = f"dynamic_agent:config:{agent_id}"
            redis_client.set(config_key, json.dumps(agent_config), ex=86400)  # Expire after 24 hours
        except Exception as e:
            log_info(f"⚠️  Failed to save to Redis: {e}")
        
        # Also save to file system as backup
        try:
            storage_dir = Path(os.getenv('DYNAMIC_AGENT_STORAGE', '/tmp/dynamic_agents'))
            storage_dir.mkdir(parents=True, exist_ok=True)
            config_file = storage_dir / f"{agent_id}.json"
            with open(config_file, 'w') as f:
                json.dump(agent_config, f, indent=2)
        except Exception as e:
            log_info(f"⚠️  Failed to save to file: {e}")
        
        return {
            'success': True,
            'agent_id': agent_id,
            'agent_name': agent_spec.role,
            'capabilities': agent_spec.capabilities,
            'tools': agent_config['tools'],
            'algorithms': spec.get('algorithms', []),
            'registered': factory.supabase is not None,
            'config_saved': True
        }
        
    except Exception as e:
        return {
            'success': False,
            'error': str(e),
            'error_type': type(e).__name__
        }


def main():
    """CLI entry point - reads spec from stdin or first argument"""
    if len(sys.argv) > 1:
        spec_json = sys.argv[1]
    else:
        spec_json = sys.stdin.read()
    
    result = asyncio.run(create_agent_from_spec(spec_json))
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()

