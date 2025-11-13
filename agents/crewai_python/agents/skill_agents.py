"""11 Skill & Domain Agents - Python CrewAI"""
from crewai import Agent
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from tools.redis_streams_tools import publish_cloudevent, fetch_cloudevent, fetch_schema

# 1. SDA - Semantic Data Agent
sda = Agent(
    role='Semantic Data Specialist',
    goal='Provide tabular data with metric governance',
    backstory='Expert at SQL, dataframes, grains, SCDs, calendars',
    tools=[publish_cloudevent, fetch_schema],
    verbose=True,
    allow_delegation=False
)

# 2. FQA - Forecast Q&A Agent
fqa = Agent(
    role='Forecast Specialist',
    goal='Generate forecasts with uncertainty',
    backstory='Expert at time series, elasticity, demand modeling. Coupled with DemandForecastSignalAgent.',
    tools=[publish_cloudevent, fetch_cloudevent],
    verbose=True,
    allow_delegation=False
)

# 3. CAA - Causal & Attribution Agent
caa = Agent(
    role='Causal Analysis Specialist',
    goal='Diagnostic why and incremental lift',
    backstory='Expert at experiments, holdouts, causal inference',
    tools=[publish_cloudevent],
    verbose=True,
    allow_delegation=False
)

# 4. SSA - Scenario Simulator Agent
ssa = Agent(
    role='Scenario Simulator',
    goal='Run what-if counterfactuals',
    backstory='Expert at response curves, inventory propagation',
    tools=[publish_cloudevent],
    verbose=True,
    allow_delegation=False
)

# 5. IRA - Inventory Risk Agent
ira = Agent(
    role='Inventory Risk Analyst',
    goal='Compute stockout risk and replenishment',
    backstory='Expert at supply chain, lead times, service levels',
    tools=[publish_cloudevent],
    verbose=True,
    allow_delegation=False
)

# 6. OPT - Optimizer Agent
opt = Agent(
    role='Prescriptive Optimizer',
    goal='Choose optimal actions under constraints',
    backstory='Expert at optimization, constraint programming',
    tools=[publish_cloudevent],
    verbose=True,
    allow_delegation=False
)

# 7. ASA - Answer Synthesis Agent
asa = Agent(
    role='Answer Synthesizer',
    goal='Synthesize crisp answers with provenance',
    backstory='Expert at summarization, provenance, recommendations',
    tools=[publish_cloudevent],
    verbose=True,
    allow_delegation=False
)

# 8. Marketing Plan Agent
marketing_plan = Agent(
    role='Marketing Plan Translator',
    goal='Turn campaign briefs into machine-readable intent',
    backstory='Expert at campaign planning, targeting, lift estimation',
    tools=[publish_cloudevent],
    verbose=True,
    allow_delegation=False
)

# 9. Sales Pipeline Agent
sales_pipeline = Agent(
    role='Sales Pipeline Analyst',
    goal='Predict close dates/amounts from CRM',
    backstory='Expert at CRM data, opportunity scoring, pipeline forecasting',
    tools=[publish_cloudevent],
    verbose=True,
    allow_delegation=False
)

# 10. Elasticity & Uplift Agent
elasticity = Agent(
    role='Elasticity Estimator',
    goal='Estimate incremental demand from price/promo/campaigns',
    backstory='Expert at price elasticity, promo uplift, campaign attribution',
    tools=[publish_cloudevent],
    verbose=True,
    allow_delegation=False
)

# 11. Campaign→SKU Mapper Agent
campaign_sku_mapper = Agent(
    role='Campaign-SKU Mapper',
    goal='Translate DG constructs to SKU×Location×Time',
    backstory='Expert at catalog mapping, assortment rules, SKU targeting',
    tools=[publish_cloudevent],
    verbose=True,
    allow_delegation=False
)
