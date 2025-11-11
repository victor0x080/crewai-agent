"""
Runners for Extended Skill Agents + Demand-Gen + Supply Chain
All integrate with simulation processes and demand forecasting signals
"""
import sys
from pathlib import Path
# Add parent directory to path so we can import base_runner
sys.path.insert(0, str(Path(__file__).parent.parent))
from base_runner import AgentRunner
from agents.extended_skill_agents import (
    # Extended Skill Agents
    ssa_simulator, ira_inventory_risk, opt_optimizer, asa_answer_synthesis,
    # Demand-Gen Agents
    marketing_plan_agent, sales_pipeline_agent, elasticity_uplift_agent, campaign_sku_mapper_agent,
    # Interop/Consensus Agents
    forecast_fusion_agent, sop_orchestrator_agent, risk_digital_twin_agent,
    # Demand-Satisfaction Agents
    inventory_position_agent, capacity_leadtime_agent, supply_planning_agent,
    production_scheduling_agent, procurement_agent, logistics_allocation_agent, atp_ctp_agent
)

# ============================================================================
# EXTENDED SKILL AGENT RUNNERS
# ============================================================================

# SSA Runner - Connects to all simulation processes
ssa_runner = AgentRunner(
    agent=ssa_simulator,
    input_stream='stream:agent:ssa:in',  # dedicated per-agent input
    output_stream='stream:agent:ssa:out',
    group='ssa-simulator',
    name='ssa-1',
    output_type='mco.event.recommendation'
)

# IRA Runner - Integrates demand forecast signals
ira_runner = AgentRunner(
    agent=ira_inventory_risk,
    input_stream='stream:agent:ira:in',
    output_stream='stream:agent:ira:out',
    group='ira-inventory-risk',
    name='ira-1',
    output_type='mco.event.recommendation'
)

# OPT Runner - Prescriptive optimization
opt_runner = AgentRunner(
    agent=opt_optimizer,
    input_stream='stream:agent:opt:in',
    output_stream='stream:agent:opt:out',
    group='opt-optimizer',
    name='opt-1',
    output_type='mco.event.decision'
)

# ASA Runner - Final answer synthesis
asa_runner = AgentRunner(
    agent=asa_answer_synthesis,
    input_stream='stream:agent:asa:in',
    output_stream='stream:agent:asa:out',
    group='asa-answer-synthesis',
    name='asa-1',
    output_type='mco.event.answer'
)

# ============================================================================
# DEMAND-GEN AGENT RUNNERS
# ============================================================================

# Marketing Plan Runner
marketing_plan_runner = AgentRunner(
    agent=marketing_plan_agent,
    input_stream='stream:agent:marketing-plan:in',
    output_stream='stream:agent:marketing-plan:out',
    group='marketing-plan',
    name='mkt-plan-1',
    output_type='mco.event.recommendation'
)

# Sales Pipeline Runner
sales_pipeline_runner = AgentRunner(
    agent=sales_pipeline_agent,
    input_stream='stream:agent:sales-pipeline:in',
    output_stream='stream:agent:sales-pipeline:out',
    group='sales-pipeline',
    name='sales-pipe-1',
    output_type='mco.event.observation'
)

# Elasticity & Uplift Runner
elasticity_runner = AgentRunner(
    agent=elasticity_uplift_agent,
    input_stream='stream:agent:elasticity-uplift:in',
    output_stream='stream:agent:elasticity-uplift:out',
    group='elasticity-uplift',
    name='elast-1',
    output_type='mco.event.recommendation'
)

# Campaign→SKU Mapper Runner
campaign_sku_runner = AgentRunner(
    agent=campaign_sku_mapper_agent,
    input_stream='stream:agent:campaign-sku-mapper:in',
    output_stream='stream:agent:campaign-sku-mapper:out',
    group='campaign-sku-mapper',
    name='sku-map-1',
    output_type='mco.event.recommendation'
)

# ============================================================================
# INTEROP/CONSENSUS AGENT RUNNERS
# ============================================================================

# Forecast Fusion Runner
forecast_fusion_runner = AgentRunner(
    agent=forecast_fusion_agent,
    input_stream='stream:agent:forecast-fusion:in',
    output_stream='stream:agent:forecast-fusion:out',
    group='forecast-fusion',
    name='fusion-1',
    output_type='mco.event.decision'
)

# S&OP Orchestrator Runner
sop_runner = AgentRunner(
    agent=sop_orchestrator_agent,
    input_stream='stream:agent:sop:in',
    output_stream='stream:agent:sop:out',
    group='sop-orchestrator',
    name='sop-1',
    output_type='mco.event.decision'
)

# Risk & Digital Twin Runner
risk_twin_runner = AgentRunner(
    agent=risk_digital_twin_agent,
    input_stream='stream:agent:risk-twin:in',
    output_stream='stream:agent:risk-twin:out',
    group='risk-digital-twin',
    name='risk-1',
    output_type='mco.event.anomaly'
)

# ============================================================================
# DEMAND-SATISFACTION AGENT RUNNERS
# ============================================================================

# Inventory Position Runner
inventory_pos_runner = AgentRunner(
    agent=inventory_position_agent,
    input_stream='stream:agent:inventory-position:in',
    output_stream='stream:agent:inventory-position:out',
    group='inventory-position',
    name='inv-pos-1',
    output_type='mco.event.observation'
)

# Capacity & Lead-time Runner
capacity_runner = AgentRunner(
    agent=capacity_leadtime_agent,
    input_stream='stream:agent:capacity-leadtime:in',
    output_stream='stream:agent:capacity-leadtime:out',
    group='capacity-leadtime',
    name='cap-1',
    output_type='mco.event.observation'
)

# Supply Planning Runner
supply_plan_runner = AgentRunner(
    agent=supply_planning_agent,
    input_stream='stream:agent:supply-planning:in',
    output_stream='stream:agent:supply-planning:out',
    group='supply-planning',
    name='supply-1',
    output_type='mco.event.decision'
)

# Production Scheduling Runner
production_runner = AgentRunner(
    agent=production_scheduling_agent,
    input_stream='stream:agent:production-scheduling:in',
    output_stream='stream:agent:production-scheduling:out',
    group='production-scheduling',
    name='prod-1',
    output_type='mco.event.action'
)

# Procurement Runner
procurement_runner = AgentRunner(
    agent=procurement_agent,
    input_stream='stream:agent:procurement:in',
    output_stream='stream:agent:procurement:out',
    group='procurement',
    name='proc-1',
    output_type='mco.event.action'
)

# Logistics & Allocation Runner
logistics_runner = AgentRunner(
    agent=logistics_allocation_agent,
    input_stream='stream:agent:logistics-allocation:in',
    output_stream='stream:agent:logistics-allocation:out',
    group='logistics-allocation',
    name='log-1',
    output_type='mco.event.decision'
)

# ATP/CTP Runner
atp_ctp_runner = AgentRunner(
    agent=atp_ctp_agent,
    input_stream='stream:agent:atp-ctp:in',
    output_stream='stream:agent:atp-ctp:out',
    group='atp-ctp-promise',
    name='atp-1',
    output_type='mco.event.decision'
)

# ============================================================================
# MAIN ENTRY POINT
# ============================================================================

if __name__ == '__main__':
    import logging
    logging.basicConfig(level=logging.INFO)
    
    runners = {
        # Extended Skill
        'ssa': ssa_runner,
        'ira': ira_runner,
        'opt': opt_runner,
        'asa': asa_runner,
        # Demand-Gen
        'marketing_plan': marketing_plan_runner,
        'sales_pipeline': sales_pipeline_runner,
        'elasticity': elasticity_runner,
        'campaign_sku': campaign_sku_runner,
        # Interop/Consensus
        'forecast_fusion': forecast_fusion_runner,
        'sop': sop_runner,
        'risk_twin': risk_twin_runner,
        # Demand-Satisfaction
        'inventory_pos': inventory_pos_runner,
        'capacity': capacity_runner,
        'supply_plan': supply_plan_runner,
        'production': production_runner,
        'procurement': procurement_runner,
        'logistics': logistics_runner,
        'atp_ctp': atp_ctp_runner
    }
    
    if len(sys.argv) < 2:
        print(f"Usage: python extended_runners.py <agent_name>")
        print(f"Available agents:")
        print(f"  Extended Skill: ssa, ira, opt, asa")
        print(f"  Demand-Gen: marketing_plan, sales_pipeline, elasticity, campaign_sku")
        print(f"  Interop: forecast_fusion, sop, risk_twin")
        print(f"  Supply Chain: inventory_pos, capacity, supply_plan, production, procurement, logistics, atp_ctp")
        sys.exit(1)
    
    agent_name = sys.argv[1]
    if agent_name not in runners:
        print(f"Unknown agent: {agent_name}")
        sys.exit(1)
    
    runners[agent_name].run()
