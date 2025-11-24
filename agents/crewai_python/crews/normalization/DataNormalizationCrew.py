#!/usr/bin/env python3
"""
Data Normalization Crew - Hierarchical Multi-Agent System

Normalizes heterogeneous data from RMNs, manufacturers, POS systems into
canonical trade desk data model using 9 specialized agents coordinated by a manager.

Features:
- Ontology-aware semantic routing
- Two-stage validation (JSON Schema + SHACL)
- Continuous learning (mapping cache, ontology evolution, ML training)
- Taxonomy versioning and tracking
- Human-in-the-loop for low-confidence cases

Compliance: 100% Redis Streams + CloudEvents + Ontology + CrewAI Hierarchical Process
"""
import sys
import os
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import json
import asyncio
from typing import List, Dict, Any, Optional
from datetime import datetime

from crewai import Agent, Crew, Task, Process
from crewai.tasks.task_output import TaskOutput

# Import CrewAI Manager Service pattern
try:
    from CrewAIManagerService import (
        CrewAIManagerService,
        ManagerConfig,
        redis_client,
        redis_publish,
        redis_ack,
        fetch_schema,
        validate_jsonschema
    )
except ImportError:
    print("⚠️  Warning: CrewAIManagerService not found. Please ensure it's in the path.")
    # Stub for testing
    class CrewAIManagerService:
        def __init__(self, config, manager, crew):
            pass
        def start(self):
            pass
        def stop(self):
            pass
    class ManagerConfig:
        def __init__(self, **kwargs):
            for k, v in kwargs.items():
                setattr(self, k, v)
    redis_client = None
    async def redis_publish(*args, **kwargs): pass
    async def redis_ack(*args, **kwargs): pass
    async def fetch_schema(*args, **kwargs): return {}
    async def validate_jsonschema(*args, **kwargs): return {'valid': True}

# Import tools
try:
    from tools.ontology_tools import (
        resolve_concept,
        expand_concepts,
        map_enum,
        get_category_constraints
    )
    from tools.shacl_tools import validate_shacl, get_shacl_shape
except ImportError:
    print("⚠️  Warning: Some tools not available. Using stubs.")
    # Stub functions for testing
    async def resolve_concept(term): return f"ex:{term}"
    async def expand_concepts(concepts, relations=None, depth=1): return concepts
    async def map_enum(field, value): return value
    async def get_category_constraints(concept): return {}
    async def validate_shacl(data, shape): return {'conforms': True, 'violations': []}
    async def get_shacl_shape(uri): return {}


# ============================================================================
# WORKER AGENTS
# ============================================================================

def build_schema_discovery_agent() -> Agent:
    """Agent 1: Schema Discovery & Field Mapping"""
    return Agent(
        role="Schema Discovery & Field Mapping Specialist",
        goal="Infer CDM field for each raw column with 70%+ confidence using regex, ML, LLM, and vector similarity",
        backstory="""Data schema expert with 10+ years analyzing diverse data formats from 100+ partners.
        Specializes in pattern recognition, synonym detection, and intelligent field mapping.
        Uses combination of rule-based matching, ML classification, and LLM reasoning for ambiguous cases.
        
        Your approach:
        1. Apply regex patterns first (impr|impressions → impressions_count)
        2. Use ML column-type classifier
        3. Query vector database for similar columns
        4. Use ontology to expand synonyms
        5. For ambiguous cases, invoke LLM with context
        6. Cache successful mappings for reuse""",
        allow_delegation=False,
        verbose=True
    )


def build_metrics_time_agent() -> Agent:
    """Agent 2: Metrics & Time Normalization"""
    return Agent(
        role="Metrics & Time Normalization Specialist",
        goal="Normalize impressions, clicks, spend, CPM, CTR, dates, timezones to canonical definitions with 85%+ accuracy",
        backstory="""Senior analytics engineer with expertise in digital marketing metrics standardization.
        Specializes in metric formula validation, unit conversion, time zone normalization, and data quality enforcement.
        Deep knowledge of advertising KPI definitions (CTR, CPM, ROAS) across platforms.
        
        Your validation rules:
        - clicks ≤ impressions
        - 0 ≤ CTR ≤ 100%
        - spend ≥ 0
        - No impossible metric values (e.g., CPM > $1000)
        - Timezone normalization to UTC
        - Date format standardization (ISO 8601)""",
        allow_delegation=False,
        verbose=True
    )


def build_product_taxonomy_agent() -> Agent:
    """Agent 3: Product Identity & Taxonomy Normalization"""
    return Agent(
        role="Product Identity & Taxonomy Normalization Specialist",
        goal="Normalize product IDs (GTIN/UPC/ASIN) and map to canonical product/category taxonomy with 75%+ accuracy",
        backstory="""Product data management expert with deep knowledge of GS1 standards, retail taxonomies, and brand hierarchies.
        Specializes in product ID resolution, category mapping, and attribute extraction from unstructured product names.
        Expert at handling multi-pack variations, size normalization, and cross-retailer product matching.
        
        Your process:
        1. Detect product ID format (GTIN-14, UPC-12, ASIN, etc.)
        2. Resolve to canonical product ID
        3. Extract attributes (brand, size, pack count) from title
        4. Classify into product taxonomy using ML + ontology
        5. Apply category-specific constraints (e.g., minMarginPct for Beverages)
        6. Handle taxonomy version mapping if source uses old taxonomy""",
        allow_delegation=False,
        verbose=True
    )


def build_campaign_tactic_agent() -> Agent:
    """Agent 4: Campaign & Tactic Normalization"""
    return Agent(
        role="Campaign & Tactic Normalization Specialist",
        goal="Interpret campaign names and map to canonical tactics (Sponsored Product, Display, Video) with 70%+ confidence",
        backstory="""Digital advertising strategist with 12+ years across Google, Meta, Amazon, Walmart platforms.
        Specializes in campaign taxonomy, ad format classification, and funnel stage mapping.
        Expert at parsing campaign naming conventions and extracting objective, tactic, and targeting strategy.
        
        Your parsing logic:
        1. Apply RMN-specific code mappings (e.g., WMT_SP_SEARCH → Sponsored Product Search)
        2. Detect keywords (SP, SB, SD, Display, Video, CTV)
        3. Use ML classifier for campaign name patterns
        4. Extract campaign structure: Brand | Product | Tactic | Targeting | Objective
        5. Map to canonical tactic taxonomy
        6. Infer funnel stage (awareness, consideration, conversion)""",
        allow_delegation=False,
        verbose=True
    )


def build_pos_promo_agent() -> Agent:
    """Agent 5: POS & Promotion Normalization"""
    return Agent(
        role="POS & Promotion Normalization Specialist",
        goal="Normalize POS transactions and promotions to canonical store-SKU-day grain with 75%+ accuracy",
        backstory="""Retail operations analyst with expertise in POS data, promotional mechanics, and in-store execution.
        Specializes in promo type classification (TPR, BOGO, coupon), display tracking, and sales decomposition.
        Deep knowledge of retail calendars, holiday periods, and promotional event patterns.
        
        Your normalization steps:
        1. Enforce canonical grain: Store × SKU × Day (or Week)
        2. Derive revenue = units × price
        3. Classify promo type from description or code
        4. Extract promo attributes: discount_pct, display_type, duration
        5. Validate promotional calendar alignment
        6. Flag unusual patterns (e.g., promo without discount)""",
        allow_delegation=False,
        verbose=True
    )


def build_audience_segment_agent() -> Agent:
    """Agent 6: Audience & Segment Normalization"""
    return Agent(
        role="Audience & Segment Normalization Specialist",
        goal="Normalize audience/segment labels into canonical ontology with 65%+ confidence",
        backstory="""Customer analytics specialist with expertise in segmentation, loyalty programs, and audience taxonomies.
        Specializes in mapping partner-specific segment labels to canonical lifecycle/value/demo attributes.
        Expert at extracting tenure windows, spend bands, recency definitions from free-text labels.
        
        Your extraction logic:
        1. Detect tenure cues: "lapsed", "new", "26 weeks", "180 days"
        2. Identify value bands: "heavy buyers", "high value", "VIP"
        3. Parse lifecycle: "prospect", "active", "at-risk", "churned"
        4. Extract demographics: age, gender, location
        5. Map to canonical audience ontology
        6. Cluster similar segments for consistency""",
        allow_delegation=False,
        verbose=True
    )


def build_kpi_attribution_agent() -> Agent:
    """Agent 7: KPI & Attribution Normalization"""
    return Agent(
        role="KPI & Attribution Normalization Specialist",
        goal="Normalize KPI definitions and attribution settings with 60%+ confidence",
        backstory="""Measurement science expert with deep knowledge of attribution models, incrementality testing, and KPI frameworks.
        Specializes in extracting attribution windows, baseline definitions, and formula specifications from documentation.
        Expert at distinguishing total vs incremental metrics, brand vs non-brand attribution.
        
        Your extraction process:
        1. Parse KPI formula (e.g., ROAS = revenue / spend)
        2. Extract attribution window (7-day click, 1-day view)
        3. Identify attribution model (last-click, multi-touch, first-touch)
        4. Detect baseline definition (for incrementality metrics)
        5. Classify KPI family (efficiency vs volume vs incrementality)
        6. Map to canonical KPI ontology""",
        allow_delegation=False,
        verbose=True
    )


def build_qa_governance_agent() -> Agent:
    """Agent 8: Quality Assurance & Governance"""
    return Agent(
        role="Quality Assurance & Governance Specialist",
        goal="Cross-validate normalized data, detect anomalies, enforce governance policies with 90%+ accuracy",
        backstory="""Data quality engineer with expertise in cross-field validation, drift detection, and governance frameworks.
        Specializes in detecting logical contradictions, sum-of-parts reconciliation, and hierarchy validation.
        Expert at generating human-readable explanations for flagged issues and recommended remediation.
        
        Your validation checks:
        1. Cross-field consistency (audience not both "new" AND "loyal > 2 years")
        2. Hierarchy integrity (category rolls up correctly)
        3. Sum-of-parts reconciliation (sub-totals match totals)
        4. Distribution drift detection (compare to historical patterns)
        5. SHACL policy enforcement (minMarginPct per category)
        6. Generate human-readable issue explanations""",
        allow_delegation=False,
        verbose=True
    )


def build_orchestrator_agent() -> Agent:
    """Agent 9: Workflow Orchestration"""
    return Agent(
        role="Workflow Orchestration Specialist",
        goal="Determine agent execution sequence and merge outputs with 80%+ efficiency",
        backstory="""Workflow automation expert with deep knowledge of dependency graphs and parallel execution patterns.
        Specializes in determining optimal agent execution order, handling failures gracefully, and aggregating results.
        Expert at branching logic (skip agents if not applicable), retry strategies, and compensation workflows.
        
        Your orchestration logic:
        1. Analyze field types from schema discovery
        2. Determine which specialists to invoke
        3. Execute independent agents in parallel
        4. Sequence dependent agents (e.g., QA after all specialists)
        5. Handle agent failures with retries or skips
        6. Merge specialist outputs into final canonical record
        7. Log transformation lineage""",
        allow_delegation=False,
        verbose=True
    )


# ============================================================================
# MANAGER AGENT
# ============================================================================

def build_manager() -> Agent:
    """Manager agent that coordinates all workers"""
    return Agent(
        role="Data Normalization Orchestra Conductor",
        goal="Coordinate 9 specialist agents to normalize heterogeneous data into canonical trade desk model with 95%+ accuracy and <30s latency",
        backstory="""You are an expert data integration architect with 15+ years building ETL pipelines for Fortune 500 retailers.
        You coordinate a team of 9 specialists to handle complex, multi-source data transformations.
        
        Your workflow:
        1. **Schema Discovery**: Delegate to SchemaDiscoveryAgent to map raw columns → CDM fields
        2. **Field Routing**: Based on field types, route to appropriate specialists:
           - Metrics/dates → MetricsTimeAgent
           - Products → ProductTaxonomyAgent
           - Campaigns → CampaignTacticAgent
           - POS/Promos → POSPromoAgent
           - Audiences → AudienceSegmentAgent
           - KPIs → KPIAttributionAgent
        3. **Parallel Execution**: Execute independent specialists concurrently
        4. **Orchestration**: OrchestratorAgent merges outputs
        5. **QA Validation**: QAGovernanceAgent performs final checks
        6. **Publishing**: Validate against schema and publish to target stream
        
        You ensure each step completes successfully. You handle errors gracefully.
        You escalate to humans when confidence < 0.60.
        You publish final results to the target stream and acknowledge the route decision.
        
        You have access to:
        - redis_publish: Publish CloudEvents to Redis Streams
        - redis_ack: Acknowledge processed messages
        - fetch_schema: Retrieve JSON schemas from registry
        - validate_jsonschema: Validate payloads against schemas""",
        tools=[redis_publish, redis_ack, fetch_schema, validate_jsonschema],
        allow_delegation=True,
        verbose=True
    )


# ============================================================================
# CREW BUILDING
# ============================================================================

def build_crew() -> tuple:
    """Build the complete normalization crew"""
    
    # Config
    config = ManagerConfig(
        manager_id="data-normalization-manager",
        crew_id="data-normalization-crew",
        route_stream="stream:ingestion:raw-data",
        consumer_group="normalization",
        consumer_name="normalization-manager-1"
    )
    
    # Build manager
    manager = build_manager()
    
    # Build workers
    workers = [
        build_schema_discovery_agent(),
        build_metrics_time_agent(),
        build_product_taxonomy_agent(),
        build_campaign_tactic_agent(),
        build_pos_promo_agent(),
        build_audience_segment_agent(),
        build_kpi_attribution_agent(),
        build_qa_governance_agent(),
        build_orchestrator_agent()
    ]
    
    # Build task
    task = Task(
        description="""
        Execute complete data normalization workflow:
        
        **Step 1: Schema Discovery**
        Delegate to SchemaDiscoveryAgent to analyze raw data and map columns to CDM fields.
        
        **Step 2: Field Type Routing**
        Based on discovered fields, route to appropriate specialists:
        - Metrics (impressions, clicks, spend) → MetricsTimeAgent
        - Product IDs, categories → ProductTaxonomyAgent
        - Campaign names, tactics → CampaignTacticAgent
        - POS transactions, promos → POSPromoAgent
        - Audience segments → AudienceSegmentAgent
        - KPI definitions → KPIAttributionAgent
        
        **Step 3: Parallel Specialist Execution**
        Execute independent agents concurrently for performance.
        
        **Step 4: Orchestration**
        OrchestratorAgent merges specialist outputs into unified record.
        
        **Step 5: QA Validation**
        QAGovernanceAgent performs cross-field validation, SHACL policy checks, anomaly detection.
        
        **Step 6: Publishing**
        - Validate final record against target schema
        - If valid: Publish to target_stream
        - If invalid: Send to DLQ with detailed errors
        - Acknowledge route decision
        
        Input variables:
        - source_event: Raw data from ingestion
        - target_schema_uri: Target schema for validation
        - target_stream: Redis stream for publishing normalized data
        - route_msg_id: Message ID to acknowledge
        - route_stream: Route stream for acknowledgment
        
        Output must include:
        - normalized_data: Canonical trade desk model record
        - confidence: Overall confidence score
        - mapping_log: Field-level transformation lineage
        - validation_results: JSON Schema + SHACL results
        - warnings: Any issues detected
        """,
        agent=manager,
        expected_output="""A complete normalization result with:
        - Normalized data validated against target schema
        - Confidence scores at field and record level
        - Mapping lineage for audit trail
        - Validation results (JSON Schema + SHACL)
        - Warnings for human review if needed
        
        Result published to target stream and route decision acknowledged."""
    )
    
    # Build crew with hierarchical process
    crew = Crew(
        agents=[manager] + workers,
        tasks=[task],
        process=Process.hierarchical,
        manager_agent=manager,
        verbose=True,
        memory=True,  # Enable crew memory
        cache=True    # Enable caching
    )
    
    return config, crew


# ============================================================================
# REGISTRATION
# ============================================================================

def register_crew():
    """Display registration command"""
    print("""
    ╔══════════════════════════════════════════════════════════════════════╗
    ║         DATA NORMALIZATION CREW - Registration Command              ║
    ╚══════════════════════════════════════════════════════════════════════╝
    
    To register this crew, run:
    
    curl -X POST http://localhost:3000/api/managers/register \\
      -H "Content-Type: application/json" \\
      -d '{
        "manager_id": "data-normalization-manager",
        "crew_id": "data-normalization-crew",
        "route_stream": "stream:ingestion:raw-data",
        "consumes_types": [
          "com.acme.ingestion.rmn.data",
          "com.acme.ingestion.manufacturer.data",
          "com.acme.ingestion.pos.data",
          "com.acme.ingestion.loyalty.data"
        ],
        "produces_streams": [
          "stream:normalized:canonical-data",
          "stream:dlq"
        ],
        "produces_schemas": [
          "https://schemas.acme.com/canonical/trade-desk/1.0.0"
        ],
        "capabilities": [
          "normalization",
          "schema_mapping",
          "data_quality",
          "ontology_integration",
          "taxonomy_mapping",
          "ml_classification"
        ],
        "policy": {
          "min_confidence": 0.60,
          "max_latency_ms": 30000,
          "max_error_rate_pct": 10,
          "failure_threshold": 3,
          "success_threshold": 2,
          "timeout_ms": 60000
        },
        "owner": "data-engineering@acme.com",
        "description": "Normalizes heterogeneous retail media data into canonical trade desk model using 9 specialized agents with ontology-aware routing and continuous learning"
      }'
    """)


# ============================================================================
# MAIN ENTRY POINT
# ============================================================================

if __name__ == '__main__':
    print("=" * 80)
    print("  DATA NORMALIZATION CREW - Hierarchical Multi-Agent System")
    print("=" * 80)
    print()
    
    # Build crew
    config, crew = build_crew()
    
    print(f"Manager: {crew.manager_agent.role}")
    print(f"Workers: {len(crew.agents) - 1}")
    print(f"Process: {crew.process}")
    print()
    print("Worker Agents:")
    for i, agent in enumerate(crew.agents[1:], 1):
        print(f"  {i}. {agent.role}")
    print()
    
    # Show registration
    register_crew()
    
    # Start service
    print("\nStarting Manager Service...")
    print(f"Route stream: {config.route_stream}")
    print(f"Consumer group: {config.consumer_group}")
    print()
    
    service = CrewAIManagerService(config, crew.manager_agent, crew)
    
    try:
        print("✅ Service started. Waiting for messages...")
        print("Press Ctrl+C to stop.\n")
        service.start()
    except KeyboardInterrupt:
        print("\n\n⚠️  Shutting down...")
        service.stop()
        print("✅ Service stopped.")

