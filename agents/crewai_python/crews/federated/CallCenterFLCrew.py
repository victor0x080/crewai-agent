"""
Call Center Federated Learning Crew using FlowerAI Framework.

Hierarchical crew structure:
- Manager: FL Coordinator (orchestrates federated rounds, aggregation)
- Workers: 4 specialist workers (preprocessing, training, evaluation, deployment)

Complies with:
- CrewAI hierarchical process pattern
- Redis Streams for communication
- CloudEvents 1.0 for all events
- JSON Schema validation
- Ontology integration
- Manager has tools, workers have none (pure transformation)
"""

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent.parent))

from crewai import Agent, Task, Crew, Process
from crewai.tools import tool
import json
from typing import Dict, List, Optional

# Import FL tools and Redis tools
from tools.flower_tools import (
    start_federated_training,
    register_fl_client,
    save_fl_model,
    load_fl_model,
    get_fl_run_metrics,
    update_fl_run_status,
    list_fl_models
)
from tools.redis_streams_tools import redis_publish, redis_ack, redis_xreadgroup
from tools.schema_registry_tools import fetch_schema, validate_against_schema


# ============================================================================
# Manager: FL Coordinator Agent
# ============================================================================

fl_coordinator_manager = Agent(
    role="Federated Learning Coordinator",
    goal=(
        "Orchestrate federated learning training runs across multiple data silos "
        "for call center CSAT prediction while ensuring privacy preservation, "
        "model quality, and compliance with governance policies."
    ),
    backstory=(
        "Expert in federated learning orchestration with deep understanding of "
        "privacy-preserving machine learning, distributed systems, and model lifecycle "
        "management. Coordinates training across multiple call center organizations "
        "without sharing raw customer data, ensuring GDPR/CCPA compliance. "
        "Monitors convergence, aggregates models using FedAvg strategy, and manages "
        "model registry with versioning and rollback capabilities."
    ),
    tools=[
        # Federated Learning tools
        start_federated_training,
        register_fl_client,
        save_fl_model,
        load_fl_model,
        get_fl_run_metrics,
        update_fl_run_status,
        list_fl_models,
        # Redis Streams tools
        redis_publish,
        redis_ack,
        redis_xreadgroup,
        # Schema validation tools
        fetch_schema,
        validate_against_schema
    ],
    allow_delegation=True,  # Manager can delegate to workers
    verbose=True
)


# ============================================================================
# Worker 1: Data Preprocessing Specialist
# ============================================================================

data_preprocessing_worker = Agent(
    role="Federated Data Preprocessing Specialist",
    goal=(
        "Prepare call center data silos for federated learning by performing "
        "local preprocessing, feature engineering, and data quality checks "
        "without exposing raw data."
    ),
    backstory=(
        "Data engineering specialist focused on privacy-preserving data preparation. "
        "Expert in feature extraction from call center transcripts, sentiment analysis, "
        "time-series feature engineering (call duration, response time patterns), "
        "and data harmonization across heterogeneous call center systems. "
        "Ensures all preprocessing happens locally at each data silo, generating "
        "only aggregated statistics for schema validation."
    ),
    tools=[],  # Workers have no tools (pure transformation)
    allow_delegation=False,
    verbose=True
)


# ============================================================================
# Worker 2: Local Model Training Specialist
# ============================================================================

local_training_worker = Agent(
    role="Local Federated Training Specialist",
    goal=(
        "Execute local model training at each call center data silo using "
        "scikit-learn models (Logistic Regression, Random Forest) on private data, "
        "then share only model updates (gradients/parameters) with coordinator."
    ),
    backstory=(
        "Machine learning engineer specialized in federated learning client implementations. "
        "Expert in training classification models for CSAT prediction using tabular features "
        "(sentiment, call duration, response time, channel, reason). "
        "Implements differential privacy techniques when required, ensuring epsilon budget "
        "compliance. Handles model serialization, parameter extraction, and secure upload "
        "of model updates to aggregation server."
    ),
    tools=[],  # Workers have no tools
    allow_delegation=False,
    verbose=True
)


# ============================================================================
# Worker 3: Model Evaluation & Monitoring Specialist
# ============================================================================

evaluation_monitoring_worker = Agent(
    role="Federated Model Evaluation Specialist",
    goal=(
        "Evaluate federated models on local validation sets, compute performance "
        "metrics (accuracy, F1, AUC, fairness), and detect model drift or degradation."
    ),
    backstory=(
        "ML evaluation expert focused on model quality and fairness in federated settings. "
        "Performs local evaluation on each client's validation set, computes metrics "
        "including accuracy, precision, recall, F1, AUC-ROC, and fairness metrics across "
        "demographic groups (if available). Monitors for catastrophic forgetting, data drift, "
        "and concept drift. Aggregates evaluation results across silos while preserving "
        "privacy (no individual predictions shared)."
    ),
    tools=[],  # Workers have no tools
    allow_delegation=False,
    verbose=True
)


# ============================================================================
# Worker 4: Model Deployment & Inference Specialist
# ============================================================================

deployment_inference_worker = Agent(
    role="Federated Model Deployment Specialist",
    goal=(
        "Deploy aggregated federated models to inference endpoints, manage model "
        "versioning, and provide real-time CSAT predictions for incoming call center data."
    ),
    backstory=(
        "MLOps engineer specialized in federated model serving and deployment. "
        "Expert in model registry management, A/B testing, canary deployments, and "
        "rollback strategies. Deploys aggregated models to REST APIs for real-time "
        "CSAT prediction, batch scoring endpoints for historical analysis, and "
        "federated evaluation endpoints for continual learning. Monitors inference "
        "latency, throughput, and model performance in production."
    ),
    tools=[],  # Workers have no tools
    allow_delegation=False,
    verbose=True
)


# ============================================================================
# Tasks
# ============================================================================

def create_fl_training_task(
    run_name: str,
    dataset_name: str,
    num_rounds: int,
    min_clients: int,
    target_metric: str = "accuracy"
) -> Task:
    """Create task for starting federated training run."""
    return Task(
        description=(
            f"Start a federated learning training run named '{run_name}' for "
            f"call center CSAT prediction using dataset '{dataset_name}'. "
            f"Execute {num_rounds} federated rounds with minimum {min_clients} clients per round. "
            f"Target metric: {target_metric}. "
            f"\n\n"
            f"Steps:\n"
            f"1. Initialize FL run with configuration\n"
            f"2. Register all available call center data silos as clients\n"
            f"3. Start FL server and coordinate training rounds\n"
            f"4. Monitor convergence and model quality\n"
            f"5. Save final aggregated model to registry\n"
            f"6. Publish training completion event to Redis Streams"
        ),
        expected_output=(
            f"JSON object with run_id, final model version, metrics per round, "
            f"and deployment recommendations."
        ),
        agent=fl_coordinator_manager
    )


def create_data_preprocessing_task(client_configs: List[Dict]) -> Task:
    """Create task for preprocessing data at each client."""
    return Task(
        description=(
            f"Preprocess call center data at {len(client_configs)} client data silos. "
            f"For each client:\n"
            f"1. Load raw call center data (customer_name, sentiment, csat_score, "
            f"call_timestamp, reason, city, state, channel, response_time, call_duration_minutes)\n"
            f"2. Perform feature engineering:\n"
            f"   - Encode sentiment (positive=2, neutral=1, negative=0)\n"
            f"   - Extract time-based features (hour, day_of_week)\n"
            f"   - Normalize continuous features (response_time, call_duration)\n"
            f"   - One-hot encode categorical features (channel, reason, state)\n"
            f"3. Create binary CSAT target (high=1 if csat_score >= 4, else 0)\n"
            f"4. Split into train/test (80/20) locally\n"
            f"5. Generate data quality report (no raw data, only aggregates)\n"
            f"6. Validate schema compatibility across clients"
        ),
        expected_output=(
            f"JSON object with preprocessing results per client: "
            f"num_samples, num_features, feature_names, class_balance, "
            f"missing_values_pct, schema_version"
        ),
        agent=data_preprocessing_worker
    )


def create_local_training_task(run_id: str, round_num: int) -> Task:
    """Create task for local training at each client."""
    return Task(
        description=(
            f"Execute local training for FL run {run_id}, round {round_num}. "
            f"For each registered client:\n"
            f"1. Receive global model parameters from coordinator\n"
            f"2. Initialize local model with global parameters\n"
            f"3. Train model on local private data for 2 epochs\n"
            f"4. Compute local training metrics (accuracy, loss)\n"
            f"5. Extract updated model parameters (coef, intercept)\n"
            f"6. Send model updates to coordinator (no raw data)\n"
            f"7. Apply differential privacy if configured (epsilon budget)\n"
            f"8. Publish training completion event per client"
        ),
        expected_output=(
            f"JSON object with training results per client: "
            f"client_id, num_examples, train_accuracy, train_loss, "
            f"model_params_hash, privacy_epsilon_used"
        ),
        agent=local_training_worker
    )


def create_evaluation_task(run_id: str, model_version: str) -> Task:
    """Create task for evaluating aggregated model."""
    return Task(
        description=(
            f"Evaluate aggregated model {model_version} for run {run_id}. "
            f"For each client:\n"
            f"1. Load aggregated global model from coordinator\n"
            f"2. Evaluate on local validation set\n"
            f"3. Compute metrics: accuracy, precision, recall, F1, AUC-ROC\n"
            f"4. Check fairness metrics if demographic data available\n"
            f"5. Detect data drift using population stability index (PSI)\n"
            f"6. Compare with previous round's performance\n"
            f"7. Send evaluation results to coordinator (aggregated only)\n"
            f"8. Publish evaluation completion event"
        ),
        expected_output=(
            f"JSON object with evaluation results per client and aggregated: "
            f"weighted_accuracy, weighted_f1, weighted_auc, "
            f"performance_degradation_pct, drift_detected (bool)"
        ),
        agent=evaluation_monitoring_worker
    )


def create_deployment_task(model_version: str, deployment_strategy: str) -> Task:
    """Create task for deploying trained model."""
    return Task(
        description=(
            f"Deploy federated model {model_version} using '{deployment_strategy}' strategy. "
            f"Steps:\n"
            f"1. Load aggregated model from registry\n"
            f"2. Run final validation tests (schema, performance thresholds)\n"
            f"3. Deploy to inference endpoints:\n"
            f"   - REST API: /api/fl/predict (real-time CSAT prediction)\n"
            f"   - Batch API: /api/fl/batch-score (bulk scoring)\n"
            f"4. Set up monitoring: latency, throughput, error rate, model drift\n"
            f"5. Configure A/B testing if canary deployment\n"
            f"6. Update model registry with deployment metadata\n"
            f"7. Publish model deployment event to Redis Streams\n"
            f"8. Generate deployment documentation"
        ),
        expected_output=(
            f"JSON object with deployment details: "
            f"model_version, deployment_url, strategy, health_check_status, "
            f"monitoring_dashboard_url, rollback_plan"
        ),
        agent=deployment_inference_worker
    )


# ============================================================================
# Crew Definition
# ============================================================================

call_center_fl_crew = Crew(
    agents=[
        fl_coordinator_manager,
        data_preprocessing_worker,
        local_training_worker,
        evaluation_monitoring_worker,
        deployment_inference_worker
    ],
    tasks=[],  # Tasks added dynamically based on workflow
    process=Process.hierarchical,
    manager_llm="gpt-4",  # Manager uses GPT-4 for orchestration
    verbose=True
)


# ============================================================================
# Workflow Functions
# ============================================================================

def execute_fl_training_workflow(
    run_name: str,
    dataset_name: str = "call_center_csat",
    num_rounds: int = 5,
    min_clients: int = 3,
    client_configs: Optional[List[Dict]] = None
) -> Dict:
    """
    Execute complete federated learning training workflow.
    
    Args:
        run_name: Human-readable name for the run
        dataset_name: Dataset identifier
        num_rounds: Number of federated rounds
        min_clients: Minimum clients per round
        client_configs: List of client configurations
        
    Returns:
        Workflow results with run_id, model_version, metrics
    """
    if client_configs is None:
        # Default: 4 call center organizations
        client_configs = [
            {"client_id": "call_center_org_1", "client_name": "Call Center East", "partition_id": 0},
            {"client_id": "call_center_org_2", "client_name": "Call Center West", "partition_id": 1},
            {"client_id": "call_center_org_3", "client_name": "Call Center North", "partition_id": 2},
            {"client_id": "call_center_org_4", "client_name": "Call Center South", "partition_id": 3}
        ]
    
    # Create task sequence
    tasks = [
        create_data_preprocessing_task(client_configs),
        create_fl_training_task(run_name, dataset_name, num_rounds, min_clients),
    ]
    
    # Add evaluation and deployment tasks for final model
    tasks.append(create_evaluation_task("{run_id}", "{model_version}"))
    tasks.append(create_deployment_task("{model_version}", "blue_green"))
    
    # Update crew tasks
    call_center_fl_crew.tasks = tasks
    
    # Execute crew
    result = call_center_fl_crew.kickoff()
    
    return result


# ============================================================================
# Main Entry Point
# ============================================================================

def main():
    """CLI entry point for Call Center FL Crew."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Call Center Federated Learning Crew")
    parser.add_argument("--run-name", type=str, required=True, help="FL run name")
    parser.add_argument("--num-rounds", type=int, default=5, help="Number of FL rounds")
    parser.add_argument("--min-clients", type=int, default=3, help="Minimum clients per round")
    
    args = parser.parse_args()
    
    result = execute_fl_training_workflow(
        run_name=args.run_name,
        num_rounds=args.num_rounds,
        min_clients=args.min_clients
    )
    
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()

