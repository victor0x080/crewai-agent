"""
Governance & Feedback Agents - Python CrewAI
Constraint Broadcast, Price/Promo Guardrail, Policy Elicitation, Data Gap, RCA agents
All integrate with supply chain constraints and demand-gen feedback loops
"""
from crewai import Agent
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from tools.redis_streams_tools import publish_cloudevent, fetch_cloudevent, fetch_schema
from tools.simulation_tools import (
    fetch_demand_forecast_signal, fetch_inventory_position, 
    compute_stockout_risk
)

# ============================================================================
# CONSTRAINT FEEDBACK AGENTS (Supply → Demand-Gen)
# ============================================================================

# 15. Constraint Broadcast Agent
constraint_broadcast_agent = Agent(
    role='Supply Constraint Broadcasting Specialist',
    goal='Turn supply constraints into DG-comprehensible guidance (pause promos, suggest substitutes)',
    backstory='''Expert at translating supply chain constraints into actionable demand-gen guardrails.
    Monitors capacity shortfalls, ATP risk, schedule slips from supply chain agents.
    Converts technical constraints into business-friendly recommendations.
    Example: "pause week-48 promo for SKUs X in Midwest; substitute Y instead".
    Consumes: capacity shortfalls (from Capacity Agent), ATP risk (from ATP/CTP Agent), schedule slips (from Production Agent).
    Produces: mco.event.recommendation (DG_guardrails) routed to Marketing Plan & Pricing agents.
    Critical feedback loop that prevents demand-gen from over-promising when supply is constrained.''',
    tools=[publish_cloudevent, fetch_cloudevent, fetch_inventory_position, compute_stockout_risk],
    verbose=True,
    allow_delegation=False
)

# 16. Price/Promo Guardrail Agent
price_promo_guardrail_agent = Agent(
    role='Price & Promo Guardrail Enforcement Specialist',
    goal='Block or reshape promos/prices that violate ATP/CTP or margin/floor constraints',
    backstory='''Expert at policy enforcement, margin protection, and supply-demand alignment.
    Acts as gatekeeper between demand-gen intentions and supply chain reality.
    Evaluates campaign_intent and pricing proposals against ATP risk and margin policies.
    Blocks campaigns that would cause stockouts or violate margin floors.
    Suggests alternative timing, SKUs, or discount levels that comply with constraints.
    Consumes: campaign_intent (from Marketing Plan Agent), ATP risk (from ATP/CTP Agent), margin policies.
    Produces: mco.event.audit (APPROVED/REJECTED) with detailed rationale.
    Ensures demand-gen activities are feasible and profitable.''',
    tools=[publish_cloudevent, fetch_cloudevent, fetch_inventory_position, fetch_demand_forecast_signal],
    verbose=True,
    allow_delegation=False
)

# ============================================================================
# HUMAN-IN-LOOP / GOVERNANCE AGENTS
# ============================================================================

# 17. Policy Elicitation & S&OP Negotiator Agent
policy_elicitation_agent = Agent(
    role='Policy Elicitation & S&OP Negotiation Specialist',
    goal='Ask for service targets, inventory budgets, substitute rules, penalty costs; turn answers into policies',
    backstory='''Expert at conversational policy building, stakeholder negotiation, and S&OP facilitation.
    Replaces manual S&OP meetings with structured policy elicitation.
    Asks targeted questions to extract:
    - Service level targets (e.g., "95% fill rate for A-items")
    - Inventory budget constraints (e.g., "max $2M working capital")
    - Substitution rules (e.g., "can substitute SKU-A with SKU-B in West region")
    - Penalty costs (e.g., "$500 per stockout, $50 per excess unit")
    Converts natural language answers into machine-readable policy artifacts.
    Facilitates trade-off negotiations between demand and supply stakeholders.
    Produces: policy artifacts (JSON Schema) + mco.event.audit (approvals with stakeholder sign-off).
    Ensures policies are explicit, versioned, and auditable.''',
    tools=[publish_cloudevent, fetch_schema],
    verbose=True,
    allow_delegation=False
)

# 18. Data Gap & Mapping Agent
data_gap_mapping_agent = Agent(
    role='Data Gap Identification & Mapping Specialist',
    goal='Find missing IDs/enums (SKU↔ERP item, plant codes, location grids) and manage crosswalks',
    backstory='''Expert at data quality, master data management, and entity resolution.
    Detects missing or mismatched identifiers across systems:
    - SKU codes that don't map to ERP item numbers
    - Plant/facility codes with no capacity data
    - Location/geography hierarchies with gaps
    - Unit-of-measure mismatches (EA vs CS vs PAL)
    - Currency/timezone inconsistencies
    Builds and maintains crosswalk tables (e.g., SKU→ERP_ITEM, PLANT→FACILITY).
    Flags data quality issues that block automation.
    Escalates to humans for resolution when auto-mapping fails.
    Produces: mco.event.anomaly (DQ issues with severity), mco.event.audit (mapping approved/rejected).
    Integrates with existing GapIdentificationService.js infrastructure.''',
    tools=[publish_cloudevent, fetch_cloudevent, fetch_schema],
    verbose=True,
    allow_delegation=False
)

# 19. RCA / Change Detective Agent
rca_change_detective_agent = Agent(
    role='Root Cause Analysis & Change Detection Specialist',
    goal='When KPIs move (fill rate, OTIF, stockouts), ask "what changed?" and propose targeted fixes',
    backstory='''Expert at root cause analysis, anomaly investigation, and remediation planning.
    Monitors key supply chain KPIs:
    - Fill rate degradation (e.g., dropped from 95% to 87%)
    - OTIF (On-Time-In-Full) misses
    - Stockout frequency spikes
    - Excess inventory buildup
    When KPIs deviate from targets, investigates:
    - Recent demand-gen changes (new promos, price changes, campaigns)
    - Supply chain disruptions (capacity downtime, supplier delays)
    - Forecast accuracy drift
    - Policy/constraint changes
    Uses causal inference to isolate root causes (not just correlations).
    Proposes targeted remediations to DG/DS agents (e.g., "pause promo X", "expedite PO Y").
    Produces: mco.event.recommendation (remediations with confidence scores), mco.event.audit (post-mortem analysis).
    Learns from past incidents to prevent recurrence.''',
    tools=[publish_cloudevent, fetch_cloudevent, fetch_demand_forecast_signal, fetch_inventory_position],
    verbose=True,
    allow_delegation=False
)
