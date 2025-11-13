"""Runners for MCO Agents - Redis Streams consumers"""
import sys
from pathlib import Path
# Add parent directory to path so we can import base_runner
sys.path.insert(0, str(Path(__file__).parent.parent))
from base_runner import AgentRunner
from agents.mco_agents import (
    ingress, catalog, feature_forecast, attribution, opportunity,
    cost_finance, budget_optimizer, bid_target, creative_ops, platform_adapter,
    qrp, validator, semantic_router, guardrail, safeguard, data_gap,
    goal_policy, counterfactual, change_detective, exception_triage, translator
)

# Core Pipeline Runners
ingress_runner = AgentRunner(ingress, 'stream:agent:ingress-normalizer:in', 'stream:agent:ingress-normalizer:out', 'ingress-normalizer', 'ing-1', 'mco.event.observation')
catalog_runner = AgentRunner(catalog, 'stream:agent:catalog-schema:in', 'stream:agent:catalog-schema:out', 'catalog-schema', 'cat-1', 'mco.schema.discovered')
feature_runner = AgentRunner(feature_forecast, 'stream:agent:feature-forecast:in', 'stream:agent:feature-forecast:out', 'feature-forecast', 'feat-1', 'mco.event.observation')
attribution_runner = AgentRunner(attribution, 'stream:agent:attribution-causal:in', 'stream:agent:attribution-causal:out', 'attribution-causal', 'attr-1', 'mco.event.outcome')
opportunity_runner = AgentRunner(opportunity, 'stream:agent:opportunity-scanner:in', 'stream:agent:opportunity-scanner:out', 'opportunity-scanner', 'opp-1', 'mco.event.recommendation')
cost_runner = AgentRunner(cost_finance, 'stream:agent:cost-finance-mapper:in', 'stream:agent:cost-finance-mapper:out', 'cost-finance-mapper', 'cost-1', 'mco.event.observation')
budget_runner = AgentRunner(budget_optimizer, 'stream:agent:budget-optimizer:in', 'stream:agent:budget-optimizer:out', 'budget-optimizer', 'budg-1', 'mco.event.decision')
bid_runner = AgentRunner(bid_target, 'stream:agent:bid-target-setter:in', 'stream:agent:bid-target-setter:out', 'bid-target-setter', 'bid-1', 'mco.event.decision')
creative_runner = AgentRunner(creative_ops, 'stream:agent:creative-ops:in', 'stream:agent:creative-ops:out', 'creative-ops', 'cre-1', 'mco.event.recommendation')
platform_runner = AgentRunner(platform_adapter, 'stream:agent:platform-adapter:in', 'stream:agent:platform-adapter:out', 'platform-adapter', 'plat-1', 'platform.executed')
qrp_runner = AgentRunner(qrp, 'stream:agent:qrp-planner:in', 'stream:agent:qrp-planner:out', 'qrp-planner', 'qrp-1', 'mco.plan.step')

# Integration Wrapper Runners
validator_runner = AgentRunner(validator, 'stream:agent:validator-registry:in', 'stream:agent:validator-registry:out', 'validator-registry', 'val-1', 'mco.validation.result')
router_runner = AgentRunner(semantic_router, 'stream:agent:semantic-router:in', 'stream:agent:semantic-router:out', 'semantic-router', 'rtr-1', 'route.decision')
guardrail_runner = AgentRunner(guardrail, 'stream:agent:guardrail-compliance:in', 'stream:agent:guardrail-compliance:out', 'guardrail-compliance', 'grd-1', 'mco.event.decision')
safeguard_runner = AgentRunner(safeguard, 'stream:agent:safeguard-rollback:in', 'stream:agent:safeguard-rollback:out', 'safeguard-rollback', 'sfg-1', 'mco.event.decision')
gap_runner = AgentRunner(data_gap, 'stream:agent:data-gap-mapping:in', 'stream:agent:data-gap-mapping:out', 'data-gap-mapping', 'gap-1', 'mco.gap.identified')
policy_runner = AgentRunner(goal_policy, 'stream:agent:goal-policy:in', 'stream:agent:goal-policy:out', 'goal-policy', 'pol-1', 'mco.event.recommendation')
experiment_runner = AgentRunner(counterfactual, 'stream:agent:counterfactual-experiment:in', 'stream:agent:counterfactual-experiment:out', 'counterfactual-experiment', 'exp-1', 'mco.event.recommendation')
rca_runner = AgentRunner(change_detective, 'stream:agent:change-detective-rca:in', 'stream:agent:change-detective-rca:out', 'change-detective-rca', 'rca-1', 'mco.event.outcome')
triage_runner = AgentRunner(exception_triage, 'stream:agent:exception-triage:in', 'stream:agent:exception-triage:out', 'exception-triage', 'tri-1', 'mco.event.escalation')
translator_runner = AgentRunner(translator, 'stream:agent:translator-contract:in', 'stream:agent:translator-contract:out', 'translator-contract', 'trn-1', 'mco.event.observation')

if __name__ == '__main__':
    import logging
    logging.basicConfig(level=logging.INFO)
    
    runners = {
        'ingress': ingress_runner, 'catalog': catalog_runner, 'feature': feature_runner,
        'attribution': attribution_runner, 'opportunity': opportunity_runner, 'cost': cost_runner,
        'budget': budget_runner, 'bid': bid_runner, 'creative': creative_runner,
        'platform': platform_runner, 'qrp': qrp_runner, 'validator': validator_runner,
        'router': router_runner, 'guardrail': guardrail_runner, 'safeguard': safeguard_runner,
        'gap': gap_runner, 'policy': policy_runner, 'experiment': experiment_runner,
        'rca': rca_runner, 'triage': triage_runner, 'translator': translator_runner
    }
    
    if len(sys.argv) < 2:
        print(f"Usage: python mco_runners.py <agent_name>")
        print(f"Available: {', '.join(runners.keys())}")
        sys.exit(1)
    
    runners[sys.argv[1]].run()
