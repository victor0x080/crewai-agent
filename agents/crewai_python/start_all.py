#!/usr/bin/env python3
"""Start all CrewAI agents as separate processes"""
import subprocess
import sys
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("AgentStarter")

# All agent runners
SKILL_AGENTS = ['sda', 'fqa', 'caa']  # Original skill agents
EXTENDED_SKILL_AGENTS = ['ssa', 'ira', 'opt', 'asa']  # Extended with simulation integration
DEMAND_GEN_AGENTS = ['marketing_plan', 'sales_pipeline', 'elasticity', 'campaign_sku']
INTEROP_AGENTS = ['forecast_fusion', 'sop', 'risk_twin']
SUPPLY_CHAIN_AGENTS = ['inventory_pos', 'capacity', 'supply_plan', 'production', 'procurement', 'logistics', 'atp_ctp']
GOVERNANCE_AGENTS = ['constraint_broadcast', 'price_guardrail', 'policy_elicitation', 'data_gap', 'rca']
MCO_AGENTS = [
    'ingress', 'catalog', 'feature', 'attribution', 'opportunity', 'cost',
    'budget', 'bid', 'creative', 'platform', 'qrp', 'validator', 'router',
    'guardrail', 'safeguard', 'gap', 'policy', 'experiment', 'rca', 'triage', 'translator'
]

processes = []

def start_agents():
    """Start all agents as background processes"""
    logger.info("Starting all CrewAI agents...")
    
    # Start original skill agents
    for agent in SKILL_AGENTS:
        logger.info(f"Starting skill agent: {agent}")
        proc = subprocess.Popen(['python', 'runners/skill_runners.py', agent])
        processes.append(proc)
    
    # Start extended skill agents (with simulation integration)
    for agent in EXTENDED_SKILL_AGENTS:
        logger.info(f"Starting extended skill agent: {agent}")
        proc = subprocess.Popen(['python', 'runners/extended_runners.py', agent])
        processes.append(proc)
    
    # Start demand-gen agents
    for agent in DEMAND_GEN_AGENTS:
        logger.info(f"Starting demand-gen agent: {agent}")
        proc = subprocess.Popen(['python', 'runners/extended_runners.py', agent])
        processes.append(proc)
    
    # Start interop/consensus agents
    for agent in INTEROP_AGENTS:
        logger.info(f"Starting interop agent: {agent}")
        proc = subprocess.Popen(['python', 'runners/extended_runners.py', agent])
        processes.append(proc)
    
    # Start supply chain agents
    for agent in SUPPLY_CHAIN_AGENTS:
        logger.info(f"Starting supply chain agent: {agent}")
        proc = subprocess.Popen(['python', 'runners/extended_runners.py', agent])
        processes.append(proc)
    
    # Start governance agents
    for agent in GOVERNANCE_AGENTS:
        logger.info(f"Starting governance agent: {agent}")
        proc = subprocess.Popen(['python', 'runners/governance_runners.py', agent])
        processes.append(proc)
    
    # Start MCO agents
    for agent in MCO_AGENTS:
        logger.info(f"Starting MCO agent: {agent}")
        proc = subprocess.Popen(['python', 'runners/mco_runners.py', agent])
        processes.append(proc)
    
    logger.info(f"Started {len(processes)} agents")
    logger.info("Press Ctrl+C to stop all agents")
    
    try:
        for proc in processes:
            proc.wait()
    except KeyboardInterrupt:
        logger.info("Stopping all agents...")
        for proc in processes:
            proc.terminate()
        logger.info("All agents stopped")

if __name__ == '__main__':
    start_agents()
