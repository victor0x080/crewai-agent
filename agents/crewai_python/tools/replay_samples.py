"""
Sample Event Replay Tool
Replays sample CloudEvents from adapter samples/ folders for testing
"""
import json
import sys
import os
from redis_streams_tools import RedisStreamsClient


def replay_sample_event(sample_file_path: str):
    """
    Replay sample CloudEvent from adapter samples/
    
    Args:
        sample_file_path: Path to sample JSON file
    """
    if not os.path.exists(sample_file_path):
        print(f"Error: File not found: {sample_file_path}")
        sys.exit(1)
    
    # Load sample event
    with open(sample_file_path, 'r') as f:
        event = json.load(f)
    
    print(f"Loaded sample event: {event['id']}")
    print(f"  Type: {event['type']}")
    print(f"  Operation: {event['data'].get('operation')}")
    print(f"  Subject: {event.get('subject')}")
    
    # Get Redis client
    r = RedisStreamsClient().get_client()
    
    # Store full event in RedisJSON
    event_id = event['id']
    r.json().set(f"event:{event_id}", "$", event)
    print(f"  Stored in RedisJSON: event:{event_id}")
    
    # Add pointer to stream
    stream_key = 'stream:mco:event:action'
    r.xadd(stream_key, {
        'event_id': event_id,
        'type': event['type'],
        'subject': event.get('subject', ''),
        'dataschema': event.get('dataschema', '')
    })
    print(f"  Published to stream: {stream_key}")
    print(f"\n✅ Event replayed successfully!")
    print(f"\nTo consume this event, run:")
    print(f"  python runners/adapter_runners.py sa360")


def replay_all_samples(adapter_name: str):
    """
    Replay all sample events for an adapter
    
    Args:
        adapter_name: Adapter name (e.g., 'sa360')
    """
    # Find adapter samples directory
    base_path = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
    samples_dir = os.path.join(base_path, '..', 'Adapters', f'adapter-{adapter_name}', 'samples')
    
    if not os.path.exists(samples_dir):
        print(f"Error: Samples directory not found: {samples_dir}")
        sys.exit(1)
    
    # Find all action_*.json files
    sample_files = [
        f for f in os.listdir(samples_dir)
        if f.startswith('action_') and f.endswith('.json')
    ]
    
    if not sample_files:
        print(f"No sample files found in {samples_dir}")
        sys.exit(1)
    
    print(f"Found {len(sample_files)} sample events for {adapter_name}:")
    for sample_file in sample_files:
        print(f"  - {sample_file}")
    
    print(f"\nReplaying all samples...")
    for sample_file in sample_files:
        sample_path = os.path.join(samples_dir, sample_file)
        print(f"\n--- Replaying {sample_file} ---")
        replay_sample_event(sample_path)


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python replay_samples.py <sample_file_path>")
        print("  python replay_samples.py --adapter <adapter_name>")
        print("\nExamples:")
        print("  python replay_samples.py ../../Adapters/adapter-sa360/samples/action_setCampaignBudget.json")
        print("  python replay_samples.py --adapter sa360")
        sys.exit(1)
    
    if sys.argv[1] == '--adapter':
        if len(sys.argv) < 3:
            print("Error: Adapter name required")
            sys.exit(1)
        replay_all_samples(sys.argv[2])
    else:
        replay_sample_event(sys.argv[1])
