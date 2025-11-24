"""
Dataset Partitioning Utilities for Federated Learning.

Provides utilities for:
- Partitioning call center dataset into multiple data silos
- IID (Independent and Identically Distributed) partitioning
- Non-IID partitioning (heterogeneous data distribution)
- Schema harmonization across silos
- Data quality validation

Complies with:
- Privacy constraints (no data sharing between silos)
- Redis Streams for metadata publishing
- CloudEvents 1.0 for events
"""

import json
import logging
from typing import Dict, List, Tuple, Optional
from pathlib import Path
from datetime import datetime
import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split

import sys
sys.path.append(str(Path(__file__).parent.parent))
from tools.flower_tools import publish_cloudevent, get_redis_client

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class CallCenterDatasetPartitioner:
    """
    Partition call center dataset into federated data silos.
    
    Supports multiple partitioning strategies:
    - IID: Random uniform distribution
    - Non-IID by region: Geographic clustering
    - Non-IID by channel: Communication channel clustering
    - Non-IID by time: Temporal clustering
    """
    
    def __init__(self, dataset_path: Optional[Path] = None, random_seed: int = 42):
        """
        Initialize dataset partitioner.
        
        Args:
            dataset_path: Optional path to call center CSV file
            random_seed: Random seed for reproducibility
        """
        self.dataset_path = dataset_path
        self.random_seed = random_seed
        self.redis_client = get_redis_client()
        
        np.random.seed(random_seed)
        
        # Load or generate dataset
        if dataset_path and dataset_path.exists():
            self.df = pd.read_csv(dataset_path)
            logger.info(f"Loaded dataset from {dataset_path}: {len(self.df)} samples")
        else:
            self.df = self._generate_synthetic_dataset()
            logger.info(f"Generated synthetic dataset: {len(self.df)} samples")
    
    def _generate_synthetic_dataset(self, n_samples: int = 10000) -> pd.DataFrame:
        """
        Generate synthetic call center dataset.
        
        Schema:
        - customer_name: str
        - sentiment: str (positive, neutral, negative)
        - csat_score: int (1-5)
        - call_timestamp: datetime
        - reason: str (billing, technical, sales, general)
        - city: str
        - state: str
        - channel: str (phone, chat, email, web)
        - response_time: int (seconds)
        - call_duration_minutes: float
        
        Returns:
            DataFrame with synthetic call center data
        """
        logger.info(f"Generating synthetic call center dataset with {n_samples} samples")
        
        # Define distributions
        sentiments = ["positive", "neutral", "negative"]
        sentiment_probs = [0.4, 0.35, 0.25]
        
        reasons = ["billing", "technical_support", "sales", "general_inquiry", "complaint"]
        reason_probs = [0.25, 0.30, 0.15, 0.20, 0.10]
        
        channels = ["phone", "chat", "email", "web"]
        channel_probs = [0.45, 0.25, 0.20, 0.10]
        
        states = ["CA", "TX", "NY", "FL", "IL", "PA", "OH", "GA", "NC", "MI"]
        state_probs = [0.15, 0.12, 0.10, 0.09, 0.08, 0.07, 0.06, 0.06, 0.05, 0.04]
        # Normalize to sum to 1.0
        state_probs = [p / sum(state_probs) for p in state_probs]
        
        cities = {
            "CA": ["Los Angeles", "San Francisco", "San Diego", "Sacramento"],
            "TX": ["Houston", "Dallas", "Austin", "San Antonio"],
            "NY": ["New York City", "Buffalo", "Rochester", "Albany"],
            "FL": ["Miami", "Orlando", "Tampa", "Jacksonville"],
            "IL": ["Chicago", "Springfield", "Peoria", "Rockford"],
            "PA": ["Philadelphia", "Pittsburgh", "Harrisburg", "Allentown"],
            "OH": ["Columbus", "Cleveland", "Cincinnati", "Toledo"],
            "GA": ["Atlanta", "Savannah", "Augusta", "Macon"],
            "NC": ["Charlotte", "Raleigh", "Greensboro", "Durham"],
            "MI": ["Detroit", "Grand Rapids", "Lansing", "Ann Arbor"]
        }
        
        # Generate data
        data = {
            "customer_name": [f"Customer_{i:05d}" for i in range(n_samples)],
            "sentiment": np.random.choice(sentiments, size=n_samples, p=sentiment_probs),
            "reason": np.random.choice(reasons, size=n_samples, p=reason_probs),
            "channel": np.random.choice(channels, size=n_samples, p=channel_probs),
            "state": np.random.choice(states, size=n_samples, p=state_probs),
            "response_time": np.random.exponential(scale=120, size=n_samples).astype(int),  # seconds
            "call_duration_minutes": np.random.gamma(shape=2, scale=5, size=n_samples),
        }
        
        # Add cities based on states
        data["city"] = [np.random.choice(cities[state]) for state in data["state"]]
        
        # Add timestamps (last 90 days)
        base_timestamp = pd.Timestamp.now() - pd.Timedelta(days=90)
        data["call_timestamp"] = [
            base_timestamp + pd.Timedelta(minutes=np.random.randint(0, 90*24*60))
            for _ in range(n_samples)
        ]
        
        df = pd.DataFrame(data)
        
        # Generate CSAT score based on features
        # Positive sentiment + fast response + short call = high CSAT
        csat_base = 3.0
        csat_base += (df["sentiment"] == "positive").astype(float) * 1.5
        csat_base -= (df["sentiment"] == "negative").astype(float) * 1.5
        csat_base += (df["response_time"] < 60).astype(float) * 0.5
        csat_base -= (df["response_time"] > 180).astype(float) * 0.5
        csat_base += (df["call_duration_minutes"] < 5).astype(float) * 0.5
        csat_base -= (df["call_duration_minutes"] > 15).astype(float) * 0.5
        
        # Add noise and clip to 1-5 range
        csat_noise = np.random.normal(0, 0.5, size=n_samples)
        df["csat_score"] = np.clip(csat_base + csat_noise, 1, 5).round().astype(int)
        
        return df
    
    def partition_iid(self, num_partitions: int) -> List[pd.DataFrame]:
        """
        Partition dataset into IID (random uniform) splits.
        
        Args:
            num_partitions: Number of data silos
            
        Returns:
            List of DataFrames, one per partition
        """
        logger.info(f"Partitioning dataset into {num_partitions} IID partitions")
        
        # Shuffle and split
        df_shuffled = self.df.sample(frac=1, random_state=self.random_seed).reset_index(drop=True)
        partition_size = len(df_shuffled) // num_partitions
        
        partitions = []
        for i in range(num_partitions):
            start_idx = i * partition_size
            end_idx = start_idx + partition_size if i < num_partitions - 1 else len(df_shuffled)
            partition = df_shuffled.iloc[start_idx:end_idx].copy()
            partitions.append(partition)
            
            logger.info(f"Partition {i}: {len(partition)} samples")
        
        self._publish_partition_metadata(partitions, strategy="iid")
        return partitions
    
    def partition_by_region(self, regions: Optional[Dict[str, List[str]]] = None) -> List[pd.DataFrame]:
        """
        Partition dataset by geographic region (non-IID).
        
        Args:
            regions: Dict mapping region names to list of states
            
        Returns:
            List of DataFrames, one per region
        """
        if regions is None:
            # Default regions
            regions = {
                "West": ["CA", "WA", "OR", "NV", "AZ"],
                "South": ["TX", "FL", "GA", "NC", "TN"],
                "Northeast": ["NY", "PA", "MA", "NJ", "CT"],
                "Midwest": ["IL", "OH", "MI", "IN", "WI"]
            }
        
        logger.info(f"Partitioning dataset into {len(regions)} regional partitions")
        
        partitions = []
        for region_name, states in regions.items():
            partition = self.df[self.df["state"].isin(states)].copy()
            partitions.append(partition)
            
            logger.info(f"Region {region_name}: {len(partition)} samples from states {states}")
        
        self._publish_partition_metadata(partitions, strategy="region", metadata=regions)
        return partitions
    
    def partition_by_channel(self) -> List[pd.DataFrame]:
        """
        Partition dataset by communication channel (non-IID).
        
        Returns:
            List of DataFrames, one per channel
        """
        channels = self.df["channel"].unique()
        logger.info(f"Partitioning dataset into {len(channels)} channel partitions")
        
        partitions = []
        for channel in channels:
            partition = self.df[self.df["channel"] == channel].copy()
            partitions.append(partition)
            
            logger.info(f"Channel {channel}: {len(partition)} samples")
        
        self._publish_partition_metadata(partitions, strategy="channel")
        return partitions
    
    def partition_by_time(self, num_partitions: int) -> List[pd.DataFrame]:
        """
        Partition dataset by time period (non-IID, for temporal drift simulation).
        
        Args:
            num_partitions: Number of time-based partitions
            
        Returns:
            List of DataFrames, one per time period
        """
        logger.info(f"Partitioning dataset into {num_partitions} temporal partitions")
        
        # Sort by timestamp
        df_sorted = self.df.sort_values("call_timestamp").reset_index(drop=True)
        partition_size = len(df_sorted) // num_partitions
        
        partitions = []
        for i in range(num_partitions):
            start_idx = i * partition_size
            end_idx = start_idx + partition_size if i < num_partitions - 1 else len(df_sorted)
            partition = df_sorted.iloc[start_idx:end_idx].copy()
            partitions.append(partition)
            
            time_range = f"{partition['call_timestamp'].min()} to {partition['call_timestamp'].max()}"
            logger.info(f"Partition {i}: {len(partition)} samples, time range: {time_range}")
        
        self._publish_partition_metadata(partitions, strategy="temporal")
        return partitions
    
    def _publish_partition_metadata(
        self,
        partitions: List[pd.DataFrame],
        strategy: str,
        metadata: Optional[Dict] = None
    ):
        """Publish partition metadata to Redis Streams (optional)."""
        partition_metadata = {
            "num_partitions": len(partitions),
            "strategy": strategy,
            "total_samples": sum(len(p) for p in partitions),
            "partition_sizes": [len(p) for p in partitions],
            "metadata": metadata or {},
            "timestamp": datetime.utcnow().isoformat()
        }
        
        try:
            publish_cloudevent(
                stream_key="fl:events",
                event_type="com.flowerai.fl.dataset.partitioned",
                source="urn:flowerai:dataset_partitioner",
                subject=f"partition_{strategy}",
                data=partition_metadata
            )
            logger.info("Published partition metadata to Redis")
        except Exception as e:
            logger.warning(f"Could not publish to Redis (optional): {e}")
    
    def save_partitions(
        self,
        partitions: List[pd.DataFrame],
        output_dir: Path,
        prefix: str = "partition"
    ) -> List[Path]:
        """
        Save partitions to separate CSV files.
        
        Args:
            partitions: List of partition DataFrames
            output_dir: Output directory
            prefix: Filename prefix
            
        Returns:
            List of output file paths
        """
        output_dir.mkdir(parents=True, exist_ok=True)
        
        output_paths = []
        for i, partition in enumerate(partitions):
            output_path = output_dir / f"{prefix}_{i}.csv"
            partition.to_csv(output_path, index=False)
            output_paths.append(output_path)
            
            logger.info(f"Saved partition {i} to {output_path}")
        
        return output_paths
    
    def get_partition_statistics(self, partitions: List[pd.DataFrame]) -> Dict:
        """
        Compute statistics for each partition.
        
        Args:
            partitions: List of partition DataFrames
            
        Returns:
            Dict with partition statistics
        """
        stats = {
            "num_partitions": len(partitions),
            "partition_stats": []
        }
        
        for i, partition in enumerate(partitions):
            partition_stats = {
                "partition_id": i,
                "num_samples": len(partition),
                "num_features": len(partition.columns),
                "feature_names": list(partition.columns),
                "sentiment_distribution": partition["sentiment"].value_counts().to_dict(),
                "channel_distribution": partition["channel"].value_counts().to_dict(),
                "csat_distribution": partition["csat_score"].value_counts().to_dict(),
                "avg_response_time": float(partition["response_time"].mean()),
                "avg_call_duration": float(partition["call_duration_minutes"].mean()),
                "date_range": {
                    "start": partition["call_timestamp"].min().isoformat(),
                    "end": partition["call_timestamp"].max().isoformat()
                }
            }
            stats["partition_stats"].append(partition_stats)
        
        return stats


def prepare_federated_datasets(
    num_clients: int = 4,
    strategy: str = "iid",
    output_dir: Optional[Path] = None,
    dataset_path: Optional[Path] = None
) -> Tuple[List[pd.DataFrame], Dict]:
    """
    Prepare federated datasets for multiple clients.
    
    Args:
        num_clients: Number of data silos
        strategy: Partitioning strategy ('iid', 'region', 'channel', 'temporal')
        output_dir: Optional directory to save partitions
        dataset_path: Optional path to existing dataset
        
    Returns:
        Tuple of (partitions, statistics)
    """
    partitioner = CallCenterDatasetPartitioner(dataset_path=dataset_path)
    
    # Partition based on strategy
    if strategy == "iid":
        partitions = partitioner.partition_iid(num_clients)
    elif strategy == "region":
        partitions = partitioner.partition_by_region()
    elif strategy == "channel":
        partitions = partitioner.partition_by_channel()
    elif strategy == "temporal":
        partitions = partitioner.partition_by_time(num_clients)
    else:
        raise ValueError(f"Unknown strategy: {strategy}")
    
    # Get statistics
    stats = partitioner.get_partition_statistics(partitions)
    
    # Save if output_dir provided
    if output_dir:
        partitioner.save_partitions(partitions, Path(output_dir))
    
    return partitions, stats


def main():
    """CLI entry point for dataset partitioning."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Partition Call Center Dataset for Federated Learning")
    parser.add_argument("--num-clients", type=int, default=4, help="Number of data silos")
    parser.add_argument(
        "--strategy",
        type=str,
        choices=["iid", "region", "channel", "temporal"],
        default="iid",
        help="Partitioning strategy"
    )
    parser.add_argument("--output-dir", type=str, help="Output directory for partitions")
    parser.add_argument("--dataset-path", type=str, help="Path to existing dataset CSV")
    
    args = parser.parse_args()
    
    partitions, stats = prepare_federated_datasets(
        num_clients=args.num_clients,
        strategy=args.strategy,
        output_dir=Path(args.output_dir) if args.output_dir else None,
        dataset_path=Path(args.dataset_path) if args.dataset_path else None
    )
    
    print(json.dumps(stats, indent=2))


if __name__ == "__main__":
    main()

