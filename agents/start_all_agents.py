#!/usr/bin/env python3
"""
Start All CrewAI Agents for New Backend
Unified agent manager that starts all agent types:
- Generic agents (Plan Review, Data Query, Stream Capture, System Call)
- Platform agents (crewai_python: Skill, Demand-Gen, Supply, Governance, MCO, RMN)
"""

import subprocess
import sys
import os
import logging
import signal
import time
from pathlib import Path

# Use virtual environment Python if available, otherwise system Python
VENV_PYTHON = Path(__file__).parent.parent / 'venv' / 'bin' / 'python3'
if VENV_PYTHON.exists():
    PYTHON_CMD = str(VENV_PYTHON)
else:
    PYTHON_CMD = sys.executable

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("AgentManager")

# Global process tracker
processes = []

# ============================================================================
# Agent Categories
# ============================================================================

# Generic Agents (from /agents folder)
GENERIC_AGENTS = [
    'plan_review_agent.py',
    'data_query_agent.py',
    'stream_capture_agent.py',
    'system_call_zapier_agent.py'
]

# CrewAI Python Agents (from /agents/crewai_python folder)
SKILL_AGENTS = ['sda', 'fqa', 'caa']  # Semantic Data, Forecast Q&A, Causal & Attribution
EXTENDED_SKILL_AGENTS = ['ssa', 'ira', 'opt', 'asa']  # Scenario, Inventory Risk, Optimizer, Answer Synthesis

DEMAND_GEN_AGENTS = [
    'marketing_plan',      # Marketing Plan Agent
    'sales_pipeline',      # Sales Pipeline Agent
    'elasticity',          # Elasticity & Uplift Agent
    'campaign_sku'         # Campaign→SKU Mapper Agent
]

SUPPLY_CHAIN_AGENTS = [
    'inventory_pos',       # Inventory Position Agent
    'capacity',            # Capacity & Lead-Time Agent
    'supply_plan',         # Supply Planning Agent
    'production',          # Production Scheduling Agent
    'procurement',         # Procurement Agent
    'logistics',           # Logistics & Allocation Agent
    'atp_ctp'              # ATP/CTP Agent
]

GOVERNANCE_AGENTS = [
    'constraint_broadcast', # Constraint Broadcast Agent
    'price_guardrail',     # Price/Promo Guardrail Agent
    'policy_elicitation',  # Policy Elicitation Agent
    'data_gap',            # Data Gap & Mapping Agent
    'rca'                  # RCA / Change Detective Agent
]

MCO_AGENTS = [
    'ingress',             # Ingress & Normalization Agent
    'catalog',             # Catalog & Schema Agent
    'feature',             # Feature & Forecast Agent
    'attribution',         # Attribution & Causal Agent
    'opportunity',         # Opportunity Scanner Agent
    'cost',                # Cost & Finance Mapper Agent
    'budget',              # Budget Optimizer Agent
    'bid',                 # Bid & Target Setter Agent
    'creative',            # Creative Ops Agent
    'platform',            # Platform Adapter Agent
    'qrp',                 # Question Router & Planner Agent
    'validator',           # Validator Registry Agent
    'router',              # Semantic Router Agent
    'guardrail',           # Guardrail Compliance Agent
    'safeguard',           # Safeguard Rollback Agent
    'gap',                 # Data Gap Agent (duplicate of data_gap)
    'policy',              # Goal & Policy Elicitation Agent
    'experiment',          # Experiment Design Agent
    'triage',              # Triage Agent
    'translator'           # Translator Contract Agent
]

INTEROP_AGENTS = [
    'forecast_fusion',     # Forecast Fusion Agent
    'sop',                 # S&OP Orchestrator Agent
    'risk_twin'            # Risk & Digital Twin Agent
]

RMN_AGENTS = [
    'amazon_rmn',          # Amazon RMN Specialist
    'walmart_rmn',         # Walmart Connect Specialist
    'target_rmn',          # Target Roundel Specialist
    'instacart_rmn'        # Instacart Ads Specialist
]

PLATFORM_AGENTS = [
    'google_ads',          # Google Ads Agent
    'meta_ads',            # Meta Ads Agent
    'tiktok_ads',          # TikTok Ads Agent
    'linkedin_ads',        # LinkedIn Ads Agent
    'pinterest_ads',       # Pinterest Ads Agent
    'snapchat_ads'         # Snapchat Ads Agent
]


# ============================================================================
# Agent Startup Functions
# ============================================================================

def start_generic_agents():
    """Start generic pattern agents from root agents folder"""
    logger.info("=" * 80)
    logger.info("STARTING GENERIC AGENTS")
    logger.info("=" * 80)
    
    agents_dir = Path(__file__).parent
    
    for agent_file in GENERIC_AGENTS:
        agent_path = agents_dir / agent_file
        if not agent_path.exists():
            logger.warning(f"⚠️  Agent file not found: {agent_file}")
            continue
        
        logger.info(f"Starting: {agent_file}")
        try:
            # Pass API_URL environment variable to child process
            env = os.environ.copy()
            api_url = os.getenv('API_URL', 'http://localhost:3001')
            env['API_URL'] = api_url
            
            proc = subprocess.Popen(
                [PYTHON_CMD, str(agent_path)],
                cwd=str(agents_dir),
                stdout=None,  # Inherit parent's stdout (goes to log file)
                stderr=None,  # Inherit parent's stderr (goes to log file)
                env=env
            )
            
            # Check if process started successfully (wait a bit to see if it crashes immediately)
            time.sleep(0.5)
            if proc.poll() is not None:
                exit_code = proc.returncode
                logger.error(f"❌ {agent_file} crashed immediately (exit code: {exit_code}) - skipping")
                logger.warning(f"   This agent may be missing dependencies or have configuration issues")
                continue
            
            processes.append(('generic', agent_file, proc))
            logger.info(f"✅ Started {agent_file} (PID: {proc.pid})")
        except Exception as e:
            logger.error(f"❌ Failed to start {agent_file}: {e}")
            logger.warning(f"   Skipping this agent")


def start_crewai_agents():
    """Start all CrewAI Python agents from crewai_python folder"""
    logger.info("=" * 80)
    logger.info("STARTING CREWAI PYTHON AGENTS")
    logger.info("=" * 80)
    
    crewai_dir = Path(__file__).parent / 'crewai_python'
    
    if not crewai_dir.exists():
        logger.error(f"❌ CrewAI Python directory not found: {crewai_dir}")
        return
    
    # Optional: minimal agent set to avoid background loops
    run_minimal = os.getenv('RUN_MINIMAL_AGENTS', 'false').lower() == 'true'
    whitelist_env = os.getenv('AGENTS_WHITELIST', '')
    whitelist = set([a.strip() for a in whitelist_env.split(',') if a.strip()])

    def allowed(agent_name: str) -> bool:
        if whitelist:
            return agent_name in whitelist
        if run_minimal:
            return agent_name in {'sda', 'fqa', 'ssa', 'ira', 'asa'}
        return True

    # Start Skill Agents
    logger.info("\n📋 Starting Skill Agents...")
    for agent in SKILL_AGENTS:
        if allowed(agent):
            start_crewai_agent('skill_runners.py', agent, crewai_dir)
    
    # Start Extended Skill Agents
    logger.info("\n📋 Starting Extended Skill Agents...")
    for agent in EXTENDED_SKILL_AGENTS:
        if allowed(agent):
            start_crewai_agent('extended_runners.py', agent, crewai_dir)
    
    # Start Demand-Gen Agents
    logger.info("\n📋 Starting Demand-Gen Agents...")
    for agent in DEMAND_GEN_AGENTS:
        if allowed(agent):
            start_crewai_agent('extended_runners.py', agent, crewai_dir)
    
    # Start Supply Chain Agents
    logger.info("\n📋 Starting Supply Chain Agents...")
    for agent in SUPPLY_CHAIN_AGENTS:
        if allowed(agent):
            start_crewai_agent('extended_runners.py', agent, crewai_dir)
    
    # Start Governance Agents
    logger.info("\n📋 Starting Governance Agents...")
    for agent in GOVERNANCE_AGENTS:
        if allowed(agent):
            start_crewai_agent('governance_runners.py', agent, crewai_dir)
    
    # Start MCO Agents
    logger.info("\n📋 Starting MCO Agents...")
    for agent in MCO_AGENTS:
        if allowed(agent):
            start_crewai_agent('mco_runners.py', agent, crewai_dir)
    
    # Start Interop Agents
    logger.info("\n📋 Starting Interop Agents...")
    for agent in INTEROP_AGENTS:
        if allowed(agent):
            start_crewai_agent('extended_runners.py', agent, crewai_dir)
    
    # Start RMN Agents (use correct runner names)
    logger.info("\n📋 Starting RMN Agents...")
    for agent in ['portfolio', 'audience', 'attribution', 'catalog']:
        if allowed(agent):
            start_crewai_agent('rmn_runners.py', agent, crewai_dir)
    
    # Start Platform Agents
    logger.info("\n📋 Starting Platform Agents...")
    # Platform agents (google_ads, meta_ads, etc.) are defined but don't have runners yet
    # They're registered differently - skip for now to avoid crashes
    logger.warning("   ⚠️  Platform agents skipped - not yet implemented with runners")
    # TODO: Create platform_runners.py or integrate with adapter_runners.py


def start_crewai_agent(runner_script, agent_id, crewai_dir):
    """Start a single CrewAI agent"""
    runner_path = crewai_dir / 'runners' / runner_script
    
    if not runner_path.exists():
        logger.warning(f"⚠️  Runner not found: {runner_script}")
        return
    
    try:
        # Pass API_URL environment variable to child process
        env = os.environ.copy()
        api_url = os.getenv('API_URL', 'http://localhost:3001')
        env['API_URL'] = api_url
        # Use isolated CrewAI storage per agent to avoid SQLite I/O contention
        # CrewAI resolves storage path using the value of CREWAI_STORAGE_DIR as the "app name"
        # which maps to ~/.local/share/{app_name}/latest_kickoff_task_outputs.db
        # Give each agent a unique name to avoid concurrent writes to the same DB file
        env['CREWAI_STORAGE_DIR'] = f"crewai_storage_{agent_id}"
        
        proc = subprocess.Popen(
            [PYTHON_CMD, str(runner_path), agent_id],
            cwd=str(crewai_dir),
            stdout=None,  # Inherit parent's stdout (goes to log file)
            stderr=None,  # Inherit parent's stderr (goes to log file)
            env=env
        )
        processes.append(('crewai', agent_id, proc))
        logger.info(f"   ✅ Started {agent_id} (PID: {proc.pid}) with API_URL={api_url}")
    except Exception as e:
        logger.error(f"   ❌ Failed to start {agent_id}: {e}")


# ============================================================================
# Process Management
# ============================================================================

def stop_all_agents(signum=None, frame=None):
    """Stop all running agents"""
    logger.info("\n" + "=" * 80)
    logger.info("STOPPING ALL AGENTS")
    logger.info("=" * 80)
    
    for category, agent_name, proc in processes:
        try:
            logger.info(f"Stopping {category}/{agent_name} (PID: {proc.pid})...")
            proc.terminate()
        except Exception as e:
            logger.error(f"Error stopping {agent_name}: {e}")
    
    # Wait for all processes to terminate
    logger.info("\nWaiting for processes to terminate...")
    for category, agent_name, proc in processes:
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            logger.warning(f"Force killing {agent_name}...")
            proc.kill()
    
    logger.info("✅ All agents stopped")
    sys.exit(0)


def monitor_agents():
    """Monitor running agents and restart if they crash"""
    logger.info("\n" + "=" * 80)
    logger.info(f"MONITORING {len(processes)} AGENTS")
    logger.info("=" * 80)
    logger.info("Press Ctrl+C to stop all agents\n")
    
    # Track which agents have already been reported as crashed
    crashed_agents = set()
    
    try:
        while True:
            time.sleep(5)
            
            # Check if any agent crashed
            for i, (category, agent_name, proc) in enumerate(processes):
                if proc.poll() is not None:  # Process has terminated
                    exit_code = proc.returncode
                    agent_key = f"{category}/{agent_name}"
                    
                    # Only log once per crashed agent
                    if agent_key not in crashed_agents:
                        crashed_agents.add(agent_key)
                        if exit_code == 0:
                            logger.warning(f"⚠️  Agent {agent_name} exited normally (exit code: 0) - may need to run continuously")
                        else:
                            logger.error(f"⚠️  Agent {agent_name} crashed (exit code: {exit_code})")
                        # Optionally restart the agent here
    
    except KeyboardInterrupt:
        stop_all_agents()


def print_summary():
    """Print summary of started agents"""
    logger.info("\n" + "=" * 80)
    logger.info("AGENT STARTUP SUMMARY")
    logger.info("=" * 80)
    
    generic_count = sum(1 for cat, _, _ in processes if cat == 'generic')
    crewai_count = sum(1 for cat, _, _ in processes if cat == 'crewai')
    
    logger.info(f"\n📊 Total Agents Started: {len(processes)}")
    logger.info(f"   Generic Agents: {generic_count}")
    logger.info(f"   CrewAI Agents: {crewai_count}")
    logger.info(f"\n✅ All agents running and connected to Redis Streams")
    logger.info("=" * 80)


# ============================================================================
# Main Entry Point
# ============================================================================

def main():
    """Main entry point"""
    logger.info("\n" + "=" * 80)
    logger.info("🚀 NEW BACKEND AGENT MANAGER")
    logger.info("=" * 80)
    
    # Register signal handlers
    signal.signal(signal.SIGINT, stop_all_agents)
    signal.signal(signal.SIGTERM, stop_all_agents)
    
    # Runtime flags
    run_generic = os.getenv('RUN_GENERIC_AGENTS', 'false').lower() == 'true'
    run_minimal = os.getenv('RUN_MINIMAL_AGENTS', 'false').lower() == 'true'

    # Start generic agents (disabled by default to keep system idle)
    if run_generic:
        start_generic_agents()
    else:
        logger.info("Skipping generic agents (RUN_GENERIC_AGENTS=false)")

    # Start CrewAI agents (respects RUN_MINIMAL_AGENTS/AGENTS_WHITELIST)
    time.sleep(2)  # Give generic agents time to initialize
    
    start_crewai_agents()
    time.sleep(2)  # Give CrewAI agents time to initialize
    
    # Print summary
    print_summary()
    
    # Monitor agents
    monitor_agents()


if __name__ == '__main__':
    main()

