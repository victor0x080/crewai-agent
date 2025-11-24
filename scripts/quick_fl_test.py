"""
Quick Federated Learning Test

Generates synthetic call center data, partitions it, and prepares for FL testing.
This script can run standalone without downloading external datasets.
"""

import sys
from pathlib import Path

# Add project paths
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root / 'agents' / 'crewai_python'))

from federated.dataset_partitioner import prepare_federated_datasets
import json

def main():
    print("=" * 80)
    print("Quick Federated Learning Test Setup")
    print("=" * 80)
    
    # Configuration
    num_clients = 4
    strategy = "iid"  # or "region", "channel", "temporal"
    output_dir = project_root / "data" / "federated" / "call_center" / "partitions" / strategy
    
    print(f"\nConfiguration:")
    print(f"  - Number of clients: {num_clients}")
    print(f"  - Partitioning strategy: {strategy}")
    print(f"  - Output directory: {output_dir}")
    
    # Generate and partition dataset
    print(f"\nGenerating synthetic call center dataset...")
    partitions, stats = prepare_federated_datasets(
        num_clients=num_clients,
        strategy=strategy,
        output_dir=output_dir,
        dataset_path=None  # Use synthetic data
    )
    
    print(f"\n✅ Dataset prepared successfully!")
    print(f"\nStatistics:")
    print(json.dumps(stats, indent=2))
    
    # Display partition details
    print(f"\n📊 Partition Details:")
    for i, partition_stat in enumerate(stats['partition_stats']):
        print(f"\nPartition {i}:")
        print(f"  - Samples: {partition_stat['num_samples']}")
        print(f"  - Features: {partition_stat['num_features']}")
        print(f"  - Sentiment: {partition_stat['sentiment_distribution']}")
        print(f"  - CSAT: {partition_stat['csat_distribution']}")
    
    # Test commands
    print(f"\n" + "=" * 80)
    print("Next Steps: Start Federated Learning")
    print("=" * 80)
    
    print(f"\n1. Start FL Server (Terminal 1):")
    print(f"   cd {project_root}/agents/crewai_python/federated")
    print(f"   python fl_server.py --run-id quick_test --num-rounds 3 --min-clients 2")
    
    print(f"\n2. Start FL Clients (Terminals 2-5):")
    for i in range(num_clients):
        print(f"   python fl_client.py --run-id quick_test --client-id client_{i} --client-name 'Client{i}' --partition-id {i}")
    
    print(f"\n3. Or use the Call Center FL Crew:")
    print(f"   cd {project_root}/agents/crewai_python/crews/federated")
    print(f"   python CallCenterFLCrew.py --run-name 'Quick Test' --num-rounds 3 --min-clients 2")
    
    print(f"\n✅ Setup complete! Dataset ready at: {output_dir}")


if __name__ == "__main__":
    main()

