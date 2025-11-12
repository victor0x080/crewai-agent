"""Dynamic Agent Runner - Loads and executes dynamically created agents from Redis Streams"""
import sys
import json
import os
from pathlib import Path

# Add parent directory to path so we can import base_runner
sys.path.insert(0, str(Path(__file__).parent.parent))
from base_runner import AgentRunner
from factory.agent_factory import get_agent_factory, AgentSpec
from factory.tool_registry import get_tool_registry
from crewai import Agent

def load_dynamic_agent(agent_id: str) -> Agent:
    """
    Load a dynamically created agent from storage.
    Agent config is stored in Redis or file system.
    """
    import redis
    from pathlib import Path
    
    # Try to load from Redis first
    try:
        redis_client = redis.Redis(
            host=os.getenv('REDIS_HOST', 'localhost'),
            port=int(os.getenv('REDIS_PORT', 6379)),
            password=os.getenv('REDIS_PASSWORD'),
            decode_responses=True
        )
        
        # Check if agent config exists in Redis
        config_key = f"dynamic_agent:config:{agent_id}"
        config_json = redis_client.get(config_key)
        
        if config_json:
            config = json.loads(config_json)
            return _create_agent_from_config(config)
    except Exception as e:
        print(f"⚠️  Failed to load from Redis: {e}")
    
    # Fallback: try to load from file system
    try:
        storage_dir = Path(os.getenv('DYNAMIC_AGENT_STORAGE', '/tmp/dynamic_agents'))
        storage_dir.mkdir(parents=True, exist_ok=True)
        config_file = storage_dir / f"{agent_id}.json"
        
        if config_file.exists():
            with open(config_file, 'r') as f:
                config = json.load(f)
            return _create_agent_from_config(config)
    except Exception as e:
        print(f"⚠️  Failed to load from file: {e}")
    
    raise ValueError(f"Dynamic agent {agent_id} not found in storage")


def _create_agent_from_config(config: dict) -> Agent:
    """Create a CrewAI Agent from stored configuration"""
    factory = get_agent_factory()
    
    # Recreate AgentSpec from config
    agent_spec = AgentSpec(
        role=config.get('role', 'Dynamic Specialist'),
        goal=config.get('goal', 'Analyze and provide insights'),
        backstory=config.get('backstory', 'Specialized agent created dynamically'),
        capabilities=config.get('capabilities', []),
        required_tools=config.get('required_tools', []),
        data_sources=config.get('data_sources', []),
        output_format=config.get('output_format', 'CloudEvent with analysis results'),
        allow_delegation=config.get('allow_delegation', False),
        model=config.get('model', 'gpt-4o-mini'),
        temperature=config.get('temperature', 0.7),
        metadata=config.get('metadata', {})
    )
    
    # Select tools using tool registry
    tools = factory._select_tools(agent_spec)
    
    # Create CrewAI Agent
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
    
    return agent


def main():
    """Main entry point - expects agent_id as command line argument"""
    if len(sys.argv) < 2:
        print("Usage: dynamic_runner.py <agent_id>")
        sys.exit(1)
    
    agent_id = sys.argv[1]
    
    try:
        # Load the dynamic agent
        agent = load_dynamic_agent(agent_id)
        
        # Normalize agent_id for stream names (must match Node.js normalization)
        # Node.js uses: agentId.toLowerCase().replace(/[^a-z0-9-]/g, '-')
        import re
        normalized_id = agent_id.lower()
        normalized_id = re.sub(r'[^a-z0-9-]', '-', normalized_id)  # Replace all non-alphanumeric (except dash) with dash
        normalized_id = re.sub(r'-+', '-', normalized_id)  # Collapse multiple dashes
        normalized_id = normalized_id.strip('-')  # Remove leading/trailing dashes
        
        # Create runner
        runner = AgentRunner(
            agent=agent,
            input_stream=f'stream:agent:{normalized_id}:in',
            output_stream=f'stream:agent:{normalized_id}:out',
            group=f'dynamic-{normalized_id}',
            name=f'{normalized_id}-1',
            output_type='mco.event.observation'
        )
        
        # Start the runner (this blocks and listens on Redis stream)
        runner.run()
        
    except Exception as e:
        print(f"❌ Failed to start dynamic agent runner: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()

