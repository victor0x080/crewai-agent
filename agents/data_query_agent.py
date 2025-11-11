"""
Data Query Agent
Queries datasets and returns results via event bus.
Follows: Redis Streams + CloudEvents + CrewAI + Ontology pattern
"""

import redis
import json
import uuid
import pandas as pd
import os
import requests
from datetime import datetime
from typing import Dict, Any, List, Optional
from crewai import Agent, Task, Crew
from crewai.tools import tool
import time

# Redis connection
redis_client = redis.Redis(host='localhost', port=6379, decode_responses=True)

# RedisJSON fallback helpers (for Redis without JSON module)
def redis_set_json(key: str, value: dict):
    """Set JSON value in Redis, with fallback if RedisJSON not available"""
    try:
        redis_client.json().set(key, "$", value)
    except redis.ResponseError as e:
        if "unknown command" in str(e).lower() or "json.set" in str(e).lower():
            # Fallback to regular SET with JSON string
            redis_client.set(key, json.dumps(value))
        else:
            raise

def redis_get_json(key: str) -> Optional[dict]:
    """Get JSON value from Redis, with fallback if RedisJSON not available"""
    try:
        return redis_client.json().get(key)
    except redis.ResponseError as e:
        if "unknown command" in str(e).lower() or "json.get" in str(e).lower():
            # Fallback to regular GET with JSON parse
            value = redis_client.get(key)
            return json.loads(value) if value else None
        else:
            raise

# Heartbeat functionality
def send_heartbeat(agent_id: str):
    """Send heartbeat to Node.js backend"""
    try:
        api_url = os.getenv('API_URL', 'http://localhost:3001')
        requests.post(
            f"{api_url}/api/managers/{agent_id}/heartbeat",
            timeout=2
        )
    except Exception:
        pass  # Silently fail - heartbeat is not critical

# Heartbeat tracking
last_heartbeat = 0
heartbeat_interval = 30  # Send heartbeat every 30 seconds

# Ontology service
class OntologyService:
    """Ontology concept resolution for data queries"""
    
    @staticmethod
    def resolve_concept(term: str) -> str:
        """Resolve data term to canonical URI"""
        concept_map = {
            'sales': 'https://schema.org/salesRevenue',
            'revenue': 'https://schema.org/revenue',
            'customer': 'https://schema.org/Customer',
            'product': 'https://schema.org/Product',
            'order': 'https://schema.org/Order',
            'sku': 'https://vocab.acme.com/product/SKU',
            'campaign': 'https://vocab.acme.com/marketing/Campaign',
            'transaction': 'https://vocab.acme.com/commerce/Transaction'
        }
        return concept_map.get(term.lower(), f'https://vocab.acme.com/{term}')
    
    @staticmethod
    def map_enum(field: str, value: str) -> str:
        """Map enum values to ontology URIs"""
        enum_map = {
            'status': {
                'active': 'https://vocab.acme.com/status/Active',
                'completed': 'https://vocab.acme.com/status/Completed',
                'pending': 'https://vocab.acme.com/status/Pending'
            },
            'region': {
                'north': 'https://vocab.acme.com/geography/NorthRegion',
                'south': 'https://vocab.acme.com/geography/SouthRegion',
                'east': 'https://vocab.acme.com/geography/EastRegion',
                'west': 'https://vocab.acme.com/geography/WestRegion'
            }
        }
        return enum_map.get(field.lower(), {}).get(value.lower(), value)

ontology = OntologyService()

# Simulated Datasets (replace with actual DB connections)
DATASETS = {
    'sales_transactions': pd.DataFrame({
        'transaction_id': ['TXN-001', 'TXN-002', 'TXN-003', 'TXN-004', 'TXN-005'],
        'date': ['2024-10-15', '2024-10-16', '2024-10-17', '2024-10-18', '2024-10-19'],
        'customer_id': ['CUST-101', 'CUST-102', 'CUST-101', 'CUST-103', 'CUST-104'],
        'product_sku': ['SKU-A001', 'SKU-B002', 'SKU-A001', 'SKU-C003', 'SKU-B002'],
        'quantity': [2, 1, 3, 1, 2],
        'unit_price': [49.99, 89.99, 49.99, 129.99, 89.99],
        'total_amount': [99.98, 89.99, 149.97, 129.99, 179.98],
        'region': ['north', 'south', 'north', 'east', 'west'],
        'status': ['completed', 'completed', 'completed', 'pending', 'completed']
    }),
    
    'customer_profiles': pd.DataFrame({
        'customer_id': ['CUST-101', 'CUST-102', 'CUST-103', 'CUST-104'],
        'name': ['Alice Johnson', 'Bob Smith', 'Carol Davis', 'David Lee'],
        'segment': ['premium', 'standard', 'premium', 'standard'],
        'lifetime_value': [2500.00, 850.00, 3200.00, 1100.00],
        'join_date': ['2023-01-15', '2023-06-20', '2022-11-10', '2024-03-05'],
        'region': ['north', 'south', 'east', 'west']
    }),
    
    'campaign_performance': pd.DataFrame({
        'campaign_id': ['CAMP-Q4-001', 'CAMP-Q4-002', 'CAMP-Q4-003'],
        'campaign_name': ['Holiday Sale', 'Black Friday', 'Cyber Monday'],
        'start_date': ['2024-11-01', '2024-11-24', '2024-12-01'],
        'budget': [50000, 75000, 60000],
        'revenue': [125000, 210000, 165000],
        'customers_acquired': [450, 780, 620],
        'roi': [2.5, 2.8, 2.75]
    })
}

# LangChain Tools
@tool("query_dataset")
def query_dataset(dataset_name: str, filters: str = "", aggregation: str = "") -> str:
    """
    Query a dataset with optional filters and aggregations.
    
    Args:
        dataset_name: Name of dataset (sales_transactions, customer_profiles, campaign_performance)
        filters: JSON string with filter conditions, e.g., {"region": "north", "status": "completed"}
        aggregation: Aggregation to perform, e.g., "sum:total_amount", "avg:unit_price", "count"
    
    Returns:
        JSON string with query results
    """
    try:
        print(f"[DataQueryAgent] Querying dataset: {dataset_name}")
        print(f"[DataQueryAgent] Filters: {filters}")
        print(f"[DataQueryAgent] Aggregation: {aggregation}")
        
        # Get dataset
        if dataset_name not in DATASETS:
            return json.dumps({
                "error": f"Dataset '{dataset_name}' not found",
                "available_datasets": list(DATASETS.keys())
            })
        
        df = DATASETS[dataset_name].copy()
        
        # Apply filters
        if filters:
            try:
                filter_dict = json.loads(filters) if isinstance(filters, str) else filters
                for field, value in filter_dict.items():
                    if field in df.columns:
                        # Map enum values via ontology
                        if field in ['status', 'region']:
                            mapped_value = ontology.map_enum(field, str(value))
                            print(f"[DataQueryAgent] Mapped {field}={value} to {mapped_value}")
                        df = df[df[field] == value]
            except Exception as e:
                print(f"[DataQueryAgent] Filter error: {e}")
        
        # Apply aggregation
        result_data = {}
        if aggregation:
            parts = aggregation.split(":")
            agg_func = parts[0]
            
            if agg_func == "count":
                result_data = {"count": len(df)}
            elif len(parts) == 2:
                field = parts[1]
                if field in df.columns:
                    if agg_func == "sum":
                        result_data = {f"sum_{field}": float(df[field].sum())}
                    elif agg_func == "avg":
                        result_data = {f"avg_{field}": float(df[field].mean())}
                    elif agg_func == "max":
                        result_data = {f"max_{field}": float(df[field].max())}
                    elif agg_func == "min":
                        result_data = {f"min_{field}": float(df[field].min())}
        else:
            # Return rows as JSON
            result_data = {
                "rows": df.to_dict('records'),
                "count": len(df)
            }
        
        # Add ontology context
        result_data["@context"] = {
            "@vocab": "https://vocab.acme.com/",
            "dataset": ontology.resolve_concept(dataset_name.split('_')[0])
        }
        
        return json.dumps(result_data, indent=2, default=str)
        
    except Exception as e:
        print(f"[DataQueryAgent] Query error: {e}")
        return json.dumps({"error": str(e)})

@tool("get_dataset_schema")
def get_dataset_schema(dataset_name: str) -> str:
    """Get schema information for a dataset."""
    try:
        if dataset_name not in DATASETS:
            return json.dumps({
                "error": f"Dataset '{dataset_name}' not found",
                "available_datasets": list(DATASETS.keys())
            })
        
        df = DATASETS[dataset_name]
        schema = {
            "dataset": dataset_name,
            "columns": [
                {
                    "name": col,
                    "type": str(df[col].dtype),
                    "ontology_uri": ontology.resolve_concept(col.split('_')[0])
                }
                for col in df.columns
            ],
            "row_count": len(df),
            "sample": df.head(2).to_dict('records')
        }
        
        return json.dumps(schema, indent=2, default=str)
        
    except Exception as e:
        return json.dumps({"error": str(e)})

@tool("analyze_dataset")
def analyze_dataset(dataset_name: str, analysis_type: str = "summary") -> str:
    """
    Perform analysis on dataset.
    
    Args:
        dataset_name: Name of dataset
        analysis_type: Type of analysis (summary, trends, distribution)
    
    Returns:
        JSON with analysis results
    """
    try:
        if dataset_name not in DATASETS:
            return json.dumps({"error": f"Dataset '{dataset_name}' not found"})
        
        df = DATASETS[dataset_name]
        
        if analysis_type == "summary":
            numeric_cols = df.select_dtypes(include=['number']).columns
            summary = {
                "row_count": len(df),
                "column_count": len(df.columns),
                "numeric_summary": {
                    col: {
                        "mean": float(df[col].mean()),
                        "median": float(df[col].median()),
                        "std": float(df[col].std()),
                        "min": float(df[col].min()),
                        "max": float(df[col].max())
                    }
                    for col in numeric_cols
                }
            }
            return json.dumps(summary, indent=2, default=str)
        
        elif analysis_type == "trends":
            # Simple trend analysis
            if 'date' in df.columns and any('amount' in col or 'revenue' in col for col in df.columns):
                value_col = next((col for col in df.columns if 'amount' in col or 'revenue' in col), None)
                if value_col:
                    df_sorted = df.sort_values('date')
                    trend = {
                        "trend_direction": "increasing" if df_sorted[value_col].iloc[-1] > df_sorted[value_col].iloc[0] else "decreasing",
                        "first_value": float(df_sorted[value_col].iloc[0]),
                        "last_value": float(df_sorted[value_col].iloc[-1]),
                        "total": float(df_sorted[value_col].sum())
                    }
                    return json.dumps(trend, indent=2)
        
        return json.dumps({"analysis_type": analysis_type, "status": "completed"})
        
    except Exception as e:
        return json.dumps({"error": str(e)})

# CrewAI Agent Definition
data_query_agent = Agent(
    role="Data Query Specialist",
    goal="Query datasets, perform analysis, and return accurate results with ontology context",
    backstory="""You are an expert data analyst with deep knowledge of SQL, pandas, and 
    data warehousing. You understand business metrics, customer analytics, and sales data. 
    You can query multiple datasets, apply filters and aggregations, and provide insights 
    with proper ontology context. You always validate data quality and provide clear, 
    actionable results.""",
    tools=[query_dataset, get_dataset_schema, analyze_dataset],
    allow_delegation=False,
    verbose=True
)

# CloudEvents Builder
def build_cloudevent(event_type: str, source: str, subject: str, data: Dict[str, Any]) -> Dict[str, Any]:
    """Build CloudEvents 1.0 compliant event"""
    event_id = str(uuid.uuid4())
    return {
        "specversion": "1.0",
        "id": event_id,
        "source": source,
        "type": event_type,
        "subject": subject,
        "time": datetime.utcnow().isoformat() + "Z",
        "datacontenttype": "application/json",
        "dataschema": "https://schemas.acme.com/agents/data-query-response/1-0-0.json",
        "data": {
            "@context": {
                "@vocab": "https://vocab.acme.com/",
                "sales": "https://schema.org/salesRevenue",
                "customer": "https://schema.org/Customer"
            },
            **data
        }
    }

# Event Bus Publisher
def publish_to_event_bus(event: Dict[str, Any], stream_key: str = "stream:agents:data-query:responses:v1"):
    """Publish CloudEvent to Redis Stream"""
    try:
        # Store full event in RedisJSON
        redis_set_json(f"event:{event['id']}", event)
        
        # Add pointer to stream
        redis_client.xadd(stream_key, {
            "event_id": event["id"],
            "type": event["type"],
            "subject": event["subject"],
            "dataschema": event["dataschema"]
        })
        
        print(f"[DataQueryAgent] Published event {event['id']} to {stream_key}")
        return True
    except Exception as e:
        print(f"[DataQueryAgent] Error publishing event: {e}")
        return False

# Main Agent Execution Loop
def run_data_query_agent():
    """
    Consume query requests from Redis Stream, execute with CrewAI agent, publish results
    """
    input_stream = "stream:agents:data-query:requests:v1"
    output_stream = "stream:agents:data-query:responses:v1"
    consumer_group = "data-query-agents"
    consumer_name = f"data-query-{uuid.uuid4().hex[:8]}"
    
    print(f"[DataQueryAgent] Starting consumer: {consumer_name}")
    
    # Create consumer group
    try:
        redis_client.xgroup_create(input_stream, consumer_group, id="$", mkstream=True)
        print(f"[DataQueryAgent] Created consumer group: {consumer_group}")
    except redis.ResponseError as e:
        if "BUSYGROUP" not in str(e):
            raise
        print(f"[DataQueryAgent] Consumer group already exists")
    
    # Main processing loop
    while True:
        try:
            # Send heartbeat periodically
            global last_heartbeat
            if time.time() - last_heartbeat > heartbeat_interval:
                send_heartbeat("data-query-agent")
                last_heartbeat = time.time()
            
            # Read from stream (blocking)
            messages = redis_client.xreadgroup(
                consumer_group,
                consumer_name,
                {input_stream: ">"},
                count=1,
                block=5000
            )
            
            if not messages:
                continue
            
            for stream, entries in messages:
                for message_id, fields in entries:
                    print(f"[DataQueryAgent] Processing message: {message_id}")
                    
                    # Fetch full event from RedisJSON
                    event_id = fields.get("event_id")
                    if not event_id:
                        redis_client.xack(input_stream, consumer_group, message_id)
                        continue
                    
                    source_event = redis_get_json(f"event:{event_id}")
                    if not source_event:
                        redis_client.xack(input_stream, consumer_group, message_id)
                        continue
                    
                    # Extract query parameters
                    data = source_event.get("data", {})
                    dataset_name = data.get("dataset", "")
                    query_text = data.get("query", "")
                    filters = data.get("filters", {})
                    aggregation = data.get("aggregation", "")
                    
                    print(f"[DataQueryAgent] Dataset: {dataset_name}, Query: {query_text}")
                    
                    # Create CrewAI task
                    task = Task(
                        description=f"""Execute this data query: "{query_text}"
                        
                        Dataset: {dataset_name}
                        Filters: {json.dumps(filters)}
                        Aggregation: {aggregation}
                        
                        Steps:
                        1. Understand the business question
                        2. Query the appropriate dataset with filters
                        3. Apply any required aggregations or analysis
                        4. Validate results for data quality
                        5. Add ontology context to results
                        
                        Return JSON with:
                        - query_result: The actual data/aggregation
                        - row_count: Number of rows returned
                        - insights: Key insights from the data
                        - ontology_context: Mapped concepts
                        """,
                        expected_output="JSON response with query results and insights",
                        agent=data_query_agent
                    )
                    
                    # Execute agent
                    crew = Crew(
                        agents=[data_query_agent],
                        tasks=[task],
                        verbose=True
                    )
                    
                    result = crew.kickoff()
                    
                    # Build response CloudEvent
                    response_event = build_cloudevent(
                        event_type="com.acme.agents.data-query.completed",
                        source="urn:agent:data-query",
                        subject=dataset_name or "dataset",
                        data={
                            "query": query_text,
                            "dataset": dataset_name,
                            "result": str(result),
                            "correlation_id": event_id,
                            "filters_applied": filters,
                            "ontology_concepts": [
                                ontology.resolve_concept(term)
                                for term in dataset_name.split('_')
                            ]
                        }
                    )
                    
                    # Publish response
                    publish_to_event_bus(response_event, output_stream)
                    
                    # ACK message
                    redis_client.xack(input_stream, consumer_group, message_id)
                    print(f"[DataQueryAgent] Completed message: {message_id}")
                    
        except Exception as e:
            print(f"[DataQueryAgent] Error in main loop: {e}")
            time.sleep(5)

# Agent Registration
AGENT_REGISTRY_ENTRY = {
    "id": "data-query-agent",
    "name": "Data Query Agent",
    "type": "data_retrieval",
    "capabilities": ["dataset_query", "data_aggregation", "data_analysis", "ontology_mapping"],
    "input_stream": "stream:agents:data-query:requests:v1",
    "output_stream": "stream:agents:data-query:responses:v1",
    "input_schema": "https://schemas.acme.com/agents/data-query-request/1-0-0.json",
    "output_schema": "https://schemas.acme.com/agents/data-query-response/1-0-0.json",
    "supported_datasets": list(DATASETS.keys()),
    "ontology_concepts": [
        "https://schema.org/salesRevenue",
        "https://schema.org/Customer",
        "https://schema.org/Product"
    ],
    "tools": ["query_dataset", "get_dataset_schema", "analyze_dataset"],
    "status": "active"
}

if __name__ == "__main__":
    # Register agent
    redis_set_json(
        f"agent:registry:{AGENT_REGISTRY_ENTRY['id']}", 
        AGENT_REGISTRY_ENTRY
    )
    print(f"[DataQueryAgent] Registered in agent registry")
    
    # Start processing
    run_data_query_agent()
