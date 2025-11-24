"""
Federated Learning Server Base Class using FlowerAI Framework.

Implements a Flower FL server with:
- FedAvg aggregation strategy
- Redis Streams integration for metrics and state
- CloudEvents publishing for observability
- Model versioning and registry integration
- Privacy-preserving aggregation (optional DP)

Complies with:
- Redis Streams for event publishing
- CloudEvents 1.0 for all events
- JSON Schema validation
- Ontology integration
"""

import json
import time
import logging
from typing import Dict, List, Optional, Tuple, Union
from datetime import datetime
from pathlib import Path

import flwr as fl
from flwr.common import (
    Parameters,
    Scalar,
    FitRes,
    EvaluateRes,
    parameters_to_ndarrays,
    ndarrays_to_parameters,
)
from flwr.server.strategy import FedAvg
from flwr.server import ServerConfig, start_server
import numpy as np
import redis

# Import our FL tools for Redis/CloudEvents integration
import sys
sys.path.append(str(Path(__file__).parent.parent))
from tools.flower_tools import publish_cloudevent, get_redis_client

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class FederatedLearningServer:
    """
    Federated Learning Server with Redis integration and CloudEvents publishing.
    
    Features:
    - FedAvg strategy with customizable aggregation
    - Model versioning with metrics tracking
    - Redis Streams for event publishing
    - Privacy budget enforcement (optional differential privacy)
    - Model registry integration
    - Real-time metrics publishing
    """
    
    def __init__(
        self,
        run_id: str,
        num_rounds: int,
        min_fit_clients: int,
        min_available_clients: int,
        min_evaluate_clients: int = 2,
        fraction_fit: float = 0.8,
        fraction_evaluate: float = 0.8,
        privacy_budget: Optional[float] = None,
        server_address: str = "0.0.0.0:8080"
    ):
        """
        Initialize Federated Learning Server.
        
        Args:
            run_id: Unique identifier for this FL run
            num_rounds: Number of federated rounds to execute
            min_fit_clients: Minimum clients for training
            min_available_clients: Minimum clients that must be available
            min_evaluate_clients: Minimum clients for evaluation
            fraction_fit: Fraction of clients used for training each round
            fraction_evaluate: Fraction of clients used for evaluation
            privacy_budget: Optional epsilon for differential privacy
            server_address: Server address to bind to
        """
        self.run_id = run_id
        self.num_rounds = num_rounds
        self.min_fit_clients = min_fit_clients
        self.min_available_clients = min_available_clients
        self.min_evaluate_clients = min_evaluate_clients
        self.fraction_fit = fraction_fit
        self.fraction_evaluate = fraction_evaluate
        self.privacy_budget = privacy_budget
        self.server_address = server_address
        
        self.redis_client = get_redis_client()
        self.current_round = 0
        self.metrics_history = []
        
        logger.info(f"Initialized FL Server for run {run_id}")
        
        # Publish server initialized event
        self._publish_event(
            event_type="com.flowerai.fl.server.initialized",
            data={
                "run_id": run_id,
                "num_rounds": num_rounds,
                "min_fit_clients": min_fit_clients,
                "privacy_budget": privacy_budget,
                "server_address": server_address
            }
        )
    
    def _publish_event(self, event_type: str, data: Dict) -> str:
        """Publish CloudEvent to Redis Stream."""
        return publish_cloudevent(
            stream_key="fl:events",
            event_type=event_type,
            source="urn:flowerai:server",
            subject=self.run_id,
            data=data
        )
    
    def _store_metrics(self, round_num: int, metrics: Dict[str, float]):
        """Store round metrics in Redis with timestamp."""
        metrics_record = {
            "run_id": self.run_id,
            "round": round_num,
            "metrics": metrics,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        # Store in Redis
        self.redis_client.set(
            f"fl:metrics:{self.run_id}:round:{round_num}",
            json.dumps(metrics_record)
        )
        
        # Add to sorted set for time-series queries
        self.redis_client.zadd(
            f"fl:metrics:timeline:{self.run_id}",
            {json.dumps(metrics_record): time.time()}
        )
        
        self.metrics_history.append(metrics_record)
        
        # Publish metrics event
        self._publish_event(
            event_type="com.flowerai.fl.round.metrics",
            data=metrics_record
        )
    
    def _save_model(self, round_num: int, parameters: Parameters, metrics: Dict[str, float]):
        """Save aggregated model to registry."""
        model_version = f"{self.run_id}_r{round_num}"
        
        # Convert parameters to numpy arrays and serialize
        arrays = parameters_to_ndarrays(parameters)
        params_bytes = json.dumps([arr.tolist() for arr in arrays])
        
        # Store in Redis
        self.redis_client.set(f"fl:model:params:{model_version}", params_bytes)
        
        model_record = {
            "model_version": model_version,
            "run_id": self.run_id,
            "round_num": round_num,
            "metrics": metrics,
            "num_parameters": len(arrays),
            "parameter_shapes": [arr.shape for arr in arrays],
            "saved_at": datetime.utcnow().isoformat()
        }
        
        self.redis_client.set(f"fl:model:{model_version}", json.dumps(model_record))
        self.redis_client.zadd(f"fl:registry:{self.run_id}", {model_version: round_num})
        
        logger.info(f"Saved model {model_version} with metrics: {metrics}")
        
        # Publish model saved event
        self._publish_event(
            event_type="com.flowerai.fl.model.saved",
            data=model_record
        )
        
        return model_version
    
    def create_strategy(self) -> FedAvg:
        """
        Create FedAvg aggregation strategy with custom callbacks.
        
        Returns:
            FedAvg strategy instance
        """
        
        def fit_config_fn(server_round: int) -> Dict[str, Scalar]:
            """Return training configuration for each round."""
            config = {
                "server_round": server_round,
                "local_epochs": 2,
                "batch_size": 32,
                "learning_rate": 0.01,
            }
            
            # Add privacy budget if configured
            if self.privacy_budget:
                config["privacy_epsilon"] = self.privacy_budget / self.num_rounds
            
            return config
        
        def evaluate_config_fn(server_round: int) -> Dict[str, Scalar]:
            """Return evaluation configuration for each round."""
            return {
                "server_round": server_round,
                "val_steps": 10,
            }
        
        def evaluate_metrics_aggregation_fn(
            metrics: List[Tuple[int, Dict[str, Scalar]]]
        ) -> Dict[str, Scalar]:
            """Aggregate evaluation metrics from all clients."""
            # Weighted average of metrics
            total_samples = sum(num_examples for num_examples, _ in metrics)
            
            aggregated = {}
            for num_examples, client_metrics in metrics:
                weight = num_examples / total_samples
                for key, value in client_metrics.items():
                    if key not in aggregated:
                        aggregated[key] = 0.0
                    aggregated[key] += weight * value
            
            return aggregated
        
        strategy = FedAvg(
            fraction_fit=self.fraction_fit,
            fraction_evaluate=self.fraction_evaluate,
            min_fit_clients=self.min_fit_clients,
            min_evaluate_clients=self.min_evaluate_clients,
            min_available_clients=self.min_available_clients,
            fit_metrics_aggregation_fn=None,  # Use default
            evaluate_metrics_aggregation_fn=evaluate_metrics_aggregation_fn,
            on_fit_config_fn=fit_config_fn,
            on_evaluate_config_fn=evaluate_config_fn,
        )
        
        logger.info("Created FedAvg strategy")
        return strategy
    
    def on_round_begin(self, server_round: int):
        """Callback at the beginning of each round."""
        self.current_round = server_round
        
        logger.info(f"Starting round {server_round}/{self.num_rounds}")
        
        # Update run status in Redis
        run_data = self.redis_client.get(f"fl:run:{self.run_id}")
        if run_data:
            run_config = json.loads(run_data)
            run_config["status"] = "running"
            run_config["current_round"] = server_round
            run_config["updated_at"] = datetime.utcnow().isoformat()
            self.redis_client.set(f"fl:run:{self.run_id}", json.dumps(run_config))
        
        # Publish round started event
        self._publish_event(
            event_type="com.flowerai.fl.round.started",
            data={
                "run_id": self.run_id,
                "round": server_round,
                "total_rounds": self.num_rounds
            }
        )
    
    def on_round_end(self, server_round: int, results: Optional[List[Tuple[fl.server.client_proxy.ClientProxy, FitRes]]]):
        """Callback at the end of each round."""
        logger.info(f"Completed round {server_round}/{self.num_rounds}")
        
        if results:
            num_clients = len(results)
            total_samples = sum(fit_res.num_examples for _, fit_res in results)
            
            # Extract metrics from results
            metrics = {
                "num_clients": num_clients,
                "total_samples": total_samples,
                "avg_samples_per_client": total_samples / num_clients if num_clients > 0 else 0
            }
            
            # Aggregate client metrics if available
            if results[0][1].metrics:
                aggregated_metrics = {}
                for _, fit_res in results:
                    for key, value in fit_res.metrics.items():
                        if key not in aggregated_metrics:
                            aggregated_metrics[key] = []
                        aggregated_metrics[key].append(value)
                
                for key, values in aggregated_metrics.items():
                    metrics[f"avg_{key}"] = sum(values) / len(values)
            
            # Store metrics
            self._store_metrics(server_round, metrics)
            
            logger.info(f"Round {server_round} metrics: {metrics}")
        
        # Publish round completed event
        self._publish_event(
            event_type="com.flowerai.fl.round.completed",
            data={
                "run_id": self.run_id,
                "round": server_round,
                "num_clients": len(results) if results else 0
            }
        )
    
    def start(self, initial_parameters: Optional[Parameters] = None):
        """
        Start the federated learning server.
        
        Args:
            initial_parameters: Optional initial model parameters
        """
        logger.info(f"Starting FL server for run {self.run_id} on {self.server_address}")
        
        # Create strategy
        strategy = self.create_strategy()
        
        # Configure server
        config = ServerConfig(num_rounds=self.num_rounds)
        
        # Update run status
        run_data = self.redis_client.get(f"fl:run:{self.run_id}")
        if run_data:
            run_config = json.loads(run_data)
            run_config["status"] = "running"
            run_config["started_at"] = datetime.utcnow().isoformat()
            self.redis_client.set(f"fl:run:{self.run_id}", json.dumps(run_config))
        
        # Publish server started event
        self._publish_event(
            event_type="com.flowerai.fl.server.started",
            data={
                "run_id": self.run_id,
                "server_address": self.server_address,
                "num_rounds": self.num_rounds
            }
        )
        
        try:
            # Start Flower server
            hist = start_server(
                server_address=self.server_address,
                config=config,
                strategy=strategy,
            )
            
            # Server completed successfully
            logger.info(f"FL server completed for run {self.run_id}")
            
            # Update run status
            if run_data:
                run_config = json.loads(run_data)
                run_config["status"] = "completed"
                run_config["completed_at"] = datetime.utcnow().isoformat()
                self.redis_client.set(f"fl:run:{self.run_id}", json.dumps(run_config))
            
            # Publish server completed event
            self._publish_event(
                event_type="com.flowerai.fl.server.completed",
                data={
                    "run_id": self.run_id,
                    "total_rounds": self.num_rounds,
                    "final_metrics": self.metrics_history[-1] if self.metrics_history else {}
                }
            )
            
            return hist
            
        except Exception as e:
            logger.error(f"FL server failed: {e}")
            
            # Update run status to failed
            if run_data:
                run_config = json.loads(run_data)
                run_config["status"] = "failed"
                run_config["error"] = str(e)
                run_config["failed_at"] = datetime.utcnow().isoformat()
                self.redis_client.set(f"fl:run:{self.run_id}", json.dumps(run_config))
            
            # Publish server failed event
            self._publish_event(
                event_type="com.flowerai.fl.server.failed",
                data={
                    "run_id": self.run_id,
                    "error": str(e),
                    "round": self.current_round
                }
            )
            
            raise


def main():
    """
    CLI entrypoint for starting FL server.
    
    Usage:
        python fl_server.py --run-id fl_run_123 --num-rounds 10 --min-clients 3
    """
    import argparse
    
    parser = argparse.ArgumentParser(description="Start Federated Learning Server")
    parser.add_argument("--run-id", type=str, required=True, help="FL run identifier")
    parser.add_argument("--num-rounds", type=int, default=5, help="Number of FL rounds")
    parser.add_argument("--min-clients", type=int, default=2, help="Minimum clients per round")
    parser.add_argument("--min-available", type=int, default=2, help="Minimum available clients")
    parser.add_argument("--privacy-budget", type=float, default=None, help="Differential privacy epsilon")
    parser.add_argument("--server-address", type=str, default="0.0.0.0:8080", help="Server address")
    
    args = parser.parse_args()
    
    # Create and start server
    server = FederatedLearningServer(
        run_id=args.run_id,
        num_rounds=args.num_rounds,
        min_fit_clients=args.min_clients,
        min_available_clients=args.min_available,
        privacy_budget=args.privacy_budget,
        server_address=args.server_address
    )
    
    server.start()


if __name__ == "__main__":
    main()

