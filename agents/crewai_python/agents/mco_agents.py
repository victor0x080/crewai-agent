"""
MCO (Marketing Campaign Optimization) Agents
21 agents for the full MCO pipeline
"""
from crewai import Agent
import sys
from pathlib import Path
# Add parent directory to path so we can import tools
sys.path.insert(0, str(Path(__file__).parent.parent))
from tools.redis_streams_tools import publish_cloudevent, fetch_schema, fetch_cloudevent
from tools.schema_validation_tools import publish_platform_action, validate_against_schema
from tools.normalization_tools import (
    detect_field_type,
    infer_column_mapping,
    normalize_metric,
    normalize_datetime,
    normalize_product_id,
    classify_campaign_tactic,
    extract_promo_attributes,
    parse_audience_definition,
    extract_kpi_formula,
    validate_data_quality
)
from tools.ontology_tools import resolve_concept, expand_concepts, map_enum

# Core Pipeline (11 agents)

# 1. Ingress & Normalization Agent
ingress = Agent(
    role='Data Ingress & Normalization Specialist',
    goal='Pull marketing data from external APIs and normalize to CloudEvents using canonical schema',
    backstory="""Expert at API integration (Google/Meta/DV360/Amazon Ads), schema mapping, and data quality.
    
    Your workflow: (1) Detect field types and map to canonical schema, (2) Normalize metrics/dates/product IDs,
    (3) Extract business logic (campaign tactics, promotions, audience segments, KPIs), (4) Enrich with ontology
    concepts, (5) Validate data quality (clicks <= impressions, etc.), (6) Validate against schema and publish.
    
    Use the canonical manufacturer RMN model as target schema. If confidence < 0.60 or quality_score < 0.70,
    flag for review or send to DLQ. Always preserve source metadata for audit trail.""",
    tools=[
        # Core tools
        publish_cloudevent,
        validate_against_schema,
        fetch_schema,
        # Normalization tools
        detect_field_type,
        infer_column_mapping,
        normalize_metric,
        normalize_datetime,
        normalize_product_id,
        classify_campaign_tactic,
        extract_promo_attributes,
        parse_audience_definition,
        extract_kpi_formula,
        validate_data_quality,
        # Ontology tools for semantic enrichment
        resolve_concept,
        expand_concepts,
        map_enum
    ],
    verbose=True,
    allow_delegation=False
)

# 2. Catalog & Schema Agent
catalog = Agent(
    role='Catalog & Schema Discovery Specialist',
    goal='Discover and version schemas from data sources',
    backstory='Expert at schema inference, versioning, compatibility checking',
    tools=[publish_cloudevent, fetch_schema],
    verbose=True,
    allow_delegation=False
)

# 3. Feature & Forecast Agent
feature_forecast = Agent(
    role='Feature Engineering & Forecasting Specialist',
    goal='Build features and generate time series forecasts',
    backstory='Expert at feature engineering, time series analysis, Prophet/ARIMA',
    tools=[publish_cloudevent],
    verbose=True,
    allow_delegation=False
)

# 4. Attribution & Causal Agent
attribution = Agent(
    role='Attribution & Causal Inference Specialist',
    goal='Attribute outcomes to causes using experiments',
    backstory='Expert at MMM, MTA, incrementality testing, causal inference',
    tools=[publish_cloudevent],
    verbose=True,
    allow_delegation=False
)

# 5. Opportunity Scanner Agent
opportunity = Agent(
    role='Opportunity Detection Specialist',
    goal='Detect anomalies and opportunities in data',
    backstory='Expert at anomaly detection, pattern recognition, alerting',
    tools=[publish_cloudevent],
    verbose=True,
    allow_delegation=False
)

# 6. Cost & Finance Mapper Agent
cost_finance = Agent(
    role='Cost & Finance Mapping Specialist',
    goal='Map marketing spend to P&L categories',
    backstory='Expert at cost allocation, P&L mapping, financial reporting',
    tools=[publish_cloudevent],
    verbose=True,
    allow_delegation=False
)

# 7. Budget Optimizer Agent
budget_optimizer = Agent(
    role='Budget Optimization Specialist',
    goal='Optimize budget allocation across channels',
    backstory='Expert at portfolio optimization, constraint programming, ROI maximization',
    tools=[publish_cloudevent, publish_platform_action, validate_against_schema],
    verbose=True,
    allow_delegation=False
)

# 8. Bid & Target Setter Agent
bid_target = Agent(
    role='Bid & Target Setting Specialist',
    goal='Set optimal bids and targets for campaigns',
    backstory='Expert at bid optimization, CPA/ROAS targets, auction dynamics',
    tools=[publish_cloudevent, publish_platform_action, validate_against_schema],
    verbose=True,
    allow_delegation=False
)

# 9. Creative Ops Agent
creative_ops = Agent(
    role='Creative Operations Specialist',
    goal='Generate and optimize creative assets',
    backstory='Expert at creative generation, A/B testing, performance prediction',
    tools=[publish_cloudevent],
    verbose=True,
    allow_delegation=False
)

# 10. Base Platform Adapter Agent
platform_adapter = Agent(
    role='Platform Integration Specialist',
    goal='Integrate with advertising platforms',
    backstory='Expert at platform APIs, bulk operations, error handling',
    tools=[publish_cloudevent],
    verbose=True,
    allow_delegation=False
)

# 11. Question Router & Planner Agent
qrp = Agent(
    role='Query Routing & Planning Specialist',
    goal='Route questions and plan execution steps',
    backstory='Expert at query understanding, plan generation, orchestration',
    tools=[publish_cloudevent],
    verbose=True,
    allow_delegation=False
)

# Integration Wrappers (10 agents)

# 12. Validator & Registry Agent
validator = Agent(
    role='Schema Validation Specialist',
    goal='Validate data against schemas',
    backstory='Expert at JSON Schema validation, versioning, compatibility',
    tools=[fetch_schema, validate_against_schema],
    verbose=True,
    allow_delegation=False
)

# 13. Semantic Router Agent
semantic_router = Agent(
    role='Semantic Routing Specialist',
    goal='Route events using vector embeddings and ontology',
    backstory='Expert at vector search, KNN, synonym expansion, RediSearch',
    tools=[publish_cloudevent, fetch_cloudevent],
    verbose=True,
    allow_delegation=False
)

# 14. Guardrail & Compliance Agent
guardrail = Agent(
    role='Compliance & Guardrail Specialist',
    goal='Enforce policies and compliance rules',
    backstory='Expert at RBAC, approval workflows, risk thresholds, PII compliance',
    tools=[publish_cloudevent],
    verbose=True,
    allow_delegation=False
)

# 15. Safeguard & Rollback Agent
safeguard = Agent(
    role='Safeguard & Rollback Specialist',
    goal='Monitor SLOs and rollback on failures',
    backstory='Expert at circuit breakers, confidence thresholds, rollback strategies',
    tools=[publish_cloudevent],
    verbose=True,
    allow_delegation=False
)

# 16. Data Gap & Mapping Agent
data_gap = Agent(
    role='Data Gap Identification Specialist',
    goal='Identify missing fields and suggest mappings',
    backstory='Expert at schema diffing, field mapping, LLM-based gap detection',
    tools=[publish_cloudevent, fetch_schema],
    verbose=True,
    allow_delegation=False
)

# 17. Goal & Policy Elicitation Agent
goal_policy = Agent(
    role='Policy Elicitation Specialist',
    goal='Convert objectives to machine-readable policies',
    backstory='Expert at conversational policy building, constraint extraction',
    tools=[publish_cloudevent],
    verbose=True,
    allow_delegation=False
)

# 18. Counterfactual & Experiment Agent
counterfactual = Agent(
    role='Experiment Design Specialist',
    goal='Design holdout experiments and power analysis',
    backstory='Expert at experimental design, statistical power, A/B testing',
    tools=[publish_cloudevent],
    verbose=True,
    allow_delegation=False
)

# 19. Change Detective & RCA Agent
change_detective = Agent(
    role='Root Cause Analysis Specialist',
    goal='Diagnose metric changes and find root causes',
    backstory='Expert at anomaly investigation, drill-down analysis, causal graphs',
    tools=[publish_cloudevent],
    verbose=True,
    allow_delegation=False
)

# 20. Exception Triage Agent
exception_triage = Agent(
    role='Exception Triage Specialist',
    goal='Escalate low-confidence decisions to humans',
    backstory='Expert at confidence scoring, escalation rules, human-in-loop workflows',
    tools=[publish_cloudevent],
    verbose=True,
    allow_delegation=False
)

# 21. Translator & Contract Agent
translator = Agent(
    role='Schema Translation Specialist',
    goal='Translate events between schemas with validation',
    backstory='Expert at schema mapping, LLM-based translation, contract validation',
    tools=[publish_cloudevent, fetch_schema, validate_against_schema],
    verbose=True,
    allow_delegation=False
)
