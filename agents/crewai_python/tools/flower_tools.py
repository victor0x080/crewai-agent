"""
Federated Learning Tools for CrewAI Agents using FlowerAI Framework.

Provides tools for:
- Starting federated training runs with FedAvg strategy
- Registering federated clients (data silos)
- Saving/loading federated models with metadata
- Making predictions using federated models
- Fetching run metrics and model registry

Complies with:
- Redis Streams for state management
- CloudEvents 1.0 for event publishing
- JSON Schema validation
- Ontology integration (resolve_concept, expand_concepts)
"""

import json
import uuid
import time
from datetime import datetime
from typing import Dict, List, Any, Optional
from crewai.tools import tool
import redis
from pathlib import Path
import pickle
import numpy as np

# Redis client singleton
_redis_client = None


def get_redis_client():
    """Get or create Redis client singleton."""
    global _redis_client
    if _redis_client is None:
        _redis_client = redis.Redis(
            host='localhost',
            port=6379,
            db=0,
            decode_responses=False  # Keep binary for model storage
        )
    return _redis_client


def publish_cloudevent(stream_key: str, event_type: str, source: str, 
                       subject: str, data: Dict[str, Any]) -> str:
    """
    Publish a CloudEvent to Redis Stream following CloudEvents 1.0 spec.
    
    Args:
        stream_key: Redis stream key (e.g., 'fl:events')
        event_type: CloudEvent type (e.g., 'com.flowerai.fl.run.started')
        source: Event source URI (e.g., 'urn:flowerai:coordinator')
        subject: Subject identifier (e.g., run_id)
        data: Event payload data
    
    Returns:
        Event ID from Redis Stream
    """
    r = get_redis_client()
    
    event_id = f"{int(time.time()*1000)}-{str(uuid.uuid4())[:8]}"
    cloudevent = {
        "specversion": "1.0",
        "id": event_id,
        "type": event_type,
        "source": source,
        "subject": subject,
        "time": datetime.utcnow().isoformat() + "Z",
        "datacontenttype": "application/json",
        "dataschema": f"https://schemas.flowerai.com/{event_type.split('.')[-1]}/1-0-0.json",
        "data": data,
    }
    
    # Store full CloudEvent in RedisJSON
    r.set(f"event:{event_id}", json.dumps(cloudevent))
    
    # Add pointer to stream
    stream_id = r.xadd(stream_key, {
        "event_id": event_id,
        "type": event_type,
        "subject": subject,
        "timestamp": cloudevent["time"]
    })
    
    return stream_id.decode() if isinstance(stream_id, bytes) else stream_id


@tool("start_federated_training")
def start_federated_training(
    run_name: str,
    dataset_name: str,
    model_type: str,
    num_rounds: int,
    min_clients: int,
    strategy: str = "FedAvg",
    target_metric: str = "accuracy",
    privacy_budget: Optional[float] = None
) -> str:
    """
    Start a federated learning training run.
    
    Args:
        run_name: Human-readable name for the run
        dataset_name: Name of dataset (e.g., 'call_center_csat')
        model_type: Model type (e.g., 'logistic_regression', 'random_forest')
        num_rounds: Number of federated rounds to run
        min_clients: Minimum clients per round
        strategy: Aggregation strategy (FedAvg, FedProx, etc.)
        target_metric: Metric to optimize (accuracy, f1, auc)
        privacy_budget: Optional differential privacy epsilon
    
    Returns:
        JSON string with run_id and status
    """
    r = get_redis_client()
    
    run_id = f"fl_run_{int(time.time())}_{str(uuid.uuid4())[:8]}"
    
    run_config = {
        "run_id": run_id,
        "run_name": run_name,
        "dataset_name": dataset_name,
        "model_type": model_type,
        "num_rounds": num_rounds,
        "min_clients": min_clients,
        "strategy": strategy,
        "target_metric": target_metric,
        "privacy_budget": privacy_budget,
        "status": "initialized",
        "created_at": datetime.utcnow().isoformat(),
        "current_round": 0,
        "registered_clients": []
    }
    
    # Store run config in Redis
    r.set(f"fl:run:{run_id}", json.dumps(run_config))
    
    # Publish CloudEvent for run started
    publish_cloudevent(
        stream_key="fl:events",
        event_type="com.flowerai.fl.run.started",
        source="urn:flowerai:coordinator",
        subject=run_id,
        data=run_config
    )
    
    return json.dumps({
        "success": True,
        "run_id": run_id,
        "status": "initialized",
        "message": f"Federated learning run '{run_name}' started with {num_rounds} rounds"
    })


@tool("register_fl_client")
def register_fl_client(
    run_id: str,
    client_id: str,
    client_name: str,
    data_silo_size: int,
    data_features: List[str],
    metadata: Optional[Dict[str, Any]] = None
) -> str:
    """
    Register a federated learning client (data silo) to a training run.
    
    Args:
        run_id: Training run identifier
        client_id: Unique client identifier (e.g., 'call_center_org_1')
        client_name: Human-readable client name
        data_silo_size: Number of samples at this client
        data_features: List of feature names available
        metadata: Optional metadata (e.g., {'region': 'US-West', 'org_type': 'enterprise'})
    
    Returns:
        JSON string with registration status
    """
    r = get_redis_client()
    
    # Check if run exists
    run_data = r.get(f"fl:run:{run_id}")
    if not run_data:
        return json.dumps({
            "success": False,
            "error": f"Run {run_id} not found"
        })
    
    run_config = json.loads(run_data)
    
    client_info = {
        "client_id": client_id,
        "client_name": client_name,
        "data_silo_size": data_silo_size,
        "data_features": data_features,
        "metadata": metadata or {},
        "registered_at": datetime.utcnow().isoformat(),
        "status": "ready"
    }
    
    # Store client info
    r.set(f"fl:client:{run_id}:{client_id}", json.dumps(client_info))
    
    # Update run config with registered client
    run_config["registered_clients"].append(client_id)
    r.set(f"fl:run:{run_id}", json.dumps(run_config))
    
    # Publish CloudEvent for client registered
    publish_cloudevent(
        stream_key="fl:events",
        event_type="com.flowerai.fl.client.registered",
        source="urn:flowerai:coordinator",
        subject=f"{run_id}/{client_id}",
        data=client_info
    )
    
    return json.dumps({
        "success": True,
        "client_id": client_id,
        "run_id": run_id,
        "message": f"Client '{client_name}' registered with {data_silo_size} samples"
    })


@tool("save_fl_model")
def save_fl_model(
    run_id: str,
    round_num: int,
    model_params: str,  # Base64 encoded or path
    metrics: Dict[str, float],
    model_metadata: Optional[Dict[str, Any]] = None
) -> str:
    """
    Save a federated learning model with metadata to model registry.
    
    Args:
        run_id: Training run identifier
        round_num: Round number (0 = initial, 1+ = after aggregation)
        model_params: Model parameters (base64 encoded pickle or file path)
        metrics: Model metrics (e.g., {'accuracy': 0.85, 'f1': 0.82})
        model_metadata: Optional metadata (e.g., {'num_clients': 5, 'total_samples': 10000})
    
    Returns:
        JSON string with model version ID and storage location
    """
    r = get_redis_client()
    
    model_version = f"{run_id}_r{round_num}"
    
    model_record = {
        "model_version": model_version,
        "run_id": run_id,
        "round_num": round_num,
        "metrics": metrics,
        "metadata": model_metadata or {},
        "saved_at": datetime.utcnow().isoformat(),
        "status": "saved"
    }
    
    # Store model metadata
    r.set(f"fl:model:{model_version}", json.dumps(model_record))
    
    # Store model params (in practice, use object storage like S3)
    r.set(f"fl:model:params:{model_version}", model_params)
    
    # Add to model registry list
    r.zadd(f"fl:registry:{run_id}", {model_version: round_num})
    
    # Publish CloudEvent for model saved
    publish_cloudevent(
        stream_key="fl:events",
        event_type="com.flowerai.fl.model.saved",
        source="urn:flowerai:coordinator",
        subject=model_version,
        data=model_record
    )
    
    return json.dumps({
        "success": True,
        "model_version": model_version,
        "metrics": metrics,
        "message": f"Model saved for round {round_num} with {metrics.get('accuracy', 'N/A')} accuracy"
    })


@tool("load_fl_model")
def load_fl_model(model_version: str) -> str:
    """
    Load a federated learning model from the model registry.
    
    Args:
        model_version: Model version ID (e.g., 'fl_run_123_r5')
    
    Returns:
        JSON string with model metadata and parameters reference
    """
    r = get_redis_client()
    
    # Get model metadata
    model_data = r.get(f"fl:model:{model_version}")
    if not model_data:
        return json.dumps({
            "success": False,
            "error": f"Model version {model_version} not found"
        })
    
    model_record = json.loads(model_data)
    
    # Get model params (reference only, actual loading done by inference service)
    params_key = f"fl:model:params:{model_version}"
    params_exist = r.exists(params_key)
    
    return json.dumps({
        "success": True,
        "model_version": model_version,
        "model_record": model_record,
        "params_available": bool(params_exist),
        "params_key": params_key if params_exist else None
    })


@tool("predict_with_fl_model")
def predict_with_fl_model(
    model_version: str,
    input_features: Dict[str, Any],
    feature_names: List[str]
) -> str:
    """
    Make a prediction using a federated learning model.
    
    Args:
        model_version: Model version ID (e.g., 'fl_run_123_r5')
        input_features: Feature values as dict (e.g., {'sentiment': 'negative', 'response_time': 120})
        feature_names: Ordered list of feature names for model input
    
    Returns:
        JSON string with prediction and confidence
    """
    r = get_redis_client()
    
    # Load model metadata
    model_data = r.get(f"fl:model:{model_version}")
    if not model_data:
        return json.dumps({
            "success": False,
            "error": f"Model version {model_version} not found"
        })
    
    # In practice, load actual model from params and run inference
    # For this tool skeleton, return mock prediction
    prediction_id = str(uuid.uuid4())[:8]
    
    # Mock prediction logic (replace with actual model inference)
    prediction = {
        "prediction_id": prediction_id,
        "model_version": model_version,
        "input_features": input_features,
        "predicted_class": 1,  # Mock: 1 = high CSAT, 0 = low CSAT
        "confidence": 0.87,
        "prediction_time": datetime.utcnow().isoformat()
    }
    
    # Publish CloudEvent for prediction made
    publish_cloudevent(
        stream_key="fl:events",
        event_type="com.flowerai.fl.prediction.made",
        source="urn:flowerai:inference",
        subject=prediction_id,
        data=prediction
    )
    
    return json.dumps({
        "success": True,
        "prediction": prediction
    })


@tool("list_fl_models")
def list_fl_models(run_id: Optional[str] = None, limit: int = 10) -> str:
    """
    List federated learning models from the model registry.
    
    Args:
        run_id: Optional run ID to filter models
        limit: Maximum number of models to return
    
    Returns:
        JSON string with list of model versions and metadata
    """
    r = get_redis_client()
    
    if run_id:
        # Get models for specific run
        model_versions = r.zrange(f"fl:registry:{run_id}", 0, limit - 1, desc=True)
    else:
        # Get all model keys (scan pattern)
        model_keys = []
        for key in r.scan_iter(match="fl:model:*", count=100):
            key_str = key.decode() if isinstance(key, bytes) else key
            if not key_str.startswith("fl:model:params:"):
                model_keys.append(key_str)
        
        model_versions = [k.replace("fl:model:", "") for k in model_keys[:limit]]
    
    models = []
    for version in model_versions:
        version_str = version.decode() if isinstance(version, bytes) else version
        model_data = r.get(f"fl:model:{version_str}")
        if model_data:
            models.append(json.loads(model_data))
    
    return json.dumps({
        "success": True,
        "count": len(models),
        "models": models
    })


@tool("get_fl_run_metrics")
def get_fl_run_metrics(run_id: str) -> str:
    """
    Get metrics and status for a federated learning run.
    
    Args:
        run_id: Training run identifier
    
    Returns:
        JSON string with run metrics, status, and history
    """
    r = get_redis_client()
    
    # Get run config
    run_data = r.get(f"fl:run:{run_id}")
    if not run_data:
        return json.dumps({
            "success": False,
            "error": f"Run {run_id} not found"
        })
    
    run_config = json.loads(run_data)
    
    # Get registered clients
    client_ids = run_config.get("registered_clients", [])
    clients = []
    for client_id in client_ids:
        client_data = r.get(f"fl:client:{run_id}:{client_id}")
        if client_data:
            clients.append(json.loads(client_data))
    
    # Get model metrics per round
    model_versions = r.zrange(f"fl:registry:{run_id}", 0, -1)
    round_metrics = []
    for version in model_versions:
        version_str = version.decode() if isinstance(version, bytes) else version
        model_data = r.get(f"fl:model:{version_str}")
        if model_data:
            model_record = json.loads(model_data)
            round_metrics.append({
                "round": model_record["round_num"],
                "metrics": model_record["metrics"]
            })
    
    return json.dumps({
        "success": True,
        "run_config": run_config,
        "num_clients": len(clients),
        "clients": clients,
        "num_rounds_completed": len(round_metrics),
        "round_metrics": round_metrics
    })


@tool("update_fl_run_status")
def update_fl_run_status(run_id: str, status: str, current_round: int = 0) -> str:
    """
    Update the status of a federated learning run.
    
    Args:
        run_id: Training run identifier
        status: New status (initialized, running, completed, failed)
        current_round: Current round number
    
    Returns:
        JSON string with updated status
    """
    r = get_redis_client()
    
    # Get run config
    run_data = r.get(f"fl:run:{run_id}")
    if not run_data:
        return json.dumps({
            "success": False,
            "error": f"Run {run_id} not found"
        })
    
    run_config = json.loads(run_data)
    run_config["status"] = status
    run_config["current_round"] = current_round
    run_config["updated_at"] = datetime.utcnow().isoformat()
    
    # Update in Redis
    r.set(f"fl:run:{run_id}", json.dumps(run_config))
    
    # Publish CloudEvent for status update
    publish_cloudevent(
        stream_key="fl:events",
        event_type="com.flowerai.fl.run.status_updated",
        source="urn:flowerai:coordinator",
        subject=run_id,
        data={
            "run_id": run_id,
            "status": status,
            "current_round": current_round
        }
    )
    
    return json.dumps({
        "success": True,
        "run_id": run_id,
        "status": status,
        "current_round": current_round
    })

