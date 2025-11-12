"""
Advanced Analytics Agents with Multiple Algorithms
Example: Marketing Mix Modeling (MMM) Agent with multiple algorithm tools
"""

from crewai import Agent
from tools.redis_streams_tools import publish_cloudevent, fetch_cloudevent
from tools.algorithm_comparison_tool import compare_algorithm_results, synthesize_multi_algorithm_insights
from factory.algorithm_tool_generator import get_algorithm_tool_generator

# Get algorithm tool generator
algorithm_generator = get_algorithm_tool_generator()

# Generate algorithm tools
robyn_mmm_tool = algorithm_generator.generate_tool_from_algorithm_spec({
    "name": "RobynMMM",
    "parameters": ["sales_data", "spend_data"],
    "outputs": ["roas", "cpa", "optimal_allocation"],
    "description": "Marketing Mix Modeling using Meta Robyn"
})

geolift_tool = algorithm_generator.generate_tool_from_algorithm_spec({
    "name": "GeoLift",
    "parameters": ["geo_data", "treatment_geos", "control_geos"],
    "outputs": ["incremental_lift", "confidence_interval", "p_value"],
    "description": "Geo experiment using Meta GeoLift"
})

causal_impact_tool = algorithm_generator.generate_tool_from_algorithm_spec({
    "name": "CausalImpact",
    "parameters": ["response_series", "control_series", "intervention_date"],
    "outputs": ["point_effect", "cumulative_effect", "credible_interval"],
    "description": "Bayesian Structural Time Series using Google CausalImpact"
})

mta_tool = algorithm_generator.generate_tool_from_algorithm_spec({
    "name": "MultiTouchAttribution",
    "parameters": ["attribution_data", "touchpoints"],
    "outputs": ["attribution_weights", "channel_contributions"],
    "description": "Multi-Touch Attribution model"
})

# Marketing Mix Modeling (MMM) Agent with Multiple Algorithms
mmm_agent = Agent(
    role='Marketing Mix Modeling (MMM) Specialist',
    goal='Estimate channel efficiency using multiple MMM frameworks and synthesize consensus recommendations',
    backstory='''Expert at Marketing Mix Modeling using Meta Robyn, GeoLift, CausalImpact, and Multi-Touch Attribution.

    **Multi-Algorithm Approach**:
    1. Run all algorithms in parallel to estimate channel effectiveness
    2. Compare channel efficiency estimates (ROAS, CPA) across algorithms
    3. Validate incrementality with geo experiments (GeoLift)
    4. Reconcile MMM with attribution models (MTA)
    5. Synthesize consensus recommendations using weighted averages
    6. Flag divergences for manual review when algorithms disagree
    
    Uses weighted consensus:
    - GeoLift: 35% (RCT gold standard)
    - CausalImpact: 30% (Bayesian inference)
    - Robyn: 25% (regression-based)
    - MTA: 10% (attribution heuristics)
    ''',
    tools=[
        publish_cloudevent,
        fetch_cloudevent,
        robyn_mmm_tool,           # Algorithm 1: Meta Robyn MMM
        geolift_tool,              # Algorithm 2: GeoLift geo experiments
        causal_impact_tool,        # Algorithm 3: CausalImpact BSTS
        mta_tool,                  # Algorithm 4: Multi-Touch Attribution
        compare_algorithm_results, # Compare results across algorithms
        synthesize_multi_algorithm_insights  # Synthesize consensus
    ],
    verbose=True,
    allow_delegation=False,
    llm_config={
        'provider': 'openai',
        'model': 'gpt-4o-mini',
        'temperature': 0.7
    }
)

# Export for use in runners
__all__ = ['mmm_agent']
