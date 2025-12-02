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

GROWTH_PLAN_AGENTS = [
    # Removed: tenmilliondollargrowthplan
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
    
    # Start conversational agent
    logger.info("\n📋 Starting Conversational Agent...")
    start_conversational_agent(crewai_dir)
    
    # Start contact center coaching crew
    logger.info("\n📋 Starting Contact Center Coaching Crew...")
    start_contact_center_coaching_crew(crewai_dir)
    
    # All other agents are disabled - only conversational and coaching agents run
    logger.info("\n⚠️  All other agents disabled - only conversational and coaching agents are running")


def start_conversational_agent(crewai_dir):
    """Start the conversational CrewAI agent"""
    runner_path = crewai_dir / 'runners' / 'conversational_runner.py'
    
    if not runner_path.exists():
        logger.error(f"❌ Conversational runner not found: {runner_path}")
        return
    
    try:
        # Pass API_URL environment variable to child process
        env = os.environ.copy()
        api_url = os.getenv('API_URL', 'http://localhost:3001')
        env['API_URL'] = api_url
        # Use isolated CrewAI storage for conversational agent
        env['CREWAI_STORAGE_DIR'] = 'crewai_storage_conversational'
        
        proc = subprocess.Popen(
            [PYTHON_CMD, str(runner_path)],
            cwd=str(crewai_dir),
            stdout=None,  # Inherit parent's stdout (goes to log file)
            stderr=None,  # Inherit parent's stderr (goes to log file)
            env=env
        )
        
        # Check if process started successfully
        time.sleep(0.5)
        if proc.poll() is not None:
            exit_code = proc.returncode
            logger.error(f"❌ Conversational agent crashed immediately (exit code: {exit_code})")
            return
        
        processes.append(('crewai', 'conversational', proc))
        logger.info(f"   ✅ Started conversational agent (PID: {proc.pid}) with API_URL={api_url}")
        logger.info(f"   📡 Listening on stream: stream:agent:conversational:in")
    except Exception as e:
        logger.error(f"   ❌ Failed to start conversational agent: {e}")


def start_contact_center_coaching_crew(crewai_dir):
    """Start the contact center coaching CrewAI crew"""
    runner_path = crewai_dir / 'runners' / 'contact_center_coaching_runner.py'
    
    if not runner_path.exists():
        logger.error(f"❌ Contact center coaching runner not found: {runner_path}")
        return
    
    try:
        # Pass API_URL environment variable to child process
        env = os.environ.copy()
        api_url = os.getenv('API_URL', 'http://localhost:3001')
        env['API_URL'] = api_url
        # Use isolated CrewAI storage for coaching crew
        env['CREWAI_STORAGE_DIR'] = 'crewai_storage_coaching'
        
        proc = subprocess.Popen(
            [PYTHON_CMD, str(runner_path)],
            cwd=str(crewai_dir),
            stdout=None,  # Inherit parent's stdout (goes to log file)
            stderr=None,  # Inherit parent's stderr (goes to log file)
            env=env
        )
        
        # Check if process started successfully
        time.sleep(0.5)
        if proc.poll() is not None:
            exit_code = proc.returncode
            logger.error(f"❌ Contact center coaching crew crashed immediately (exit code: {exit_code})")
            return
        
        processes.append(('crewai', 'contact_center_coaching', proc))
        logger.info(f"   ✅ Started contact center coaching crew (PID: {proc.pid}) with API_URL={api_url}")
        logger.info(f"   📡 Listening on stream: stream:route.decisions:coaching-manager")
    except Exception as e:
        logger.error(f"   ❌ Failed to start contact center coaching crew: {e}")


def start_crewai_agent(runner_script, agent_id, crewai_dir):
    """Start a single CrewAI agent (disabled - only conversational and coaching agents run)"""
    # This function is kept for compatibility but not used
    pass


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
    
    # Only start conversational agent - all other agents disabled
    logger.info("Starting only conversational agent (all other agents disabled)")
    
    # Skip generic agents
    logger.info("Skipping generic agents")
    
    # Start only conversational agent
    start_crewai_agents()
    time.sleep(2)  # Give conversational agent time to initialize
    
    # Print summary
    print_summary()
    
    # Monitor agents
    monitor_agents()


if __name__ == '__main__':
    main()

