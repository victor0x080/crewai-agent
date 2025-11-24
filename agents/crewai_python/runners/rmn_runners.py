"""
RMN Agent Runners
Runs the 4 RMN-specific agents with Redis Streams integration
"""
import sys
import logging
from pathlib import Path
# Add parent directory to path so we can import modules
sys.path.insert(0, str(Path(__file__).parent.parent))
from base_runner import AgentRunner
from crewai import Task, Crew, Process
from agents.rmn_agents import (
    rmn_portfolio_optimizer,
    rmn_audience_sync,
    rmn_attribution,
    rmn_catalog_sync
)
# Walmart agents removed
walmart_strategies_agent = None

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def rmn_portfolio_optimizer_runner():
    """
    RMN Portfolio Optimizer Runner
    
    Consumes: stream:mco:event:performance (from all RMN platforms)
    Produces: stream:mco:event:action (budget reallocation actions)
    
    Logic:
    1. Aggregate performance across RMNs (Amazon, Walmart, Target, Instacart, etc.)
    2. Calculate ROAS, incrementality, and efficiency metrics per platform
    3. Optimize budget allocation to maximize total portfolio ROAS
    4. Publish budget reallocation actions to each platform
    """
    logger.info("Starting RMN Portfolio Optimizer runner")
    
    task = Task(
        description="""
        Analyze performance data from all RMN platforms (Amazon, Walmart, Target, Instacart, etc.).
        Calculate ROAS and incrementality per platform.
        Optimize budget allocation to maximize total portfolio ROAS subject to constraints:
        - Minimum budget per platform
        - Maximum budget per platform
        - Total budget constraint
        - ROAS targets per platform
        
        For each reallocation decision, publish a setCampaignBudget action to the appropriate
        platform adapter using publish_platform_action tool.
        
        Input: Performance CloudEvents from stream:mco:event:performance
        Output: Budget reallocation actions to stream:mco:event:action
        """,
        expected_output="Budget reallocation actions published to all RMN platforms",
        agent=rmn_portfolio_optimizer
    )
    
    crew = Crew(
        agents=[rmn_portfolio_optimizer],
        tasks=[task],
        process=Process.sequential,
        verbose=True
    )
    
    # In production, this would consume from Redis Streams
    # For now, run with sample inputs
    result = crew.kickoff(inputs={
        'platforms': ['amazon', 'walmart-connect', 'target-roundel', 'instacart'],
        'total_budget': 100000,
        'target_roas': 4.0
    })
    
    logger.info(f"RMN Portfolio Optimizer result: {result}")
    return result


def rmn_audience_sync_runner():
    """
    RMN Audience Sync Runner
    
    Consumes: stream:mco:event:audience (unified audience definitions)
    Produces: stream:mco:event:action (audience targeting actions)
    
    Logic:
    1. Receive unified audience segment definition
    2. Map to platform-specific audience types:
       - Amazon: AMC audiences, in-market segments
       - Walmart: Walmart+ members, in-store shoppers
       - Target: RedCard holders, Circle members
       - Instacart: rapid delivery users
    3. Publish updateAudienceTargeting actions to each platform
    """
    logger.info("Starting RMN Audience Sync runner")
    
    task = Task(
        description="""
        Receive unified audience segment definition with semantic labels.
        Use ontology to map audience types to platform-specific targeting:
        
        Example mappings:
        - 'premium_member' → Walmart+ (Walmart), RedCard (Target), Prime (Amazon)
        - 'in_store_shopper' → In-store attribution (Walmart), Store proximity (Target)
        - 'rapid_delivery' → Same-day delivery (Target), 30-min delivery (Instacart)
        
        For each platform, publish updateAudienceTargeting action using publish_platform_action tool.
        
        Input: Audience CloudEvents from stream:mco:event:audience
        Output: Audience targeting actions to stream:mco:event:action
        """,
        expected_output="Audience targeting actions published to all RMN platforms",
        agent=rmn_audience_sync
    )
    
    crew = Crew(
        agents=[rmn_audience_sync],
        tasks=[task],
        process=Process.sequential,
        verbose=True
    )
    
    result = crew.kickoff(inputs={
        'audience_segment': 'premium_members',
        'platforms': ['amazon', 'walmart-connect', 'target-roundel']
    })
    
    logger.info(f"RMN Audience Sync result: {result}")
    return result


def rmn_attribution_runner():
    """
    RMN Attribution Runner
    
    Consumes: stream:mco:event:conversion (from all RMN platforms)
    Produces: stream:mco:event:attribution (attribution reports)
    
    Logic:
    1. Collect conversion events from all RMN platforms
    2. Apply platform-specific attribution windows
    3. Calculate multi-touch attribution across platforms
    4. Measure incrementality (test vs. control)
    5. Publish attribution reports
    """
    logger.info("Starting RMN Attribution runner")
    
    task = Task(
        description="""
        Collect conversion events from all RMN platforms.
        Apply platform-specific attribution windows:
        - Amazon: 14-day click, 1-day view
        - Walmart: 30-day click, 7-day view (in-store + online)
        - Target: 14-day click, 1-day view
        - Instacart: 7-day click
        
        Calculate multi-touch attribution using:
        - Last-click attribution
        - Linear attribution
        - Time-decay attribution
        
        Measure incrementality using test/control groups.
        
        Publish attribution reports as CloudEvents to stream:mco:event:attribution.
        
        Input: Conversion CloudEvents from stream:mco:event:conversion
        Output: Attribution reports to stream:mco:event:attribution
        """,
        expected_output="Attribution reports published with incrementality measurements",
        agent=rmn_attribution
    )
    
    crew = Crew(
        agents=[rmn_attribution],
        tasks=[task],
        process=Process.sequential,
        verbose=True
    )
    
    result = crew.kickoff(inputs={
        'time_window': '30d',
        'attribution_model': 'multi_touch',
        'platforms': ['amazon', 'walmart-connect', 'target-roundel', 'instacart']
    })
    
    logger.info(f"RMN Attribution result: {result}")
    return result


def rmn_catalog_sync_runner():
    """
    RMN Product Catalog Sync Runner
    
    Consumes: stream:mco:event:catalog (master product catalog updates)
    Produces: stream:mco:event:action (product feed update actions)
    
    Logic:
    1. Receive master product catalog update
    2. Map SKUs to platform-specific product IDs:
       - Amazon: ASIN
       - Walmart: Item ID
       - Target: TCIN
       - Instacart: Multi-retailer product IDs
    3. Validate product attributes (title, image, price, availability)
    4. Publish product feed update actions
    """
    logger.info("Starting RMN Catalog Sync runner")
    
    task = Task(
        description="""
        Receive master product catalog update with SKU, title, description, image, price, availability.
        
        Map SKU to platform-specific product IDs:
        - Amazon: Look up ASIN via brand registry
        - Walmart: Map to Item ID via UPC
        - Target: Map to TCIN via DPCI
        - Instacart: Map to retailer-specific product IDs
        
        Validate product attributes using ontology constraints:
        - Title length limits
        - Image format/size requirements
        - Price format (currency, decimal places)
        - Availability status enums
        
        Publish product feed update actions (or flag for manual review if mapping fails).
        
        Input: Catalog CloudEvents from stream:mco:event:catalog
        Output: Product feed actions to stream:mco:event:action
        """,
        expected_output="Product feed updates published to all RMN platforms",
        agent=rmn_catalog_sync
    )
    
    crew = Crew(
        agents=[rmn_catalog_sync],
        tasks=[task],
        process=Process.sequential,
        verbose=True
    )
    
    result = crew.kickoff(inputs={
        'sku': 'SKU-12345',
        'title': 'Premium Widget',
        'price': 29.99,
        'platforms': ['amazon', 'walmart-connect', 'target-roundel']
    })
    
    logger.info(f"RMN Catalog Sync result: {result}")
    return result


if __name__ == '__main__':
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python rmn_runners.py <agent_name>")
        print("Available agents: portfolio, audience, attribution, catalog, walmart-rmn")
        sys.exit(1)
    
    agent_name = sys.argv[1]
    
    # Map agent names to agents and streams
    agent_map = {
        'portfolio': (rmn_portfolio_optimizer, 'stream:agent:portfolio:in', 'stream:agent:portfolio:out', 'portfolio'),
        'audience': (rmn_audience_sync, 'stream:agent:audience:in', 'stream:agent:audience:out', 'audience'),
        'attribution': (rmn_attribution, 'stream:agent:attribution:in', 'stream:agent:attribution:out', 'attribution'),
        'catalog': (rmn_catalog_sync, 'stream:agent:catalog:in', 'stream:agent:catalog:out', 'catalog')
    }
    if walmart_strategies_agent is not None:
        agent_map['walmart-rmn'] = (walmart_strategies_agent, 'stream:agent:walmart-rmn:in', 'stream:agent:walmart-rmn:out', 'walmart-rmn')
    
    if agent_name not in agent_map:
        print(f"Unknown agent: {agent_name}")
        print("Available agents: " + ", ".join(agent_map.keys()))
        sys.exit(1)
    
    # Get agent and stream configuration
    agent, input_stream, output_stream, group = agent_map[agent_name]
    
    # Create and run agent runner (continuous loop)
    runner = AgentRunner(
        agent=agent,
        input_stream=input_stream,
        output_stream=output_stream,
        group=group,
        name=f"{group}-1",
        output_type="mco.event.outcome"
    )
    
    # Run continuously
    runner.run()
