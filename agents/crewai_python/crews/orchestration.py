"""Crew Orchestration - Multi-agent workflows"""
from crewai import Crew, Process
from agents.skill_agents import sda, fqa, caa, ssa, ira, opt, asa
from agents.mco_agents import qrp, semantic_router, translator

# Query→Plan→Execute→Answer Crew
query_answer_crew = Crew(
    agents=[qrp, sda, fqa, caa, ssa, ira, opt, asa],
    tasks=[],  # Tasks created dynamically per query
    process=Process.sequential,
    verbose=True
)

# Semantic Routing & Translation Crew
routing_crew = Crew(
    agents=[semantic_router, translator],
    tasks=[],
    process=Process.sequential,
    verbose=True
)

# Full MCO Pipeline Crew (all agents)
from agents.mco_agents import (
    ingress, catalog, feature_forecast, attribution, opportunity,
    cost_finance, budget_optimizer, bid_target, creative_ops, platform_adapter,
    validator, guardrail, safeguard, data_gap, goal_policy,
    counterfactual, change_detective, exception_triage
)

mco_pipeline_crew = Crew(
    agents=[
        ingress, catalog, feature_forecast, attribution, opportunity,
        cost_finance, budget_optimizer, bid_target, creative_ops, platform_adapter,
        qrp, validator, semantic_router, guardrail, safeguard, data_gap,
        goal_policy, counterfactual, change_detective, exception_triage, translator
    ],
    tasks=[],
    process=Process.hierarchical,  # QRP as manager
    manager_agent=qrp,
    verbose=True
)
