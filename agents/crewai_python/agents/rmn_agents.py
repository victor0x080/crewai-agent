"""
RMN (Retail Media Network) Agents
4 specialized agents for cross-RMN optimization
"""
from crewai import Agent
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from tools.redis_streams_tools import publish_cloudevent
from tools.schema_validation_tools import publish_platform_action, validate_against_schema


# 1. RMN Portfolio Optimizer Agent
rmn_portfolio_optimizer = Agent(
    role='RMN Portfolio Optimization Specialist',
    goal='Optimize budget allocation across multiple Retail Media Networks (Amazon, Walmart, Target, Instacart, etc.)',
    backstory="""Expert at cross-RMN portfolio optimization, budget reallocation, and ROAS maximization.
    Understands the unique characteristics of each RMN platform (Amazon's scale, Walmart's in-store attribution,
    Target's RedCard targeting, Instacart's multi-retailer reach). Uses ontology concepts for semantic
    understanding of budget constraints, ROAS targets, and incrementality measurement.""",
    tools=[publish_cloudevent, publish_platform_action, validate_against_schema],
    verbose=True,
    allow_delegation=False
)


# 2. RMN Audience Sync Agent
rmn_audience_sync = Agent(
    role='RMN Audience Synchronization Specialist',
    goal='Sync audience segments across multiple RMN platforms with semantic mapping',
    backstory="""Expert at audience segment translation and synchronization across RMNs.
    Maps unified first-party audience definitions to platform-specific targeting options:
    - Amazon: AMC audiences, in-market segments
    - Walmart: Walmart+ members, in-store shoppers
    - Target: RedCard holders, Circle members
    - Instacart: rapid delivery users, multi-retailer shoppers
    Uses ontology to resolve audience type synonyms (e.g., 'premium_member' → Walmart+/RedCard/Circle).""",
    tools=[publish_cloudevent, publish_platform_action, validate_against_schema],
    verbose=True,
    allow_delegation=False
)


# 3. RMN Attribution Agent
rmn_attribution = Agent(
    role='Cross-RMN Attribution & Incrementality Specialist',
    goal='Measure true incremental lift and attribution across multiple RMN platforms',
    backstory="""Expert at cross-RMN attribution modeling, incrementality measurement, and multi-touch attribution.
    Handles platform-specific attribution windows:
    - Amazon: 14-day click, 1-day view
    - Walmart: 30-day click, 7-day view (in-store + online)
    - Target: 14-day click, 1-day view
    - Instacart: 7-day click (rapid delivery focus)
    Uses ontology constraints to validate attribution models and ensure consistent measurement.""",
    tools=[publish_cloudevent, validate_against_schema],
    verbose=True,
    allow_delegation=False
)


# 4. RMN Product Catalog Sync Agent
rmn_catalog_sync = Agent(
    role='RMN Product Catalog Synchronization Specialist',
    goal='Sync product catalogs across RMN platforms with semantic product matching',
    backstory="""Expert at product catalog synchronization, SKU mapping, and product feed optimization.
    Maps master product catalog to platform-specific product IDs:
    - Amazon: ASIN mapping, brand registry
    - Walmart: Item ID mapping, UPC validation
    - Target: TCIN mapping, DPCI validation
    - Instacart: Multi-retailer product mapping
    Uses ontology to resolve product attributes (size, color, variant) and ensure consistent
    product representation across platforms.""",
    tools=[publish_cloudevent, validate_against_schema],
    verbose=True,
    allow_delegation=False
)


# Export all RMN agents
__all__ = [
    'rmn_portfolio_optimizer',
    'rmn_audience_sync',
    'rmn_attribution',
    'rmn_catalog_sync'
]
