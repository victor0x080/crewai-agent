# 🎯 Template Examples - Real Queries

## Quick Reference: Query → Template → Agents

---

## 📊 **Forecasting Questions**

### Example 1
**Query**: *"What is the demand forecast for Nike Air Max shoes in Q3 2025?"*

**Matched Template**: `Demand Forecasting Workflow`

**Agents Allocated**:
1. **FQA** (Forecast Q&A) - Generates demand forecast
2. **SDA** (Semantic Data) - Retrieves historical sales data
3. **SSA** (Scenario Simulator) - Runs optimistic/baseline/pessimistic scenarios
4. **IRA** (Inventory Risk) - Assesses stockout/overstock risks

**Expected Response**:
- Q3 2025 forecast: 45,000 units
- Confidence interval: [42,000 - 48,000]
- Historical comparison: +12% vs Q3 2024
- Scenarios: Optimistic (52K), Baseline (45K), Pessimistic (38K)
- Risk: 15% stockout probability with current inventory

---

### Example 2
**Query**: *"When will we reach 100,000 units sold?"*

**Matched Template**: `Quick Forecast Q&A`

**Agents Allocated**:
1. **FQA** (Forecast Q&A) - Answers forecast question
2. **ASA** (Answer Synthesis) - Formats final answer

**Expected Response**:
- Estimated date: Mid-August 2025
- Based on current trend: ~5,000 units/week
- Confidence: 82%

---

## 💰 **Marketing Questions**

### Example 3
**Query**: *"Should I increase my Google Ads budget for the holiday season?"*

**Matched Template**: `Marketing Budget Optimization`

**Agents Allocated**:
1. **Marketing Plan** - Analyzes holiday campaign strategy
2. **Budget Optimizer** - Calculates optimal budget allocation
3. **Elasticity & Uplift** - Estimates incremental ROI
4. **Google Ads Agent** - Gets historical holiday performance
5. **Meta Ads Agent** - Compares cross-platform performance

**Expected Response**:
- ✅ **Recommendation**: Increase Google Ads budget by 35%
- Current: $50,000/month → Recommended: $67,500/month
- Expected ROAS: 6.5x (vs normal 4.2x)
- Incremental revenue: $113,750
- Best channels: Shopping campaigns (8.2x ROAS)

---

### Example 4
**Query**: *"Why did my Black Friday campaign underperform?"*

**Matched Template**: `Campaign Performance Analysis`

**Agents Allocated**:
1. **Campaign-SKU Mapper** - Maps campaign to affected products
2. **CAA** (Causal & Attribution) - Performs causal analysis
3. **Elasticity & Uplift** - Calculates actual vs expected uplift
4. **ASA** (Answer Synthesis) - Synthesizes insights

**Expected Response**:
- **Root Cause**: Competitor increased promo intensity by 40%
- **Attribution**: Only 60% of sales were incremental (vs 80% expected)
- **Price Elasticity**: Discount was insufficient (-15% vs market avg -25%)
- **Recommendations**: 
  1. Increase discount to -22%
  2. Add bundle offers
  3. Extend promotion by 3 days

---

## 📦 **Inventory Questions**

### Example 5
**Query**: *"Do I have enough inventory for holiday demand?"*

**Matched Template**: `Inventory Optimization Workflow`

**Agents Allocated**:
1. **Inventory Position** - Checks current inventory levels
2. **IRA** (Inventory Risk) - Assesses stockout risk
3. **Capacity & Lead-Time** - Checks production capacity
4. **OPT** (Optimizer) - Calculates optimal inventory
5. **ASA** (Answer Synthesis) - Synthesizes recommendations

**Expected Response**:
- ⚠️ **WARNING**: Current inventory insufficient
- Current: 15,000 units
- Holiday demand forecast: 52,000 units
- Stockout probability: 35% (HIGH RISK)
- **Action Required**: Order 32,000 units immediately
- Lead time: 45 days → Order deadline: October 15

---

## 🔄 **Scenario Analysis Questions**

### Example 6
**Query**: *"What if we reduce prices by 10%?"*

**Matched Template**: `Pricing Impact Analysis`

**Agents Allocated**:
1. **Elasticity & Uplift** - Calculates price elasticity
2. **SSA** (Scenario Simulator) - Simulates price reduction scenarios
3. **IRA** (Inventory Risk) - Assesses inventory impact
4. **Price-Promo Guardrail** - Checks pricing guardrails
5. **ASA** (Answer Synthesis) - Synthesizes recommendation

**Expected Response**:
- **Price Elasticity**: -1.8 (elastic)
- **Demand Impact**: +18% unit sales
- **Revenue Impact**: +6.2% ($312K additional)
- **Margin Impact**: -4.5% margin reduction
- **Inventory Impact**: Need 9,000 additional units
- **Guardrails**: ✅ Within policy (min margin: 22%, current: 24%)
- **Recommendation**: ✅ **Proceed with 10% price reduction**

---

## 🛍️ **Retail Media Questions**

### Example 7
**Query**: *"Should I invest more in Amazon or Walmart advertising?"*

**Matched Template**: `Multi-Retailer RMN Comparison`

**Agents Allocated**:
1. **Amazon RMN** - Gets Amazon metrics
2. **Walmart RMN** - Gets Walmart metrics
3. **Target RMN** - Gets Target metrics
4. **Instacart RMN** - Gets Instacart metrics
5. **Budget Optimizer** - Compares ROI
6. **ASA** (Answer Synthesis) - Synthesizes comparison

**Expected Response**:
| Retailer | ROAS | Cost/Click | Conversion | Volume |
|----------|------|------------|------------|--------|
| **Amazon** | 5.2x | $0.85 | 12.3% | High |
| **Walmart** | 4.8x | $0.65 | 10.1% | Medium |
| Target | 4.1x | $0.75 | 9.5% | Medium |
| Instacart | 3.9x | $0.95 | 8.2% | Low |

**Recommendation**: ✅ **Amazon** - Highest ROAS and conversion
- Allocate 60% of budget to Amazon
- Allocate 30% to Walmart (good value)
- Allocate 10% to Target/Instacart (testing)

---

## 📈 **Sales Questions**

### Example 8
**Query**: *"What's my sales pipeline forecast for next quarter?"*

**Matched Template**: `Sales Pipeline Forecasting`

**Agents Allocated**:
1. **Sales Pipeline Agent** - Analyzes current pipeline
2. **FQA** (Forecast Q&A) - Forecasts revenue
3. **CAA** (Causal & Attribution) - Analyzes conversion factors
4. **ASA** (Answer Synthesis) - Synthesizes forecast

**Expected Response**:
- **Q1 2025 Pipeline Forecast**: $2.4M
- **Confidence Interval**: [$2.1M - $2.7M]
- **Current Pipeline**: $5.8M (weighted)
- **Average Close Rate**: 42%
- **Deal Breakdown**:
  - High probability (>70%): $1.2M
  - Medium probability (40-70%): $0.8M
  - Low probability (<40%): $0.4M
- **Key Factors**: 
  - Enterprise deals closing slower (-2 weeks)
  - SMB conversion rate improving (+5%)

---

## 🔍 **Analysis Questions**

### Example 9
**Query**: *"Why did our revenue drop 15% last month?"*

**Matched Template**: `Root Cause Analysis`

**Agents Allocated**:
1. **RCA-Change Detective** - Detects changes and anomalies
2. **SDA** (Semantic Data) - Queries related metrics
3. **CAA** (Causal & Attribution) - Performs causal inference
4. **Data-Gap Mapping** - Identifies data gaps
5. **ASA** (Answer Synthesis) - Synthesizes root cause

**Expected Response**:
- **Root Cause**: Website outage on March 15-16 (48 hours)
- **Impact Analysis**:
  - Direct revenue loss: $180K (outage period)
  - Indirect loss: $95K (delayed conversions)
  - Total impact: $275K (14.8% of expected revenue)
- **Contributing Factors**:
  - Competitor launched aggressive promo (-3% market share)
  - Supply chain delay affected 2 key products (-2% revenue)
- **Correlation Score**: 0.89 (high confidence)

---

## ⚡ **Quick Questions**

### Example 10
**Query**: *"What was our revenue last quarter?"*

**Matched Template**: `Data Retrieval Query`

**Agents Allocated**:
1. **SDA** (Semantic Data) - Queries revenue data
2. **ASA** (Answer Synthesis) - Formats answer

**Expected Response**:
- **Q4 2024 Revenue**: $8.2M
- **vs Q3 2024**: +12.5% ($910K increase)
- **vs Q4 2023**: +18.3% ($1.27M increase)
- **Top products**: 
  1. Product A: $2.1M (26%)
  2. Product B: $1.8M (22%)
  3. Product C: $1.5M (18%)

---

## 🎯 **Template Selection Logic**

```
Query: "What is the demand forecast for Q3?"
        ↓
Keywords: ["demand", "forecast", "Q3"]
        ↓
Match Score:
  - Demand Forecasting Workflow: 0.89 ← SELECTED
  - Quick Forecast Q&A: 0.75
  - Sales Pipeline Forecasting: 0.65
        ↓
Allocate agents from winning template: [FQA, SDA, SSA, IRA]
```

---

## 💡 **Pro Tips**

### **1. Be Specific for Better Matching**
- ❌ "Forecast" → Generic Quick Q&A
- ✅ "Demand forecast for Q3 with risk assessment" → Full Demand Forecasting Workflow

### **2. Use Domain Keywords**
- Marketing: "campaign", "ads", "ROI", "budget"
- Supply Chain: "inventory", "stockout", "replenishment"
- Sales: "pipeline", "deals", "conversion", "revenue"
- RMN: "Amazon", "Walmart", "retailer", "sponsored"

### **3. Specify Timeframe**
- "Q3 2025" → Better context for forecasting
- "Last month" → Better for analysis
- "Holiday season" → Triggers seasonal patterns

---

**Your system now has intelligent template matching! 🎉**

Try these queries and see which templates get selected!

