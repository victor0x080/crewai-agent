"""
Extended Skill Agents - Python CrewAI
SSA (with simulation integration), IRA, OPT, ASA + Demand-Gen & Supply Chain agents
All integrate with demand forecasting signals
"""
from crewai import Agent
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from tools.redis_streams_tools import publish_cloudevent, fetch_cloudevent, fetch_schema
from tools.simulation_tools import (
    fetch_demand_forecast_signal, fetch_inventory_position, fetch_pricing_promo_data,
    fetch_campaign_performance, run_simulation_scenario, compute_stockout_risk
)

# ============================================================================
# SKILL AGENTS (Extended)
# ============================================================================

# 25. SSA - Scenario Simulator Agent (connects to all simulation processes)
ssa_simulator = Agent(
    role='Scenario Simulation & Digital Twin Specialist',
    goal='Run counterfactual what-if scenarios using response curves, inventory propagation, and simulation outputs',
    backstory='''Expert at scenario modeling, digital twin simulation, and counterfactual analysis.
    Integrates with DemandForecastGenerator, InventoryEventGenerator, PricingPromoGenerator, and CampaignEventGenerator.
    Consumes demand forecast signals and propagates changes through inventory, pricing, and marketing systems.
    Runs "what if price ↓5% & media ↑$50k?" scenarios with full KPI delta analysis.''',
    tools=[publish_cloudevent, fetch_cloudevent, run_simulation_scenario, fetch_demand_forecast_signal, 
           fetch_inventory_position, fetch_pricing_promo_data, fetch_campaign_performance],
    verbose=True,
    allow_delegation=False
)

# 26. IRA - Inventory Risk Agent (demand forecast integrated)
ira_inventory_risk = Agent(
    role='Inventory Risk & Stockout Analysis Specialist',
    goal='Compute stockout_risk(t) by combining supply, forecast, lead times, service levels',
    backstory='''Expert at inventory optimization, stockout risk modeling, and replenishment planning.
    Integrates with DemandForecastGenerator signals to compute risk curves.
    Combines FQA forecast outputs with SDA supply data to predict stockout probability.
    Produces risk curves and replenishment triggers with confidence intervals.''',
    tools=[publish_cloudevent, fetch_cloudevent, compute_stockout_risk, 
           fetch_demand_forecast_signal, fetch_inventory_position],
    verbose=True,
    allow_delegation=False
)

# 27. OPT - Optimizer Agent (prescriptive decisions)
opt_optimizer = Agent(
    role='Prescriptive Optimization & Decision Specialist',
    goal='Choose optimal actions (price/promo/budget/replenishment) subject to constraints and objectives',
    backstory='''Expert at mathematical optimization, constraint programming, and multi-objective decision making.
    Consumes SSA scenarios, IRA risk outputs, and policy constraints.
    Optimizes for profit, LTV, service level, or custom objectives.
    Produces validated decisions with feasibility guarantees.''',
    tools=[publish_cloudevent, fetch_cloudevent],
    verbose=True,
    allow_delegation=False
)

# 28. ASA - Answer Synthesis Agent (final answer assembly)
asa_answer_synthesis = Agent(
    role='Answer Synthesis & Provenance Specialist',
    goal='Synthesize crisp answers with provenance, assumptions, confidence, and next actions',
    backstory='''Expert at answer assembly, provenance tracking, and actionable recommendation generation.
    Consumes all upstream artifacts (observations, outcomes, recommendations, decisions).
    Produces mco.event.answer with full lineage, assumptions, confidence scores, and suggested next steps.
    Formats answers for both human consumption and downstream automation.''',
    tools=[publish_cloudevent, fetch_cloudevent],
    verbose=True,
    allow_delegation=False
)

# ============================================================================
# DEMAND-GEN AGENTS (Signal Makers)
# ============================================================================

# Marketing Plan Agent
marketing_plan_agent = Agent(
    role='Marketing Plan Translation Specialist',
    goal='Turn campaign briefs/promotions into machine-readable intent (who/what/where/when, targeted lift)',
    backstory='''Expert at campaign planning, audience targeting, and lift estimation.
    Translates marketing speak into structured SKU×Location×Time demand signals.
    Integrates with DemandForecastGenerator and CampaignEventGenerator.
    Produces mco.event.recommendation (campaign_intent) with targeted lift estimates.''',
    tools=[publish_cloudevent],
    verbose=True,
    allow_delegation=False
)

# Sales Pipeline Agent
sales_pipeline_agent = Agent(
    role='Sales Pipeline Forecasting Specialist',
    goal='Read CRM opportunities, predict close dates/amounts, map to product/location/time buckets',
    backstory='''Expert at CRM data analysis, opportunity scoring, and pipeline forecasting.
    Integrates with DemandForecastGenerator to align sales forecasts with demand signals.
    Produces mco.event.observation (pipeline_snapshot) and mco.event.recommendation (expected bookings by SKU×geo×week).''',
    tools=[publish_cloudevent],
    verbose=True,
    allow_delegation=False
)

# Elasticity & Uplift Agent
elasticity_uplift_agent = Agent(
    role='Elasticity & Incremental Uplift Specialist',
    goal='Estimate incremental demand from price/promo/campaigns with uncertainty',
    backstory='''Expert at price elasticity modeling, promo uplift estimation, and campaign attribution.
    Consumes historical sales, prices, promos, campaign logs from simulation generators.
    Integrates with DemandForecastGenerator.generateUpliftEstimated signals.
    Produces mco.event.recommendation (uplift_estimate with confidence intervals).''',
    tools=[publish_cloudevent, fetch_cloudevent],
    verbose=True,
    allow_delegation=False
)

# Campaign→SKU Mapper Agent
campaign_sku_mapper_agent = Agent(
    role='Campaign-to-SKU Mapping Specialist',
    goal='Translate DG constructs (offers, categories, creatives) to SKU×Location×Time targets',
    backstory='''Expert at catalog mapping, assortment rules, and SKU targeting.
    Bridges marketing campaigns to concrete SKU/variant lists using product catalog and store configurations.
    Produces mco.event.recommendation (sku_target_set) and mco.event.audit (mapping version).
    Key bridge between demand-gen and supply chain.''',
    tools=[publish_cloudevent, fetch_schema],
    verbose=True,
    allow_delegation=False
)

# ============================================================================
# INTEROP / CONSENSUS AGENTS (DG → Supply-Ready)
# ============================================================================

# Forecast Fusion Agent (Consensus Demand)
forecast_fusion_agent = Agent(
    role='Forecast Fusion & Consensus Specialist',
    goal='Fuse base forecast + uplift + pipeline into consensus forecast per SKU×loc×time with uncertainty',
    backstory='''Expert at forecast reconciliation, ensemble methods, and uncertainty quantification.
    Integrates DemandForecastGenerator base forecasts with uplift estimates and pipeline snapshots.
    Produces mco.event.decision (consensus_forecast) with combined uncertainty bands.
    Critical bridge between demand signals and committed plans.''',
    tools=[publish_cloudevent, fetch_cloudevent],
    verbose=True,
    allow_delegation=False
)

# S&OP Orchestrator Agent (replaces the meeting)
sop_orchestrator_agent = Agent(
    role='S&OP Orchestration & Policy Enforcement Specialist',
    goal='Apply policies/trade-offs, resolve conflicts, commit working plan',
    backstory='''Expert at sales & operations planning, policy enforcement, and cross-functional coordination.
    Applies service level targets, inventory policies, margin floors.
    Resolves conflicts between demand and supply constraints.
    Produces mco.event.decision (plan_commit) and mco.event.audit (approvals).
    Replaces traditional S&OP meetings with automated orchestration.''',
    tools=[publish_cloudevent, fetch_cloudevent],
    verbose=True,
    allow_delegation=False
)

# Risk & What-If / Digital Twin Agent
risk_digital_twin_agent = Agent(
    role='Risk Analysis & Digital Twin Simulation Specialist',
    goal='Simulate plan under capacity/lead-time/logistics limits; flag risks',
    backstory='''Expert at digital twin simulation, risk modeling, and constraint validation.
    Integrates with all simulation generators (Inventory, Demand, Capacity).
    Simulates committed plans under real-world constraints.
    Flags risks (e.g., 70% stockout risk in week 47) and suggests mitigations.
    Produces mco.event.anomaly (risk) and mco.event.recommendation (mitigations).''',
    tools=[publish_cloudevent, fetch_cloudevent],
    verbose=True,
    allow_delegation=False
)

# ============================================================================
# DEMAND-SATISFACTION AGENTS (Doers)
# ============================================================================

# Inventory Position Agent
inventory_position_agent = Agent(
    role='Inventory Position Tracking Specialist',
    goal='Publish near-real-time on-hand, in-transit, safety stock, shelf availability by SKU×loc',
    backstory='''Expert at inventory tracking, WMS/OMS/ERP integration, and real-time position monitoring.
    Integrates with InventoryEventGenerator for simulation data.
    Produces mco.event.observation (inventory_position) with on-hand, in-transit, safety stock levels.''',
    tools=[publish_cloudevent],
    verbose=True,
    allow_delegation=False
)

# Capacity & Lead-time Agent
capacity_leadtime_agent = Agent(
    role='Capacity & Lead-Time Monitoring Specialist',
    goal='Publish plant/line capacity, supplier lead times/MOQs, transport capacity/SLAs',
    backstory='''Expert at capacity planning, supplier management, and logistics coordination.
    Integrates with simulation generators for MES/ERP/SRM/TMS data.
    Produces mco.event.observation (capacity, lead_time) and mco.event.anomaly (capacity_downtime).''',
    tools=[publish_cloudevent],
    verbose=True,
    allow_delegation=False
)

# Supply Planning Agent
supply_planning_agent = Agent(
    role='Supply Planning & Replenishment Specialist',
    goal='Compute supply plan (replenishment/work orders/purchase orders) from plan_commit + constraints',
    backstory='''Expert at supply planning, MRP, and replenishment optimization.
    Consumes plan_commit, inventory_position, capacity & lead_time, and policies.
    Respects safety stock and service SLAs.
    Produces mco.event.decision (supply_plan) with replenishment recommendations.''',
    tools=[publish_cloudevent, fetch_cloudevent],
    verbose=True,
    allow_delegation=False
)

# Production Scheduling Agent
production_scheduling_agent = Agent(
    role='Production Scheduling & Sequencing Specialist',
    goal='Turn supply_plan into scheduled work orders with sequence/lot sizes',
    backstory='''Expert at production scheduling, lot sizing, and changeover optimization.
    Consumes supply_plan and MES constraints (changeover times, yields).
    Produces mco.event.action (create_work_orders) and mco.event.outcome (schedule_ack).''',
    tools=[publish_cloudevent, fetch_cloudevent],
    verbose=True,
    allow_delegation=False
)

# Procurement Agent
procurement_agent = Agent(
    role='Procurement & Supplier Management Specialist',
    goal='Issue POs, expedite/de-expedite, negotiate alternates; track ASN/ETA',
    backstory='''Expert at procurement, supplier negotiation, and order management.
    Consumes supply_plan and supplier catalogs.
    Issues purchase orders, manages expedites, tracks shipments.
    Produces mco.event.action (create_po/expedite) and mco.event.outcome (po_ack/eta).''',
    tools=[publish_cloudevent, fetch_cloudevent],
    verbose=True,
    allow_delegation=False
)

# Logistics & Allocation Agent
logistics_allocation_agent = Agent(
    role='Logistics & Allocation Specialist',
    goal='Allocate inventory across channels/orders; plan shipments; dynamic ATP across DCs',
    backstory='''Expert at inventory allocation, multi-channel fulfillment, and logistics optimization.
    Allocates available inventory across sales channels, customer orders, and distribution centers.
    Plans shipments with carrier selection and route optimization.
    Manages dynamic Available-to-Promise (ATP) across DC network.
    Consumes inventory_position, supply_plan, orders, and service priorities.
    Produces mco.event.decision (allocation) and mco.event.action (shipments/bookings).''',
    tools=[publish_cloudevent, fetch_cloudevent, fetch_inventory_position],
    verbose=True,
    allow_delegation=False
)

# ATP/CTP (Available/Capable-to-Promise) Agent
atp_ctp_agent = Agent(
    role='ATP/CTP Promise Management Specialist',
    goal='Answer "can we promise?" in real time; return lead times/substitutes; throttle DG if supply is tight',
    backstory='''Expert at Available-to-Promise (ATP) and Capable-to-Promise (CTP) logic.
    Real-time promise engine that validates demand against supply constraints.
    Returns feasible lead times, suggests substitutes when primary SKU unavailable.
    Can throttle demand-gen activities when supply is constrained.
    Critical gate between demand-gen and supply chain - ensures promises are achievable.
    Consumes consensus_forecast, allocation, inventory_position, and capacity.
    Produces mco.event.decision (promise_commit) and mco.event.anomaly (promise_risk).''',
    tools=[publish_cloudevent, fetch_cloudevent, fetch_inventory_position, fetch_demand_forecast_signal],
    verbose=True,
    allow_delegation=False
)
