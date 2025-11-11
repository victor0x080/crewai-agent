"""
Integration Example: Wire CrewAI Event Listener to Existing Agents
Shows how to add semantic filtering to plan_review_agent, data_query_agent, etc.
"""

from crewai import Crew
from crewai.events import CrewAIEventsBus
from crewai_event_listener import SemanticBusListener

# Import your existing agents
from plan_review_agent import plan_review_agent
from data_query_agent import data_query_agent
from stream_capture_agent import stream_capture_agent
from system_call_zapier_agent import system_call_agent

def create_monitored_crew_with_listener(agents, tasks, policies_path="crewai_policies.yaml"):
    """
    Create a CrewAI crew with semantic event listener attached.
    
    This enables automatic filtering and broadcasting of agent events
    to Redis Streams based on semantic policies.
    
    Args:
        agents: List of CrewAI agents
        tasks: List of CrewAI tasks
        policies_path: Path to policies YAML file
    
    Returns:
        Crew instance with event listener attached
    """
    
    # Create the crew
    crew = Crew(
        agents=agents,
        tasks=tasks,
        verbose=True
    )
    
    # Get the CrewAI event bus
    event_bus = CrewAIEventsBus()
    
    # Create and register semantic listener
    listener = SemanticBusListener(policies_path)
    listener.setup_listeners(event_bus)
    
    print(f"[Integration] Semantic event listener attached to crew with {len(agents)} agents")
    
    return crew, listener

# Example 1: Add listener to plan review workflow
def monitored_plan_review_workflow():
    """Plan review with automatic event broadcasting"""
    from crewai import Task
    
    task = Task(
        description="Query the strategic plan for Q4 revenue targets and provide analysis.",
        expected_output="JSON with Q4 revenue analysis",
        agent=plan_review_agent
    )
    
    crew, listener = create_monitored_crew_with_listener(
        agents=[plan_review_agent],
        tasks=[task]
    )
    
    # Execute - events will be automatically filtered and broadcast
    result = crew.kickoff()
    
    return result

# Example 2: Add listener to data query workflow
def monitored_data_query_workflow():
    """Data query with automatic event broadcasting"""
    from crewai import Task
    
    task = Task(
        description="Query sales_transactions dataset for total revenue by region.",
        expected_output="JSON with revenue by region",
        agent=data_query_agent
    )
    
    crew, listener = create_monitored_crew_with_listener(
        agents=[data_query_agent],
        tasks=[task]
    )
    
    result = crew.kickoff()
    
    return result

# Example 3: Multi-agent workflow with listener
def monitored_multi_agent_workflow():
    """Multi-agent workflow with semantic filtering"""
    from crewai import Task
    
    # Plan review task
    plan_task = Task(
        description="Review strategic plan for Q4 targets",
        expected_output="Strategic plan summary",
        agent=plan_review_agent
    )
    
    # Data query task
    data_task = Task(
        description="Query actual Q4 sales data",
        expected_output="Q4 sales data",
        agent=data_query_agent,
        context=[plan_task]  # Depends on plan task
    )
    
    # Analysis task
    analysis_task = Task(
        description="""Compare strategic plan targets with actual sales data.
        Identify gaps and provide recommendations.""",
        expected_output="Gap analysis and recommendations",
        agent=plan_review_agent,
        context=[plan_task, data_task]
    )
    
    crew, listener = create_monitored_crew_with_listener(
        agents=[plan_review_agent, data_query_agent],
        tasks=[plan_task, data_task, analysis_task]
    )
    
    result = crew.kickoff()
    
    return result

# Example 4: Hierarchical crew with manager and listener
def monitored_hierarchical_workflow():
    """Hierarchical process with semantic filtering"""
    from crewai import Process, Task
    from crewai import Agent
    
    # Create a manager agent
    manager = Agent(
        role="Strategic Planning Manager",
        goal="Coordinate analysis of strategic plans and data",
        backstory="""You are a senior manager who coordinates strategic planning 
        analysis. You delegate tasks to specialists and synthesize their findings.""",
        allow_delegation=True,
        verbose=True
    )
    
    tasks = [
        Task(
            description="Analyze Q4 strategic plan targets",
            expected_output="Strategic plan analysis",
            agent=plan_review_agent
        ),
        Task(
            description="Query Q4 actual sales data",
            expected_output="Sales data",
            agent=data_query_agent
        )
    ]
    
    crew, listener = create_monitored_crew_with_listener(
        agents=[manager, plan_review_agent, data_query_agent],
        tasks=tasks
    )
    
    # Set hierarchical process
    crew.process = Process.hierarchical
    crew.manager_agent = manager
    
    result = crew.kickoff()
    
    return result

# Example 5: Retrofit existing agent with listener
def retrofit_existing_agent_script():
    """
    Shows how to add listener to an existing agent script
    that already has its own Redis Streams consumer loop.
    """
    import redis
    from crewai import Task, Crew
    from crewai.events import CrewAIEventsBus
    from crewai_event_listener import SemanticBusListener
    
    redis_client = redis.Redis(host='localhost', port=6379, decode_responses=True)
    
    # Your existing stream consumer setup
    input_stream = "stream:agents:plan-review:requests:v1"
    consumer_group = "plan-review-agents"
    
    # Initialize listener ONCE at startup
    event_bus = CrewAIEventsBus()
    listener = SemanticBusListener("crewai_policies.yaml")
    listener.setup_listeners(event_bus)
    
    print("[Retrofit] Event listener initialized")
    
    # Your existing consumer loop
    while True:
        messages = redis_client.xreadgroup(
            consumer_group,
            "consumer-1",
            {input_stream: ">"},
            count=1,
            block=5000
        )
        
        if not messages:
            continue
        
        for stream, entries in messages:
            for message_id, fields in entries:
                # Get event
                event_id = fields.get("event_id")
                source_event = redis_client.json().get(f"event:{event_id}")
                
                # Extract query
                query = source_event.get("data", {}).get("query", "")
                
                # Create task
                task = Task(
                    description=f"Analyze query: {query}",
                    expected_output="Analysis result",
                    agent=plan_review_agent
                )
                
                # Execute with listener attached
                crew = Crew(agents=[plan_review_agent], tasks=[task])
                result = crew.kickoff()
                
                # Listener automatically captured and filtered events!
                
                # Your existing response publishing
                # ...
                
                redis_client.xack(input_stream, consumer_group, message_id)

# Example 6: Custom event filtering function
def custom_event_filter_example():
    """
    Add custom filtering logic on top of semantic policies.
    """
    from crewai_event_listener import SemanticBusListener
    
    class CustomSemanticListener(SemanticBusListener):
        """Extended listener with custom filters"""
        
        def _try_publish(self, payload):
            """Override to add custom logic"""
            
            # Custom filter 1: Only high-value agents
            agent_name = payload.get("agent", {}).get("name", "")
            if "test" in agent_name.lower():
                print(f"[CustomFilter] Skipping test agent: {agent_name}")
                return
            
            # Custom filter 2: Only successful executions with output
            if not payload.get("success"):
                print(f"[CustomFilter] Skipping failed execution")
                return
            
            if not payload.get("output", "").strip():
                print(f"[CustomFilter] Skipping empty output")
                return
            
            # Custom filter 3: Token threshold
            tokens = payload.get("metadata", {}).get("tokens", 0)
            if tokens > 0 and tokens < 20:
                print(f"[CustomFilter] Skipping trivial output ({tokens} tokens)")
                return
            
            # Pass to semantic policy engine
            super()._try_publish(payload)
    
    # Use custom listener
    listener = CustomSemanticListener("crewai_policies.yaml")
    return listener

# Testing
if __name__ == "__main__":
    print("="*80)
    print("CREWAI EVENT LISTENER INTEGRATION EXAMPLES")
    print("="*80 + "\n")
    
    print("Example 1: Monitored plan review workflow")
    print("  - Creates crew with plan_review_agent")
    print("  - Attaches semantic event listener")
    print("  - Automatically broadcasts strategic insights\n")
    
    print("Example 2: Monitored data query workflow")
    print("  - Creates crew with data_query_agent")
    print("  - Filters and broadcasts significant data findings\n")
    
    print("Example 3: Multi-agent workflow")
    print("  - Coordinates plan review + data query")
    print("  - Broadcasts each agent's contributions\n")
    
    print("Example 4: Hierarchical workflow with manager")
    print("  - Manager delegates to specialists")
    print("  - Captures all agent activities\n")
    
    print("Example 5: Retrofit existing agent script")
    print("  - Add listener to existing Redis consumer loop")
    print("  - No changes to existing code structure\n")
    
    print("Example 6: Custom event filtering")
    print("  - Extend listener with custom logic")
    print("  - Add domain-specific filters\n")
    
    print("="*80)
    print("To use: Import and call these functions in your agent scripts")
    print("="*80)
