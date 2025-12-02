"""
Contact Center Coaching Runner
==============================

Runs the Contact Center Coaching CrewAI manager service.
Listens on Redis Stream for route decisions and provides real-time coaching.
"""

import os
import sys
import logging
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Configure logging
if not logging.getLogger().handlers:
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        force=True
    )

logger = logging.getLogger("Runner.contact_center_coaching")

# Load environment variables from .env file if it exists
try:
    possible_env_paths = [
        Path(__file__).parent.parent.parent / '.env',
        Path(__file__).parent.parent.parent.parent / '.env',
        Path.cwd() / '.env',
        Path.home() / '.env',
    ]
    
    env_file = None
    for path in possible_env_paths:
        if path.exists():
            env_file = path
            break
    
    if env_file:
        logger.info(f"📋 Loading environment from: {env_file}")
        with open(env_file) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    value = value.split('#')[0].strip().strip('"').strip("'")
                    if key.strip() not in os.environ:
                        os.environ[key.strip()] = value
        logger.info(f"✅ Loaded environment variables from .env")
    else:
        logger.warning("⚠️ No .env file found, using system environment variables only")
except Exception as e:
    logger.warning(f"⚠️ Failed to load .env file: {e}")

# Import the crew using importlib to handle hyphenated directory name
import importlib.util

# Load ContactCenterCoachingCrew module (directory has hyphen, can't use normal import)
crew_file = Path(__file__).parent.parent / 'crews' / 'contact-center' / 'ContactCenterCoachingCrew.py'
spec = importlib.util.spec_from_file_location("ContactCenterCoachingCrew", crew_file)
crew_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(crew_module)
build_crew = crew_module.build_crew
build_coaching_manager = crew_module.build_coaching_manager

from CrewAIManagerService import CrewAIManagerService


def main():
    """Main entry point for contact center coaching runner."""
    logger.info("=== Contact Center Real-Time Coaching Crew ===")
    
    try:
        # Build crew
        config, crew = build_crew()
        
        # Get manager agent
        if crew.manager_agent:
            manager = crew.manager_agent
            logger.info(f"Manager: {manager.role} (hierarchical mode)")
            logger.info(f"Worker agents: {len(crew.agents)}")
        else:
            manager = crew.agents[0]
            logger.info(f"Manager: {manager.role} (sequential mode)")
            logger.info(f"Total agents: {len(crew.agents)}")
        
        logger.info(f"Process: {crew.process}")
        logger.info("Agents in crew:")
        for i, agent in enumerate(crew.agents, 1):
            logger.info(f"  {i}. {agent.role}")
        
        # Start service
        logger.info(f"\nStarting Coaching Manager Service...")
        logger.info(f"Route stream: {config.route_stream}")
        
        service = CrewAIManagerService(config, manager, crew)
        
        try:
            service.start()
        except KeyboardInterrupt:
            logger.info("\n\nShutting down...")
            service.stop()
    except Exception as e:
        logger.error(f"❌ Failed to start contact center coaching crew: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()

