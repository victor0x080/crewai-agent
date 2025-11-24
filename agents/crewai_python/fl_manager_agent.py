"""
Federated Learning Manager Agent
=================================

A CrewAI agent that serves as the interface for managing federated learning jobs.

Complies with:
- CloudEvents 1.0 for all messages
- Redis Streams for event bus
- JSON Schema validation
- Ontology integration
- CrewAI design patterns

Responsibilities:
- Create and manage FL training runs
- Register and monitor FL clients
- Orchestrate federated rounds
- Publish model results to RAG
- Monitor training progress
- Handle failures and retries
"""

from crewai import Agent, Task, Crew, Process
from crewai_tools import tool
from typing import Dict, List, Any, Optional
import json
import redis
from datetime import datetime
from pathlib import Path

# Import existing tools
import sys
sys.path.append(str(Path(__file__).parent))
from tools.redis_streams_tools import publish_cloudevent, fetch_cloudevent, redis_ack
from tools.schema_tools import validate_against_schema, fetch_schema
from tools.ontology_tools import resolve_concept, expand_concepts, map_enum
from tools.fl_rag_integration import (
    publish_fl_model_to_rag,
    publish_fl_training_summary_to_rag,
    query_fl_models_from_rag
)
from tools.flower_tools import (
    start_federated_training,
    register_fl_client,
    save_fl_model,
    get_fl_run_metrics,
    update_fl_run_status
)

# Redis client
redis_client = redis.Redis(host='localhost', port=6379, decode_responses=True)


# ===================================================================
# FL MANAGER TOOLS
# ===================================================================

@tool
def create_fl_training_run(
    run_name: str,
    dataset_name: str,
    num_rounds: int,
    min_clients: int,
    model_type: str = "logistic_regression",
    strategy: str = "FedAvg"
) -> Dict[str, Any]:
    """
    Create a new federated learning training run.
    
    Use this to initiate a new FL training job with specified configuration.
    
    Args:
        run_name: Human-readable name for the run
        dataset_name: Dataset identifier (e.g., 'call_center_csat')
        num_rounds: Number of federated rounds
        min_clients: Minimum clients required per round
        model_type: Model type ('logistic_regression' or 'random_forest')
        strategy: Aggregation strategy (default: 'FedAvg')
    
    Returns:
        {
            'run_id': str,
            'status': str,
            'config': Dict,
            'event_published': bool
        }
    
    Example:
        result = create_fl_training_run(
            run_name='Q4 CSAT Prediction',
            dataset_name='call_center_csat',
            num_rounds=5,
            min_clients=3
        )
    """
    
    # Generate run ID
    run_id = f"fl_run_{int(datetime.utcnow().timestamp())}_{hash(run_name) % 10000}"
    
    # Create run configuration
    run_config = {
        'run_id': run_id,
        'run_name': run_name,
        'dataset_name': dataset_name,
        'model_type': model_type,
        'num_rounds': num_rounds,
        'min_clients': min_clients,
        'strategy': strategy,
        'status': 'initialized',
        'created_at': datetime.utcnow().isoformat(),
        'current_round': 0,
        'registered_clients': []
    }
    
    # Store in Redis
    redis_client.set(f"fl:run:{run_id}", json.dumps(run_config))
    
    # Publish CloudEvent
    event_published = publish_cloudevent(
        stream_key='fl:events',
        event_type='com.flowerai.fl.run.created',
        source='urn:flowerai:manager_agent',
        subject=run_id,
        data={
            'run_id': run_id,
            'run_name': run_name,
            'config': run_config,
            '@context': {
                '@vocab': 'https://ontology.flowerai.com/fl#',
                'run_id': 'fl:RunIdentifier',
                'dataset_name': 'fl:DatasetName',
                'strategy': 'fl:AggregationStrategy'
            }
        }
    )
    
    return {
        'run_id': run_id,
        'status': 'initialized',
        'config': run_config,
        'event_published': event_published.get('published', False),
        'message': f"FL training run '{run_name}' created with ID {run_id}"
    }


@tool
def monitor_fl_training_progress(run_id: str) -> Dict[str, Any]:
    """
    Monitor the progress of a federated learning training run.
    
    Use this to check status, metrics, and convergence of an FL run.
    
    Args:
        run_id: FL run identifier
    
    Returns:
        {
            'run_id': str,
            'status': str,
            'current_round': int,
            'num_rounds': int,
            'metrics': Dict,
            'convergence_status': str
        }
    
    Example:
        progress = monitor_fl_training_progress('fl_run_123')
        print(f"Round {progress['current_round']}/{progress['num_rounds']}")
        print(f"Accuracy: {progress['metrics']['accuracy']}")
    """
    
    # Get run config
    run_data = redis_client.get(f"fl:run:{run_id}")
    if not run_data:
        return {
            'error': f"FL run {run_id} not found",
            'run_id': run_id
        }
    
    run_config = json.loads(run_data)
    
    # Get latest metrics
    metrics = get_fl_run_metrics(run_id)
    
    # Analyze convergence
    convergence_status = _analyze_convergence(metrics)
    
    return {
        'run_id': run_id,
        'status': run_config.get('status'),
        'current_round': run_config.get('current_round', 0),
        'num_rounds': run_config.get('num_rounds'),
        'registered_clients': len(run_config.get('registered_clients', [])),
        'metrics': metrics,
        'convergence_status': convergence_status
    }


@tool
def register_client_for_fl_run(
    run_id: str,
    client_id: str,
    client_name: str,
    data_silo_size: int,
    data_features: List[str]
) -> Dict[str, Any]:
    """
    Register a client (data silo) for a federated learning run.
    
    Use this when a new organization wants to participate in FL training.
    
    Args:
        run_id: FL run identifier
        client_id: Unique client identifier
        client_name: Human-readable client name
        data_silo_size: Number of samples at this client
        data_features: List of available features
    
    Returns:
        {
            'client_id': str,
            'registered': bool,
            'run_id': str
        }
    
    Example:
        result = register_client_for_fl_run(
            run_id='fl_run_123',
            client_id='client_east',
            client_name='Call Center East',
            data_silo_size=2500,
            data_features=['sentiment', 'call_duration', 'response_time']
        )
    """
    
    # Register client
    registration = register_fl_client(
        run_id=run_id,
        client_id=client_id,
        client_name=client_name,
        data_silo_size=data_silo_size,
        data_features=data_features
    )
    
    # Update run config
    run_data = redis_client.get(f"fl:run:{run_id}")
    if run_data:
        run_config = json.loads(run_data)
        if client_id not in run_config.get('registered_clients', []):
            run_config['registered_clients'].append(client_id)
            redis_client.set(f"fl:run:{run_id}", json.dumps(run_config))
    
    # Publish CloudEvent
    publish_cloudevent(
        stream_key='fl:events',
        event_type='com.flowerai.fl.client.registered',
        source='urn:flowerai:manager_agent',
        subject=f"{run_id}/{client_id}",
        data={
            'run_id': run_id,
            'client_id': client_id,
            'client_name': client_name,
            'data_silo_size': data_silo_size,
            '@context': {
                '@vocab': 'https://ontology.flowerai.com/fl#'
            }
        }
    )
    
    return {
        'client_id': client_id,
        'registered': registration.get('registered', False),
        'run_id': run_id,
        'message': f"Client '{client_name}' registered for run {run_id}"
    }


@tool
def finalize_fl_training_run(
    run_id: str,
    publish_to_rag: bool = True
) -> Dict[str, Any]:
    """
    Finalize a federated learning training run and publish results.
    
    Use this when FL training completes to:
    - Save final model
    - Publish to RAG for discoverability
    - Generate training summary
    - Update run status
    
    Args:
        run_id: FL run identifier
        publish_to_rag: Whether to publish results to RAG (default: True)
    
    Returns:
        {
            'run_id': str,
            'final_model_version': str,
            'metrics': Dict,
            'published_to_rag': bool,
            'summary': str
        }
    
    Example:
        result = finalize_fl_training_run('fl_run_123')
        print(f"Final model: {result['final_model_version']}")
        print(f"Accuracy: {result['metrics']['accuracy']}")
    """
    
    # Get run config and metrics
    run_data = redis_client.get(f"fl:run:{run_id}")
    if not run_data:
        return {'error': f"FL run {run_id} not found"}
    
    run_config = json.loads(run_data)
    metrics = get_fl_run_metrics(run_id)
    
    # Get final model version
    final_round = run_config.get('num_rounds', 0)
    final_model_version = f"{run_id}_r{final_round}"
    
    # Generate training summary
    summary = _generate_training_summary(run_config, metrics)
    
    # Update run status
    run_config['status'] = 'completed'
    run_config['completed_at'] = datetime.utcnow().isoformat()
    redis_client.set(f"fl:run:{run_id}", json.dumps(run_config))
    
    update_fl_run_status(run_id, 'completed')
    
    # Publish to RAG if requested
    rag_published = False
    if publish_to_rag:
        # Publish model
        model_result = publish_fl_model_to_rag(
            model_version=final_model_version,
            run_id=run_id,
            metrics=metrics.get('final_metrics', {}),
            model_metadata={
                'dataset': run_config.get('dataset_name'),
                'num_clients': len(run_config.get('registered_clients', [])),
                'num_rounds': run_config.get('num_rounds'),
                'strategy': run_config.get('strategy'),
                'model_type': run_config.get('model_type')
            },
            training_summary=summary
        )
        
        # Publish training summary
        summary_result = publish_fl_training_summary_to_rag(
            run_id=run_id,
            run_name=run_config.get('run_name'),
            num_rounds=run_config.get('num_rounds'),
            num_clients=len(run_config.get('registered_clients', [])),
            final_metrics=metrics.get('final_metrics', {}),
            convergence_analysis=_analyze_convergence(metrics),
            privacy_guarantees='No raw data shared between organizations. Local training only.'
        )
        
        rag_published = model_result.get('published_to_rag', False) and summary_result.get('published', False)
    
    # Publish completion event
    publish_cloudevent(
        stream_key='fl:events',
        event_type='com.flowerai.fl.run.completed',
        source='urn:flowerai:manager_agent',
        subject=run_id,
        data={
            'run_id': run_id,
            'final_model_version': final_model_version,
            'metrics': metrics.get('final_metrics', {}),
            'published_to_rag': rag_published,
            '@context': {
                '@vocab': 'https://ontology.flowerai.com/fl#'
            }
        }
    )
    
    return {
        'run_id': run_id,
        'final_model_version': final_model_version,
        'metrics': metrics.get('final_metrics', {}),
        'published_to_rag': rag_published,
        'summary': summary,
        'message': f"FL training run {run_id} completed successfully"
    }


@tool
def query_fl_training_history(
    filters: Optional[Dict] = None
) -> Dict[str, Any]:
    """
    Query historical federated learning training runs.
    
    Use this to find past FL runs, compare performance, or retrieve models.
    
    Args:
        filters: Optional filters (dataset, min_accuracy, date_range)
    
    Returns:
        {
            'runs': List[Dict],
            'count': int,
            'best_performing': Dict
        }
    
    Example:
        history = query_fl_training_history(
            filters={'dataset': 'call_center_csat', 'min_accuracy': 0.85}
        )
        print(f"Found {history['count']} runs")
        print(f"Best: {history['best_performing']['run_id']}")
    """
    
    # Query from RAG
    query = "Show me federated learning training runs"
    if filters:
        if 'dataset' in filters:
            query += f" for dataset {filters['dataset']}"
        if 'min_accuracy' in filters:
            query += f" with accuracy above {filters['min_accuracy']}"
    
    rag_result = query_fl_models_from_rag(query, filters)
    
    # Get runs from Redis
    run_keys = redis_client.keys("fl:run:*")
    runs = []
    for key in run_keys:
        run_data = redis_client.get(key)
        if run_data:
            run_config = json.loads(run_data)
            # Apply filters
            if filters:
                if 'dataset' in filters and run_config.get('dataset_name') != filters['dataset']:
                    continue
            runs.append(run_config)
    
    # Find best performing
    best_performing = None
    if rag_result.get('models'):
        best_model = max(rag_result['models'], key=lambda m: m.get('metrics', {}).get('accuracy', 0))
        best_performing = best_model
    
    return {
        'runs': runs,
        'count': len(runs),
        'best_performing': best_performing,
        'rag_answer': rag_result.get('answer')
    }


# ===================================================================
# HELPER FUNCTIONS
# ===================================================================

def _analyze_convergence(metrics: Dict) -> str:
    """Analyze convergence status from metrics."""
    if not metrics or 'round_metrics' not in metrics:
        return 'insufficient_data'
    
    round_metrics = metrics['round_metrics']
    if len(round_metrics) < 2:
        return 'early_stage'
    
    # Check if accuracy is improving
    accuracies = [r.get('metrics', {}).get('avg_accuracy', 0) for r in round_metrics]
    if len(accuracies) >= 3:
        recent_improvement = accuracies[-1] - accuracies[-3]
        if recent_improvement < 0.01:
            return 'converged'
        elif recent_improvement > 0.05:
            return 'improving'
        else:
            return 'slow_convergence'
    
    return 'in_progress'


def _generate_training_summary(run_config: Dict, metrics: Dict) -> str:
    """Generate natural language training summary."""
    run_name = run_config.get('run_name', 'Unknown')
    num_rounds = run_config.get('num_rounds', 0)
    num_clients = len(run_config.get('registered_clients', []))
    strategy = run_config.get('strategy', 'FedAvg')
    
    final_metrics = metrics.get('final_metrics', {})
    accuracy = final_metrics.get('accuracy', 0)
    
    summary = f"""
Federated Learning Training Run: {run_name}

Configuration:
- Strategy: {strategy}
- Rounds: {num_rounds}
- Participating Clients: {num_clients}

Performance:
- Final Accuracy: {accuracy:.2%}
- Convergence: {_analyze_convergence(metrics)}

This federated learning model was trained across {num_clients} independent data silos 
over {num_rounds} rounds using the {strategy} aggregation strategy. The model achieved 
{accuracy:.2%} accuracy without sharing raw data between organizations, preserving 
privacy while enabling collaborative learning.
    """.strip()
    
    return summary


# ===================================================================
# FL MANAGER AGENT DEFINITION
# ===================================================================

fl_manager_agent = Agent(
    role='Federated Learning Manager',
    goal='Manage federated learning training runs, coordinate clients, monitor progress, and publish results to RAG for discoverability',
    backstory="""You are an expert in federated learning orchestration and privacy-preserving 
    machine learning. You understand how to coordinate multiple organizations training models 
    collaboratively without sharing raw data. You ensure all FL operations follow CloudEvents 
    standards, publish to Redis Streams, and integrate with the RAG system for discoverability.
    
    You are responsible for:
    - Creating and configuring FL training runs
    - Registering and managing FL clients (data silos)
    - Monitoring training progress and convergence
    - Publishing results to RAG for natural language queries
    - Ensuring privacy and compliance throughout the process
    """,
    tools=[
        # FL-specific tools
        create_fl_training_run,
        monitor_fl_training_progress,
        register_client_for_fl_run,
        finalize_fl_training_run,
        query_fl_training_history,
        # Standard compliance tools
        publish_cloudevent,
        fetch_cloudevent,
        redis_ack,
        validate_against_schema,
        fetch_schema,
        resolve_concept,
        expand_concepts,
        map_enum
    ],
    allow_delegation=False,
    verbose=True
)


# ===================================================================
# FL MANAGER TASKS
# ===================================================================

def create_fl_management_task(
    task_type: str,
    inputs: Dict[str, Any]
) -> Task:
    """
    Create a task for the FL Manager Agent.
    
    Args:
        task_type: Type of task ('create_run', 'monitor', 'register_client', 'finalize', 'query_history')
        inputs: Task-specific inputs
    
    Returns:
        CrewAI Task
    """
    
    task_descriptions = {
        'create_run': f"""
        Create a new federated learning training run with the following configuration:
        - Run Name: {inputs.get('run_name')}
        - Dataset: {inputs.get('dataset_name')}
        - Number of Rounds: {inputs.get('num_rounds')}
        - Minimum Clients: {inputs.get('min_clients')}
        
        Ensure the run is properly configured and a CloudEvent is published to fl:events.
        """,
        
        'monitor': f"""
        Monitor the progress of federated learning run: {inputs.get('run_id')}
        
        Check:
        - Current round and status
        - Registered clients
        - Training metrics
        - Convergence status
        
        Provide a comprehensive progress report.
        """,
        
        'register_client': f"""
        Register a new client for federated learning run: {inputs.get('run_id')}
        
        Client Details:
        - Client ID: {inputs.get('client_id')}
        - Client Name: {inputs.get('client_name')}
        - Data Silo Size: {inputs.get('data_silo_size')}
        
        Ensure the client is registered and a CloudEvent is published.
        """,
        
        'finalize': f"""
        Finalize federated learning run: {inputs.get('run_id')}
        
        Complete the following:
        1. Save the final model
        2. Publish model and training summary to RAG
        3. Update run status to completed
        4. Publish completion CloudEvent
        
        Ensure all results are discoverable via natural language queries.
        """,
        
        'query_history': f"""
        Query the history of federated learning training runs.
        
        Filters: {inputs.get('filters', {})}
        
        Provide:
        - List of matching runs
        - Best performing model
        - Summary from RAG
        """
    }
    
    return Task(
        description=task_descriptions.get(task_type, 'Unknown task'),
        agent=fl_manager_agent,
        expected_output='JSON object with task results and status'
    )


# ===================================================================
# FL MANAGER CREW
# ===================================================================

def create_fl_manager_crew() -> Crew:
    """Create a crew with the FL Manager Agent."""
    
    return Crew(
        agents=[fl_manager_agent],
        tasks=[],  # Tasks added dynamically
        process=Process.sequential,
        verbose=True
    )


# ===================================================================
# EVENT BUS INTEGRATION
# ===================================================================

def handle_fl_management_event(event: Dict[str, Any]) -> Dict[str, Any]:
    """
    Handle incoming FL management events from Redis Streams.
    
    This is the event bus integration point that follows the agent design pattern:
    1. Receive CloudEvent from Redis Stream
    2. Validate against schema
    3. Map to FL Manager task
    4. Execute agent
    5. Publish result as CloudEvent
    
    Args:
        event: CloudEvent from Redis Stream
    
    Returns:
        Result CloudEvent
    """
    
    # Validate event
    event_type = event.get('type')
    data = event.get('data', {})
    
    # Map event type to task
    task_mapping = {
        'com.flowerai.fl.run.create.requested': 'create_run',
        'com.flowerai.fl.run.monitor.requested': 'monitor',
        'com.flowerai.fl.client.register.requested': 'register_client',
        'com.flowerai.fl.run.finalize.requested': 'finalize',
        'com.flowerai.fl.history.query.requested': 'query_history'
    }
    
    task_type = task_mapping.get(event_type)
    if not task_type:
        return {
            'error': f'Unknown event type: {event_type}',
            'event_id': event.get('id')
        }
    
    # Create and execute task
    task = create_fl_management_task(task_type, data)
    crew = create_fl_manager_crew()
    crew.tasks = [task]
    
    result = crew.kickoff()
    
    # Publish result as CloudEvent
    result_event = publish_cloudevent(
        stream_key='fl:events',
        event_type=f"{event_type.replace('.requested', '.completed')}",
        source='urn:flowerai:manager_agent',
        subject=event.get('subject'),
        data={
            'original_event_id': event.get('id'),
            'result': result,
            '@context': {
                '@vocab': 'https://ontology.flowerai.com/fl#'
            }
        }
    )
    
    # Acknowledge original event
    redis_ack(event.get('id'))
    
    return result_event


# ===================================================================
# CLI ENTRYPOINT
# ===================================================================

def main():
    """CLI entrypoint for FL Manager Agent."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Federated Learning Manager Agent")
    parser.add_argument('--action', type=str, required=True,
                       choices=['create', 'monitor', 'register', 'finalize', 'query'],
                       help='Action to perform')
    parser.add_argument('--run-id', type=str, help='FL run ID')
    parser.add_argument('--run-name', type=str, help='FL run name')
    parser.add_argument('--dataset', type=str, default='call_center_csat', help='Dataset name')
    parser.add_argument('--num-rounds', type=int, default=5, help='Number of rounds')
    parser.add_argument('--min-clients', type=int, default=2, help='Minimum clients')
    parser.add_argument('--client-id', type=str, help='Client ID')
    parser.add_argument('--client-name', type=str, help='Client name')
    parser.add_argument('--data-size', type=int, help='Data silo size')
    
    args = parser.parse_args()
    
    # Map action to task
    task_type_map = {
        'create': 'create_run',
        'monitor': 'monitor',
        'register': 'register_client',
        'finalize': 'finalize',
        'query': 'query_history'
    }
    
    # Build inputs
    inputs = {}
    if args.action == 'create':
        inputs = {
            'run_name': args.run_name,
            'dataset_name': args.dataset,
            'num_rounds': args.num_rounds,
            'min_clients': args.min_clients
        }
    elif args.action in ['monitor', 'finalize']:
        inputs = {'run_id': args.run_id}
    elif args.action == 'register':
        inputs = {
            'run_id': args.run_id,
            'client_id': args.client_id,
            'client_name': args.client_name,
            'data_silo_size': args.data_size,
            'data_features': ['sentiment', 'call_duration_minutes', 'response_time']
        }
    elif args.action == 'query':
        inputs = {'filters': {'dataset': args.dataset}}
    
    # Create and execute task
    task = create_fl_management_task(task_type_map[args.action], inputs)
    crew = create_fl_manager_crew()
    crew.tasks = [task]
    
    result = crew.kickoff()
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()

