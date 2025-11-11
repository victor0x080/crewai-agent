"""
Runners for Governance & Feedback Agents
Constraint Broadcast, Price/Promo Guardrail, Policy Elicitation, Data Gap, RCA
"""
import sys
from pathlib import Path
# Add parent directory to path so we can import base_runner
sys.path.insert(0, str(Path(__file__).parent.parent))
from base_runner import AgentRunner
from agents.governance_agents import (
    constraint_broadcast_agent,
    price_promo_guardrail_agent,
    policy_elicitation_agent,
    data_gap_mapping_agent,
    rca_change_detective_agent
)

# ============================================================================
# CONSTRAINT FEEDBACK RUNNERS (Supply → Demand-Gen)
# ============================================================================

# Constraint Broadcast Runner
constraint_broadcast_runner = AgentRunner(
    agent=constraint_broadcast_agent,
    input_stream='stream:agent:constraint-broadcast:in',
    output_stream='stream:agent:constraint-broadcast:out',
    group='constraint-broadcast',
    name='constraint-1',
    output_type='mco.event.recommendation'
)

# Price/Promo Guardrail Runner
price_promo_guardrail_runner = AgentRunner(
    agent=price_promo_guardrail_agent,
    input_stream='stream:agent:price-promo-guardrail:in',
    output_stream='stream:agent:price-promo-guardrail:out',
    group='price-promo-guardrail',
    name='guardrail-1',
    output_type='mco.event.audit'
)

# ============================================================================
# HUMAN-IN-LOOP / GOVERNANCE RUNNERS
# ============================================================================

# Policy Elicitation Runner
policy_elicitation_runner = AgentRunner(
    agent=policy_elicitation_agent,
    input_stream='stream:agent:policy-elicitation:in',
    output_stream='stream:agent:policy-elicitation:out',
    group='policy-elicitation',
    name='policy-1',
    output_type='mco.event.audit'
)

# Data Gap & Mapping Runner
data_gap_mapping_runner = AgentRunner(
    agent=data_gap_mapping_agent,
    input_stream='stream:agent:data-gap-mapping:in',
    output_stream='stream:agent:data-gap-mapping:out',
    group='data-gap-mapping',
    name='gap-1',
    output_type='mco.event.anomaly'
)

# RCA / Change Detective Runner
rca_change_detective_runner = AgentRunner(
    agent=rca_change_detective_agent,
    input_stream='stream:agent:rca-change-detective:in',
    output_stream='stream:agent:rca-change-detective:out',
    group='rca-change-detective',
    name='rca-1',
    output_type='mco.event.recommendation'
)

# ============================================================================
# MAIN ENTRY POINT
# ============================================================================

if __name__ == '__main__':
    import logging
    logging.basicConfig(level=logging.INFO)
    
    runners = {
        # Constraint Feedback
        'constraint_broadcast': constraint_broadcast_runner,
        'price_guardrail': price_promo_guardrail_runner,
        # Human-in-Loop / Governance
        'policy_elicitation': policy_elicitation_runner,
        'data_gap': data_gap_mapping_runner,
        'rca': rca_change_detective_runner
    }
    
    if len(sys.argv) < 2:
        print(f"Usage: python governance_runners.py <agent_name>")
        print(f"Available agents:")
        print(f"  Constraint Feedback: constraint_broadcast, price_guardrail")
        print(f"  Governance: policy_elicitation, data_gap, rca")
        sys.exit(1)
    
    agent_name = sys.argv[1]
    if agent_name not in runners:
        print(f"Unknown agent: {agent_name}")
        sys.exit(1)
    
    runners[agent_name].run()
