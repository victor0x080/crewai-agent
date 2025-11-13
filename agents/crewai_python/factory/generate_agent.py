#!/usr/bin/env python3
"""
Bridge script for generating agents from TypeScript
Called by ProactiveAgentSpawner via subprocess

Usage:
    python generate_agent.py <trigger_file.json> <context_file.json>

Returns JSON to stdout:
    {
        "success": true,
        "agent_id": "dynamic_...",
        "role": "...",
        "goal": "...",
        "backstory": "...",
        "capabilities": [...],
        "tools": [...]
    }
"""
import sys
import os
sys.path.append(os.path.dirname(__file__))

import json
import asyncio
import time
from agent_factory import get_agent_factory


async def main():
    """Main entry point for agent generation."""
    
    # Validate arguments
    if len(sys.argv) < 3:
        error_response = {
            'success': False,
            'error': 'Missing arguments. Usage: generate_agent.py <trigger_file> <context_file>'
        }
        print(json.dumps(error_response), file=sys.stderr)
        sys.exit(1)
    
    trigger_file = sys.argv[1]
    context_file = sys.argv[2]
    
    try:
        # Load trigger event
        with open(trigger_file, 'r') as f:
            trigger_event = json.load(f)
        
        # Load context
        with open(context_file, 'r') as f:
            context = json.load(f)
        
        # Extract available datasets from context
        available_datasets = context.get('available_datasets', [
            'demand_forecast',
            'inventory',
            'pricing',
            'campaign_performance'
        ])
        
        # Get agent factory instance
        factory = get_agent_factory()
        
        # Generate agent
        print(f"Generating agent for trigger: {trigger_event.get('type', 'unknown')}", file=sys.stderr)
        
        agent = await factory.generate_agent_from_trigger(
            trigger_event,
            context,
            available_datasets,
            use_cache=True  # Enable caching for performance
        )
        
        # Extract agent metadata
        # Note: CrewAI Agent doesn't store capabilities directly, 
        # so we need to reconstruct from the generation process
        agent_id = f"dynamic_{agent.role.lower().replace(' ', '_').replace('-', '_')}_{int(time.time())}"
        
        # Build response
        result = {
            'success': True,
            'agent_id': agent_id,
            'role': agent.role,
            'goal': agent.goal,
            'backstory': agent.backstory,
            'tools': [t.__name__ for t in agent.tools] if hasattr(agent, 'tools') else [],
            'allow_delegation': agent.allow_delegation if hasattr(agent, 'allow_delegation') else False,
            'verbose': agent.verbose if hasattr(agent, 'verbose') else True,
            'llm_config': agent.llm_config if hasattr(agent, 'llm_config') else {},
            'generated_at': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
            'trigger_type': trigger_event.get('type'),
            'trigger_severity': trigger_event.get('severity')
        }
        
        # Output result to stdout (TypeScript will parse this)
        print(json.dumps(result, indent=2))
        
        # Log success to stderr (for debugging)
        print(f"✅ Successfully generated agent: {agent.role}", file=sys.stderr)
        
        sys.exit(0)
    
    except FileNotFoundError as e:
        error_response = {
            'success': False,
            'error': f'File not found: {e.filename}'
        }
        print(json.dumps(error_response), file=sys.stderr)
        sys.exit(1)
    
    except json.JSONDecodeError as e:
        error_response = {
            'success': False,
            'error': f'Invalid JSON in input file: {e.msg}'
        }
        print(json.dumps(error_response), file=sys.stderr)
        sys.exit(1)
    
    except Exception as e:
        error_response = {
            'success': False,
            'error': str(e),
            'error_type': type(e).__name__
        }
        print(json.dumps(error_response), file=sys.stderr)
        print(f"❌ Agent generation failed: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    # Run async main
    asyncio.run(main())
