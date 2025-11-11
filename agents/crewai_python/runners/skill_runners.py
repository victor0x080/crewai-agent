"""Runners for Skill Agents - Redis Streams consumers"""
import sys
from pathlib import Path
# Add parent directory to path so we can import base_runner
sys.path.insert(0, str(Path(__file__).parent.parent))
from base_runner import AgentRunner
from agents.skill_agents import sda, fqa, caa, ssa, ira, opt, asa, marketing_plan, sales_pipeline, elasticity, campaign_sku_mapper

# SDA Runner
sda_runner = AgentRunner(
    agent=sda,
    input_stream='stream:agent:sda:in',
    output_stream='stream:agent:sda:out',
    group='sda-semantic-data',
    name='sda-1',
    output_type='mco.event.observation'
)

# FQA Runner
fqa_runner = AgentRunner(
    agent=fqa,
    input_stream='stream:agent:fqa:in',
    output_stream='stream:agent:fqa:out',
    group='fqa-forecast-qa',
    name='fqa-1',
    output_type='mco.event.observation'
)

# CAA Runner
caa_runner = AgentRunner(
    agent=caa,
    input_stream='stream:agent:caa:in',
    output_stream='stream:agent:caa:out',
    group='caa-causal',
    name='caa-1',
    output_type='mco.event.outcome'
)

# SSA Runner
ssa_runner = AgentRunner(
    agent=ssa,
    input_stream='stream:agent:ssa:in',
    output_stream='stream:agent:ssa:out',
    group='ssa-simulator',
    name='ssa-1',
    output_type='mco.event.recommendation'
)

# IRA Runner
ira_runner = AgentRunner(
    agent=ira,
    input_stream='stream:agent:ira:in',
    output_stream='stream:agent:ira:out',
    group='ira-inventory-risk',
    name='ira-1',
    output_type='mco.event.recommendation'
)

# OPT Runner
opt_runner = AgentRunner(
    agent=opt,
    input_stream='stream:agent:opt:in',
    output_stream='stream:agent:opt:out',
    group='opt-optimizer',
    name='opt-1',
    output_type='mco.event.decision'
)

# ASA Runner
asa_runner = AgentRunner(
    agent=asa,
    input_stream='stream:agent:asa:in',
    output_stream='stream:agent:asa:out',
    group='asa-answer-synthesis',
    name='asa-1',
    output_type='mco.event.answer'
)

# Marketing Plan Runner
marketing_runner = AgentRunner(
    agent=marketing_plan,
    input_stream='stream:agent:marketing-plan:in',
    output_stream='stream:agent:marketing-plan:out',
    group='marketing-plan',
    name='mkt-1',
    output_type='mco.event.recommendation'
)

# Sales Pipeline Runner
sales_runner = AgentRunner(
    agent=sales_pipeline,
    input_stream='stream:agent:sales-pipeline:in',
    output_stream='stream:agent:sales-pipeline:out',
    group='sales-pipeline',
    name='sales-1',
    output_type='mco.event.observation'
)

# Elasticity Runner
elasticity_runner = AgentRunner(
    agent=elasticity,
    input_stream='stream:agent:elasticity-uplift:in',
    output_stream='stream:agent:elasticity-uplift:out',
    group='elasticity-uplift',
    name='elast-1',
    output_type='mco.event.recommendation'
)

# Campaign-SKU Mapper Runner
mapper_runner = AgentRunner(
    agent=campaign_sku_mapper,
    input_stream='stream:agent:campaign-sku-mapper:in',
    output_stream='stream:agent:campaign-sku-mapper:out',
    group='campaign-sku-mapper',
    name='mapper-1',
    output_type='mco.event.recommendation'
)

if __name__ == '__main__':
    import sys
    import logging
    logging.basicConfig(level=logging.INFO)
    
    runner_map = {
        'sda': sda_runner,
        'fqa': fqa_runner,
        'caa': caa_runner,
        'ssa': ssa_runner,
        'ira': ira_runner,
        'opt': opt_runner,
        'asa': asa_runner,
        'marketing': marketing_runner,
        'sales': sales_runner,
        'elasticity': elasticity_runner,
        'mapper': mapper_runner
    }
    
    if len(sys.argv) < 2:
        print(f"Usage: python skill_runners.py <agent_name>")
        print(f"Available: {', '.join(runner_map.keys())}")
        sys.exit(1)
    
    agent_name = sys.argv[1]
    if agent_name not in runner_map:
        print(f"Unknown agent: {agent_name}")
        sys.exit(1)
    
    runner_map[agent_name].run()
