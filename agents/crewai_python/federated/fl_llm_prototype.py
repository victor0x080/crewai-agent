"""
Federated LLM Prototype
=======================

Prototype implementation of federated LLM fine-tuning using FlowerAI + PEFT.

This demonstrates how to integrate LLM federation into Quest Agent Forge:
- Uses LoRA for parameter-efficient fine-tuning
- Aggregates adapters across clients
- Publishes to RAG for discoverability
- Follows CloudEvents pattern

Based on FlowerAI's FlowerTune LLM example:
https://flower.ai/docs/examples/flowertune-llm.html
"""

from typing import Dict, List, Any, Optional
import torch
from transformers import (
    AutoModelForCausalLM,
    AutoTokenizer,
    TrainingArguments,
    Trainer
)
from peft import (
    LoraConfig,
    get_peft_model,
    PeftModel,
    TaskType
)
from datasets import load_dataset
import flwr as fl
from flwr.common import Parameters, Scalar
import numpy as np
import json
from datetime import datetime
from pathlib import Path

# Import existing FL tools
import sys
sys.path.append(str(Path(__file__).parent.parent))
from tools.redis_streams_tools import publish_cloudevent
from tools.fl_rag_integration import publish_fl_model_to_rag


# ===================================================================
# CONFIGURATION
# ===================================================================

class FLLLMConfig:
    """Configuration for federated LLM training."""
    
    # Model configuration
    BASE_MODEL = "gpt2"  # Start with small model for testing
    # BASE_MODEL = "meta-llama/Llama-2-7b-hf"  # Production
    # BASE_MODEL = "microsoft/phi-2"  # Alternative
    
    # LoRA configuration
    LORA_R = 16  # LoRA rank
    LORA_ALPHA = 32  # LoRA alpha
    LORA_DROPOUT = 0.05
    TARGET_MODULES = ["c_attn"]  # GPT-2 attention layers
    # TARGET_MODULES = ["q_proj", "v_proj"]  # For Llama
    
    # Training configuration
    NUM_ROUNDS = 3
    MIN_CLIENTS = 2
    BATCH_SIZE = 4
    GRADIENT_ACCUMULATION_STEPS = 4
    LEARNING_RATE = 2e-4
    NUM_EPOCHS = 1
    
    # Dataset configuration
    DATASET_NAME = "tatsu-lab/alpaca"  # Instruction tuning dataset
    MAX_LENGTH = 512


# ===================================================================
# FL LLM SERVER
# ===================================================================

class FederatedLLMServer:
    """
    Federated LLM Server using FlowerAI.
    
    Aggregates LoRA adapters from multiple clients using FedAvg.
    """
    
    def __init__(
        self,
        run_id: str,
        base_model: str = FLLLMConfig.BASE_MODEL,
        num_rounds: int = FLLLMConfig.NUM_ROUNDS,
        min_clients: int = FLLLMConfig.MIN_CLIENTS
    ):
        self.run_id = run_id
        self.base_model = base_model
        self.num_rounds = num_rounds
        self.min_clients = min_clients
        
        print(f"Initializing FL LLM Server for run: {run_id}")
        print(f"Base model: {base_model}")
        print(f"Rounds: {num_rounds}, Min clients: {min_clients}")
    
    def create_strategy(self) -> fl.server.strategy.Strategy:
        """Create FedAvg strategy for adapter aggregation."""
        
        def on_fit_config_fn(server_round: int) -> Dict[str, Scalar]:
            """Configure training for each round."""
            return {
                "server_round": server_round,
                "local_epochs": FLLLMConfig.NUM_EPOCHS,
                "learning_rate": FLLLMConfig.LEARNING_RATE
            }
        
        def on_evaluate_config_fn(server_round: int) -> Dict[str, Scalar]:
            """Configure evaluation for each round."""
            return {"server_round": server_round}
        
        strategy = fl.server.strategy.FedAvg(
            fraction_fit=1.0,
            fraction_evaluate=1.0,
            min_fit_clients=self.min_clients,
            min_evaluate_clients=self.min_clients,
            min_available_clients=self.min_clients,
            on_fit_config_fn=on_fit_config_fn,
            on_evaluate_config_fn=on_evaluate_config_fn
        )
        
        return strategy
    
    def start(self):
        """Start FL LLM server."""
        
        # Publish start event
        publish_cloudevent(
            stream_key='fl:events',
            event_type='com.flowerai.llm.server.started',
            source='urn:flowerai:llm_server',
            subject=self.run_id,
            data={
                'run_id': self.run_id,
                'base_model': self.base_model,
                'num_rounds': self.num_rounds,
                '@context': {
                    '@vocab': 'https://ontology.flowerai.com/llm#'
                }
            }
        )
        
        # Start Flower server
        strategy = self.create_strategy()
        
        fl.server.start_server(
            server_address="0.0.0.0:8080",
            config=fl.server.ServerConfig(num_rounds=self.num_rounds),
            strategy=strategy
        )
        
        # Publish completion event
        publish_cloudevent(
            stream_key='fl:events',
            event_type='com.flowerai.llm.server.completed',
            source='urn:flowerai:llm_server',
            subject=self.run_id,
            data={
                'run_id': self.run_id,
                'status': 'completed',
                '@context': {
                    '@vocab': 'https://ontology.flowerai.com/llm#'
                }
            }
        )


# ===================================================================
# FL LLM CLIENT
# ===================================================================

class FederatedLLMClient(fl.client.NumPyClient):
    """
    Federated LLM Client using FlowerAI + PEFT.
    
    Fine-tunes LoRA adapters on local private data.
    """
    
    def __init__(
        self,
        run_id: str,
        client_id: str,
        base_model: str = FLLLMConfig.BASE_MODEL,
        local_dataset: Optional[Any] = None
    ):
        self.run_id = run_id
        self.client_id = client_id
        self.base_model = base_model
        
        print(f"Initializing FL LLM Client: {client_id}")
        
        # Load base model
        self.model = AutoModelForCausalLM.from_pretrained(
            base_model,
            torch_dtype=torch.float16 if torch.cuda.is_available() else torch.float32,
            device_map="auto" if torch.cuda.is_available() else None
        )
        
        # Load tokenizer
        self.tokenizer = AutoTokenizer.from_pretrained(base_model)
        self.tokenizer.pad_token = self.tokenizer.eos_token
        
        # Configure LoRA
        lora_config = LoraConfig(
            r=FLLLMConfig.LORA_R,
            lora_alpha=FLLLMConfig.LORA_ALPHA,
            target_modules=FLLLMConfig.TARGET_MODULES,
            lora_dropout=FLLLMConfig.LORA_DROPOUT,
            bias="none",
            task_type=TaskType.CAUSAL_LM
        )
        
        # Add LoRA adapters
        self.model = get_peft_model(self.model, lora_config)
        self.model.print_trainable_parameters()
        
        # Load dataset
        self.dataset = local_dataset or self._load_default_dataset()
        
        print(f"Client {client_id} initialized with {len(self.dataset)} samples")
    
    def _load_default_dataset(self):
        """Load default instruction tuning dataset."""
        dataset = load_dataset(FLLLMConfig.DATASET_NAME, split="train[:1000]")
        
        def format_instruction(example):
            """Format as instruction-response pair."""
            if example.get('input'):
                text = f"### Instruction:\n{example['instruction']}\n\n### Input:\n{example['input']}\n\n### Response:\n{example['output']}"
            else:
                text = f"### Instruction:\n{example['instruction']}\n\n### Response:\n{example['output']}"
            
            return {"text": text}
        
        dataset = dataset.map(format_instruction)
        return dataset
    
    def get_parameters(self, config: Dict[str, Scalar]) -> Parameters:
        """Get LoRA adapter parameters."""
        # Only return LoRA parameters (not full model)
        lora_state_dict = {
            k: v.cpu().numpy()
            for k, v in self.model.state_dict().items()
            if "lora" in k
        }
        
        return fl.common.ndarrays_to_parameters(
            [v for v in lora_state_dict.values()]
        )
    
    def set_parameters(self, parameters: Parameters) -> None:
        """Set LoRA adapter parameters from server."""
        params_dict = zip(
            [k for k in self.model.state_dict().keys() if "lora" in k],
            fl.common.parameters_to_ndarrays(parameters)
        )
        
        state_dict = {k: torch.from_numpy(v) for k, v in params_dict}
        self.model.load_state_dict(state_dict, strict=False)
    
    def fit(
        self,
        parameters: Parameters,
        config: Dict[str, Scalar]
    ) -> tuple:
        """Fine-tune LoRA adapter on local data."""
        
        print(f"Client {self.client_id}: Starting local training")
        
        # Set global parameters
        self.set_parameters(parameters)
        
        # Training arguments
        training_args = TrainingArguments(
            output_dir=f"./fl_llm_output/{self.client_id}",
            per_device_train_batch_size=FLLLMConfig.BATCH_SIZE,
            gradient_accumulation_steps=FLLLMConfig.GRADIENT_ACCUMULATION_STEPS,
            num_train_epochs=config.get("local_epochs", FLLLMConfig.NUM_EPOCHS),
            learning_rate=config.get("learning_rate", FLLLMConfig.LEARNING_RATE),
            fp16=torch.cuda.is_available(),
            logging_steps=10,
            save_strategy="no",
            report_to="none"
        )
        
        # Tokenize dataset
        def tokenize_function(examples):
            return self.tokenizer(
                examples["text"],
                truncation=True,
                max_length=FLLLMConfig.MAX_LENGTH,
                padding="max_length"
            )
        
        tokenized_dataset = self.dataset.map(
            tokenize_function,
            batched=True,
            remove_columns=self.dataset.column_names
        )
        
        # Create trainer
        trainer = Trainer(
            model=self.model,
            args=training_args,
            train_dataset=tokenized_dataset
        )
        
        # Train
        trainer.train()
        
        # Get updated parameters
        updated_parameters = self.get_parameters({})
        
        # Metrics
        metrics = {
            "num_samples": len(self.dataset),
            "loss": trainer.state.log_history[-1].get("loss", 0.0)
        }
        
        print(f"Client {self.client_id}: Training complete")
        
        # Publish training event
        publish_cloudevent(
            stream_key='fl:events',
            event_type='com.flowerai.llm.client.training_completed',
            source=f'urn:flowerai:llm_client:{self.client_id}',
            subject=f"{self.run_id}/{self.client_id}",
            data={
                'run_id': self.run_id,
                'client_id': self.client_id,
                'metrics': metrics,
                '@context': {
                    '@vocab': 'https://ontology.flowerai.com/llm#'
                }
            }
        )
        
        return updated_parameters, len(self.dataset), metrics
    
    def evaluate(
        self,
        parameters: Parameters,
        config: Dict[str, Scalar]
    ) -> tuple:
        """Evaluate LoRA adapter on local validation data."""
        
        # Set parameters
        self.set_parameters(parameters)
        
        # Simple perplexity evaluation
        # In production, use proper validation set
        loss = 0.0  # Placeholder
        
        metrics = {
            "loss": loss,
            "perplexity": np.exp(loss) if loss > 0 else 0.0
        }
        
        return loss, len(self.dataset), metrics


# ===================================================================
# HELPER FUNCTIONS
# ===================================================================

def publish_llm_adapter_to_rag(
    run_id: str,
    adapter_version: str,
    base_model: str,
    metrics: Dict[str, float],
    lora_config: Dict[str, Any]
) -> Dict[str, Any]:
    """Publish LLM adapter to RAG for discoverability."""
    
    return publish_fl_model_to_rag(
        model_version=adapter_version,
        run_id=run_id,
        metrics=metrics,
        model_metadata={
            'base_model': base_model,
            'adapter_type': 'LoRA',
            'lora_rank': lora_config.get('r'),
            'lora_alpha': lora_config.get('lora_alpha'),
            'target_modules': lora_config.get('target_modules'),
            'model_type': 'llm_adapter'
        },
        training_summary=f"""
Federated LLM Adapter: {adapter_version}

Base Model: {base_model}
Adapter Type: LoRA (Low-Rank Adaptation)
Configuration:
- Rank: {lora_config.get('r')}
- Alpha: {lora_config.get('lora_alpha')}
- Target Modules: {', '.join(lora_config.get('target_modules', []))}

This adapter was trained using federated learning across multiple organizations
without sharing raw text data. Only adapter weights were aggregated.

Performance:
- Loss: {metrics.get('loss', 'N/A')}
- Perplexity: {metrics.get('perplexity', 'N/A')}

Use Cases:
- Domain-specific text generation
- Instruction following
- Privacy-preserving LLM fine-tuning
        """.strip()
    )


# ===================================================================
# CLI ENTRYPOINTS
# ===================================================================

def start_llm_server():
    """Start FL LLM server."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Start Federated LLM Server")
    parser.add_argument("--run-id", type=str, required=True)
    parser.add_argument("--base-model", type=str, default=FLLLMConfig.BASE_MODEL)
    parser.add_argument("--num-rounds", type=int, default=FLLLMConfig.NUM_ROUNDS)
    parser.add_argument("--min-clients", type=int, default=FLLLMConfig.MIN_CLIENTS)
    
    args = parser.parse_args()
    
    server = FederatedLLMServer(
        run_id=args.run_id,
        base_model=args.base_model,
        num_rounds=args.num_rounds,
        min_clients=args.min_clients
    )
    
    server.start()


def start_llm_client():
    """Start FL LLM client."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Start Federated LLM Client")
    parser.add_argument("--run-id", type=str, required=True)
    parser.add_argument("--client-id", type=str, required=True)
    parser.add_argument("--base-model", type=str, default=FLLLMConfig.BASE_MODEL)
    parser.add_argument("--server-address", type=str, default="localhost:8080")
    
    args = parser.parse_args()
    
    client = FederatedLLMClient(
        run_id=args.run_id,
        client_id=args.client_id,
        base_model=args.base_model
    )
    
    fl.client.start_numpy_client(
        server_address=args.server_address,
        client=client
    )


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "server":
        sys.argv.pop(1)
        start_llm_server()
    elif len(sys.argv) > 1 and sys.argv[1] == "client":
        sys.argv.pop(1)
        start_llm_client()
    else:
        print("Usage:")
        print("  python fl_llm_prototype.py server --run-id <run_id>")
        print("  python fl_llm_prototype.py client --run-id <run_id> --client-id <client_id>")

