# Agent Examples - Retail Datacube Usage

## Example CrewAI Agents Using Datacube

### 1. Retail Performance Analyst Agent

```python
from crewai import Agent, Task, Crew
from tools.datacube_tools import (
    get_cross_domain_insights,
    detect_anomalies,
    get_pos_metrics
)

# Define Agent
performance_analyst = Agent(
    role='Retail Performance Analyst',
    goal='Analyze weekly sales trends and identify performance issues',
    backstory="""You are an expert retail analyst with 15 years experience.
    You excel at identifying trends, anomalies, and actionable insights from
    multi-domain retail data. You always back recommendations with data.""",
    tools=[
        get_cross_domain_insights,
        detect_anomalies,
        get_pos_metrics
    ],
    verbose=True,
    allow_delegation=False
)

# Define Task
analysis_task = Task(
    description="""Analyze last 12 weeks of retail performance for Region 5.
    
    1. Get cross-domain insights (sales, inventory, marketing)
    2. Detect any anomalies (low ROAS, stockout risk, overstock)
    3. Identify top 3 issues requiring immediate attention
    4. Provide specific recommendations with expected impact
    
    Output: Structured analysis with data-backed recommendations.""",
    agent=performance_analyst,
    expected_output="JSON report with findings and recommendations"
)

# Execute
crew = Crew(agents=[performance_analyst], tasks=[analysis_task])
result = crew.kickoff()
```

**Expected Agent Execution:**
```
> Entering new CrewAgentExecutor chain...

Thought: I need to get comprehensive data for Region 5 over last 12 weeks
Action: get_cross_domain_insights
Action Input: {"date_range": "last 12 weeks", "region_id": 5}

Observation: [
  {
    "RetailWeeklyStoreCategory.week": "2025-10-27",
    "RetailWeeklyStoreCategory.storeId": 101,
    "RetailWeeklyStoreCategory.categoryId": 3,
    "RetailWeeklyStoreCategory.unitsSold": 1520,
    "RetailWeeklyStoreCategory.netSales": 45600.00,
    "RetailWeeklyStoreCategory.roas": 2.3,
    "RetailWeeklyStoreCategory.weeksOfSupply": 8.5
  },
  ...
]

Thought: Now let me check for anomalies
Action: detect_anomalies
Action Input: {"date_range": "last 4 weeks", "region_id": 5}

Observation: {
  "anomaly_count": 3,
  "anomalies": [
    {
      "storeId": 103,
      "categoryId": 7,
      "roas": 1.2,
      "weeksOfSupply": 0.8
    },
    ...
  ]
}

Final Answer:
{
  "region": 5,
  "period": "Last 12 weeks",
  "key_findings": [
    {
      "issue": "Low ROAS in Store 103, Category 7",
      "severity": "High",
      "current_value": 1.2,
      "target_value": 3.0,
      "impact": "$12K wasted marketing spend"
    },
    {
      "issue": "Stockout risk in Store 103, Category 7", 
      "severity": "Critical",
      "current_value": "0.8 weeks supply",
      "target_value": "2-8 weeks",
      "impact": "Est. $25K lost sales"
    }
  ],
  "recommendations": [
    {
      "action": "Pause marketing campaigns for Store 103, Category 7",
      "expected_impact": "Save $3K/week, improve ROAS by 50%",
      "timeline": "Immediate"
    },
    {
      "action": "Expedite procurement for Category 7 to Store 103",
      "expected_impact": "Prevent stockout, recover $25K sales",
      "timeline": "2-3 days"
    }
  ]
}
```

---

### 2. Inventory Optimization Agent

```python
from crewai import Agent, Task
from tools.datacube_tools import (
    get_inventory_metrics,
    get_pos_metrics,
    get_procurement_metrics,
    query_retail_datacube
)

inventory_optimizer = Agent(
    role='Inventory Optimization Specialist',
    goal='Optimize inventory levels to minimize stockouts and overstock',
    backstory="""You are a supply chain expert specializing in inventory
    optimization. You balance service levels with holding costs and use
    data-driven approaches to recommend optimal stock positions.""",
    tools=[
        get_inventory_metrics,
        get_pos_metrics,
        get_procurement_metrics,
        query_retail_datacube
    ],
    verbose=True,
    allow_delegation=False
)

optimization_task = Task(
    description="""Optimize inventory for Store 101, all categories.
    
    1. Calculate current weeks of supply (inventory / sales velocity)
    2. Identify categories at stockout risk (< 2 weeks supply)
    3. Identify overstocked categories (> 10 weeks supply)
    4. Check inbound POs and ETAs
    5. Recommend rebalancing actions
    
    Target: 4-6 weeks of supply for all categories.""",
    agent=inventory_optimizer,
    expected_output="Inventory rebalancing plan with SKU-level actions"
)
```

**Sample Output:**
```json
{
  "store_id": 101,
  "analysis_date": "2025-11-04",
  "current_state": {
    "total_inventory_value": "$450K",
    "avg_weeks_supply": 7.2,
    "categories_at_risk": 3,
    "overstocked_categories": 2
  },
  "stockout_risks": [
    {
      "category_id": 7,
      "current_weeks": 1.2,
      "target_weeks": 4.0,
      "units_short": 850,
      "inbound_po_qty": 500,
      "eta": "2025-11-06",
      "action": "Expedite additional 350 units, ETA 2025-11-05"
    }
  ],
  "overstock": [
    {
      "category_id": 12,
      "current_weeks": 14.5,
      "target_weeks": 6.0,
      "excess_units": 1200,
      "action": "Redistribute 800 units to Stores 102, 105; Promo 400 units"
    }
  ],
  "expected_savings": "$32K in holding costs, $18K avoided lost sales"
}
```

---

### 3. Marketing ROI Optimizer Agent

```python
from crewai import Agent, Task
from tools.datacube_tools import (
    get_marketing_metrics,
    get_pos_metrics,
    query_retail_datacube
)

marketing_optimizer = Agent(
    role='Marketing ROI Optimization Specialist',
    goal='Maximize marketing ROI by reallocating budget to high-performing channels',
    backstory="""You are a digital marketing expert with deep expertise in
    multi-channel attribution and budget optimization. You use data to
    identify wasted spend and reallocate to winning channels.""",
    tools=[
        get_marketing_metrics,
        get_pos_metrics,
        query_retail_datacube
    ],
    verbose=True,
    allow_delegation=False
)

roi_optimization_task = Task(
    description="""Optimize marketing budget allocation for Region 5.
    
    Current budget: $50K/week across all channels
    Target ROAS: 4.0x
    
    1. Analyze ROAS by channel, store, campaign
    2. Identify low-performing spend (ROAS < 2.0x)
    3. Identify high-performing opportunities (ROAS > 5.0x)
    4. Recommend budget reallocation
    5. Estimate incremental revenue impact
    
    Constraint: Maintain total budget at $50K/week.""",
    agent=marketing_optimizer,
    expected_output="Budget reallocation plan with expected ROAS improvement"
)
```

**Sample Output:**
```json
{
  "current_state": {
    "total_spend": "$50,000/week",
    "total_attributed_sales": "$140,000/week",
    "overall_roas": 2.8,
    "target_roas": 4.0
  },
  "underperformers": [
    {
      "channel": "Social Media",
      "current_spend": "$15,000",
      "current_roas": 1.5,
      "recommendation": "Reduce by $8K → Reallocate"
    },
    {
      "campaign": "Campaign_XYZ",
      "current_spend": "$5,000",
      "current_roas": 0.9,
      "recommendation": "Pause immediately"
    }
  ],
  "high_performers": [
    {
      "channel": "Search",
      "current_spend": "$20,000",
      "current_roas": 5.2,
      "recommendation": "Increase by $10K",
      "incremental_revenue": "$52K"
    },
    {
      "channel": "Email",
      "current_spend": "$5,000",
      "current_roas": 6.8,
      "recommendation": "Increase by $3K",
      "incremental_revenue": "$20K"
    }
  ],
  "reallocation_plan": {
    "moves": [
      "Social Media: $15K → $7K (-$8K)",
      "Campaign_XYZ: $5K → $0K (-$5K)",
      "Search: $20K → $30K (+$10K)",
      "Email: $5K → $8K (+$3K)"
    ],
    "total_budget": "$50,000 (unchanged)",
    "projected_roas": 4.3,
    "incremental_revenue": "+$72K/week",
    "payback_period": "Immediate"
  }
}
```

---

### 4. Promotional Lift Analyzer Agent

```python
from crewai import Agent, Task
from tools.datacube_tools import (
    get_merchandising_metrics,
    get_pos_metrics,
    query_retail_datacube
)

promo_analyst = Agent(
    role='Promotional Effectiveness Analyst',
    goal='Measure promotional lift and recommend optimal promo strategies',
    backstory="""You are a pricing and promotions expert. You analyze the
    true incremental impact of promotions accounting for baseline sales,
    forward buying, and cannibalization.""",
    tools=[
        get_merchandising_metrics,
        get_pos_metrics,
        query_retail_datacube
    ],
    verbose=True,
    allow_delegation=False
)

promo_analysis_task = Task(
    description="""Analyze promotional effectiveness for Category 5.
    
    1. Compare sales during promo weeks vs non-promo weeks
    2. Calculate true incremental lift (accounting for baseline)
    3. Analyze promo depth (discount %) vs lift
    4. Identify optimal promo depth for maximum profit
    5. Recommend promo calendar for next quarter
    
    Output: Promotional playbook with profit-maximizing strategies.""",
    agent=promo_analyst,
    expected_output="Promo effectiveness report with recommendations"
)
```

---

### 5. Supply Chain Health Monitor Agent

```python
from crewai import Agent, Task
from tools.datacube_tools import (
    get_cross_domain_insights,
    get_procurement_metrics,
    get_inventory_metrics,
    detect_anomalies
)

supply_chain_monitor = Agent(
    role='Supply Chain Health Monitor',
    goal='Proactively detect and resolve supply chain issues',
    backstory="""You are a supply chain operations expert. You monitor
    end-to-end supply chain health metrics and intervene before issues
    escalate to customer-facing stockouts.""",
    tools=[
        get_cross_domain_insights,
        get_procurement_metrics,
        get_inventory_metrics,
        detect_anomalies
    ],
    verbose=True,
    allow_delegation=False
)

monitoring_task = Task(
    description="""Monitor supply chain health across all stores.
    
    Check for:
    1. Stockout risks (< 2 weeks supply)
    2. Delayed inbound shipments (past ETA)
    3. Supplier lead time variances
    4. Inventory imbalances across stores
    
    For each issue, assess severity and recommend corrective action.
    Escalate critical issues (imminent stockouts) immediately.""",
    agent=supply_chain_monitor,
    expected_output="Supply chain health report with prioritized action items"
)
```

---

## TypeScript Agent Example

```typescript
import { retailDatacube } from '@/services/datacube/RetailDatacubeService';
import { Agent } from '@/agents/base/Agent';

class RetailInsightsAgent extends Agent {
  async execute(context: { storeId: number; weeks: number }) {
    // Get comprehensive insights
    const insights = await retailDatacube.getCrossDomainInsights({
      storeId: context.storeId,
      dateRange: `last ${context.weeks} weeks`
    });
    
    // Detect anomalies
    const anomalies = await retailDatacube.detectAnomalies({
      dateRange: 'last 2 weeks'
    });
    
    // Analyze trends
    const trends = this.analyzeTrends(insights);
    
    // Generate recommendations
    const recommendations = this.generateRecommendations(
      insights,
      anomalies,
      trends
    );
    
    return {
      summary: `Analyzed ${insights.length} weeks of data`,
      anomalies: anomalies.length,
      recommendations: recommendations,
      confidence: 0.92
    };
  }
  
  private analyzeTrends(data: any[]) {
    // Calculate week-over-week growth
    const weeks = data.sort((a, b) => 
      new Date(a['RetailWeeklyStoreCategory.week']).getTime() - 
      new Date(b['RetailWeeklyStoreCategory.week']).getTime()
    );
    
    const salesTrend = weeks.map((w, i) => {
      if (i === 0) return null;
      const curr = w['RetailWeeklyStoreCategory.netSales'];
      const prev = weeks[i-1]['RetailWeeklyStoreCategory.netSales'];
      return ((curr - prev) / prev * 100).toFixed(1);
    }).filter(t => t !== null);
    
    return {
      avgWeeklyGrowth: salesTrend.reduce((a, b) => a + parseFloat(b), 0) / salesTrend.length,
      trend: salesTrend.slice(-4).every(t => parseFloat(t) > 0) ? 'improving' : 'declining'
    };
  }
  
  private generateRecommendations(insights: any[], anomalies: any[], trends: any) {
    const recommendations = [];
    
    // Low ROAS recommendations
    const lowROAS = anomalies.filter(a => a['RetailWeeklyStoreCategory.roas'] < 2);
    if (lowROAS.length > 0) {
      recommendations.push({
        priority: 'high',
        action: 'Optimize marketing spend allocation',
        impact: `Potential to save $${lowROAS.length * 2000}/week`,
        stores: lowROAS.map(a => a['RetailWeeklyStoreCategory.storeId'])
      });
    }
    
    // Stockout risk recommendations
    const atRisk = anomalies.filter(a => a['RetailWeeklyStoreCategory.weeksOfSupply'] < 2);
    if (atRisk.length > 0) {
      recommendations.push({
        priority: 'critical',
        action: 'Expedite inbound shipments',
        impact: `Prevent $${atRisk.length * 15000} in lost sales`,
        stores: atRisk.map(a => a['RetailWeeklyStoreCategory.storeId'])
      });
    }
    
    return recommendations;
  }
}
```

---

## Agent Orchestration Example

```python
from crewai import Crew, Process

# Define multiple specialized agents
performance_analyst = Agent(...)  # From example 1
inventory_optimizer = Agent(...)  # From example 2
marketing_optimizer = Agent(...)  # From example 3

# Create orchestrated crew
retail_ops_crew = Crew(
    agents=[performance_analyst, inventory_optimizer, marketing_optimizer],
    tasks=[
        Task(description="Analyze overall performance", agent=performance_analyst),
        Task(description="Optimize inventory", agent=inventory_optimizer),
        Task(description="Optimize marketing ROI", agent=marketing_optimizer)
    ],
    process=Process.sequential,  # Or Process.hierarchical with a manager
    verbose=True
)

# Execute crew
result = retail_ops_crew.kickoff()

# Result contains outputs from all agents
print(result)
```

---

## Best Practices

### 1. Always Specify Date Ranges
```python
# ✅ Good - explicit date range
get_pos_metrics(date_range="last 12 weeks", region_id=5)

# ❌ Bad - relies on default
get_pos_metrics(region_id=5)
```

### 2. Use Appropriate Granularity
```python
# ✅ Good - weekly for trend analysis (fast)
query_retail_datacube(domain='weekly', time_granularity='week')

# ❌ Bad - daily for long time ranges (slow)
query_retail_datacube(domain='pos', time_granularity='day', date_range='last 52 weeks')
```

### 3. Filter Early
```python
# ✅ Good - filter at query time
get_pos_metrics(region_id=5, category_id=7, date_range='last 4 weeks')

# ❌ Bad - fetch all then filter in code
all_data = get_pos_metrics(date_range='last 4 weeks')
filtered = [d for d in all_data if d['regionId'] == 5]
```

### 4. Handle Missing Data
```python
result = get_inventory_metrics(store_id=101, sku_id=456)
data = json.loads(result)

if not data:
    return "No inventory data found for Store 101, SKU 456"

# Safely access metrics
on_hand = data[0].get('RetailInventoryDaily.onHand', 0)
```

### 5. Cache Expensive Queries
```python
import functools
import json

@functools.lru_cache(maxsize=100)
def get_cached_insights(store_id: int, date_range: str):
    return get_cross_domain_insights(
        store_id=store_id,
        date_range=date_range
    )
```

---

These examples demonstrate how agents can leverage the retail datacube to make data-driven decisions across all operational domains.

